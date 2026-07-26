#!/usr/bin/env python3
"""Inject the latest momentum scan into classic and routed dashboard surfaces.

Reads the newest ~/trading/scans/vwap-scan-*.json (or a path given
as argv[1]) plus its matching scan-charts JSON emitted by setup_vwap_charts.py, renders the
"Momentum scan" tab panel in house style, and rewrites the marker block plus
the tab-count badge.

Usage: python3 scripts/update-trading-scan.py [vwap-scan.json] [scan-charts.json] [quotes.json] [--risk risk-ytd.json]
Run from the repo root.
"""
import argparse
import copy
from collections import Counter
import datetime as dt
import glob
import hashlib
import html
import json
import math
import os
import re
import sys
from zoneinfo import ZoneInfo

from sync_trading_desk import sync_sections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "trading", "classic", "index.html")
CHART_ASSET = os.path.join(ROOT, "trading", "scan-charts.json")
UNIVERSE_ASSET = os.path.join(ROOT, "trading", "scan-universe.json")
DEFAULT_RISK_ASSET = os.path.join(ROOT, "trading", "risk-ytd.json")
SCAN_GLOB = os.path.expanduser("~/trading/scans/vwap-scan-*.json")
LONG_SIGNALS = ("ENTER+", "ENTER")
SHORT_SIGNALS = ("SHORT+", "SHORT", "BREAKING")


def znum(x, suffix="", dash="—"):
    """Signed mono number colored by sign."""
    if x is None:
        return f'<span class="scan-null">{dash}</span>'
    cls = "scan-z-pos" if x >= 0 else "scan-z-neg"
    return f'<span class="{cls}">{x:+.2f}{suffix}</span>'


def signal(row, *, public=True):
    """Public signal label: short verdicts win over the long-side AVOID."""
    sv = row.get("short_verdict")
    if sv in SHORT_SIGNALS:
        return sv, "short"
    v = row.get("public_verdict", row["verdict"]) if public else row["verdict"]
    key = {"ENTER+": "enter", "ENTER": "enter", "WATCH": "watch",
           "AVOID": "avoid", "NO DATA": "nodata"}[v]
    return v, key


def load_risk_context(path, last_bar, *, allow_stale=False):
    """Load and validate the public Stage-2 scanner policy without leaking local paths."""
    if not os.path.exists(path):
        raise ValueError(f"Missing risk policy artifact: {os.path.basename(path)}")
    with open(path, "rb") as risk_file:
        raw = risk_file.read()
    payload = json.loads(raw)
    policy = payload.get("scanner_policy") or {}
    label = (payload.get("score") or {}).get("label")
    score = (payload.get("score") or {}).get("total")
    if payload.get("schema_version") != 2 or label not in ("Contained", "Watchful", "Elevated"):
        raise ValueError("Risk policy artifact has an invalid schema or regime")
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
        raise ValueError("Risk policy score must be finite")
    required = {
        "schema_version", "stage", "as_of", "watchful_action", "elevated_action",
        "elevated_hard_gate_enabled", "stage1_bands_separate_from_unconditional_base_rate",
    }
    if not required <= set(policy) or policy["schema_version"] != 1 or policy["stage"] != "risk_v2_stage2":
        raise ValueError("Risk scanner policy is incomplete")
    fresh = payload.get("as_of") == last_bar and policy.get("as_of") == last_bar
    if not fresh and not allow_stale:
        raise ValueError(f"Risk policy must match scan session {last_bar}; pass --allow-stale-risk only for backfills")
    hard_gate = bool(
        fresh
        and label == "Elevated"
        and policy["elevated_hard_gate_enabled"]
        and policy["stage1_bands_separate_from_unconditional_base_rate"]
        and policy["elevated_action"] == "gate"
    )
    return {
        "source": os.path.basename(path),
        "source_digest": hashlib.sha256(raw).hexdigest()[:12],
        "as_of": payload.get("as_of"),
        "label": label,
        "score": round(float(score), 2),
        "fresh": fresh,
        "policy": {
            "watchful_action": policy["watchful_action"],
            "elevated_action": policy["elevated_action"],
            "elevated_hard_gate_enabled": hard_gate,
            "stage1_bands_separate_from_unconditional_base_rate": bool(policy["stage1_bands_separate_from_unconditional_base_rate"]),
        },
    }


def disabled_risk_context(last_bar):
    """Explicitly disable mechanical risk gating when the public risk page is journal-only."""
    return {
        "source": None,
        "source_digest": None,
        "as_of": last_bar,
        "label": "Disabled",
        "score": None,
        "fresh": True,
        "policy": {
            "watchful_action": "none",
            "elevated_action": "none",
            "elevated_hard_gate_enabled": False,
            "stage1_bands_separate_from_unconditional_base_rate": False,
        },
    }


def apply_risk_policy(source_rows, risk):
    """Preserve raw signals, then add deterministic public verdicts and audit decisions."""
    rows = []
    counts = {name: 0 for name in ("none", "annotate_watchful", "shadow_elevated", "gated_elevated", "stale_risk_shadow")}
    for source in source_rows:
        row = copy.deepcopy(source)
        public_verdict = row["verdict"]
        action = "none"
        hard_gate = False
        would_gate = False
        reason = "RISK_NO_ACTION"
        gated_from = None
        is_short = row.get("short_verdict") in SHORT_SIGNALS
        is_long = not is_short and row.get("verdict") in LONG_SIGNALS
        if is_long and not risk["fresh"]:
            action = "stale_risk_shadow"
            reason = "RISK_AS_OF_MISMATCH_NO_GATE"
        elif is_long and risk["label"] == "Watchful":
            action = "annotate_watchful"
            reason = "RISK_WATCHFUL_HALF_SIZE"
        elif is_long and risk["label"] == "Elevated":
            would_gate = True
            if risk["policy"]["elevated_hard_gate_enabled"]:
                action = "gated_elevated"
                hard_gate = True
                gated_from = row["verdict"]
                public_verdict = "WATCH"
                reason = "RISK_ELEVATED_STAGE1_SEPARATED_GATE"
            else:
                action = "shadow_elevated"
                reason = "RISK_ELEVATED_SHADOW_ONLY"
        row["public_verdict"] = public_verdict
        row["risk_decision"] = {
            "regime": risk["label"],
            "score": risk["score"],
            "action": action,
            "hard_gate": hard_gate,
            "would_gate": would_gate,
            "reason_code": reason,
            "gated_from": gated_from,
        }
        counts[action] += 1
        rows.append(row)
    return rows, counts


def fmt_date(iso):
    return dt.date.fromisoformat(iso).strftime("%b %-d")


def earn_cell(row):
    if not row.get("next_earn"):
        return '<span class="scan-null">—</span>'
    d = row.get("days_to_earn")
    flag = " ⚠" if d is not None and d <= 9 else ""
    return f'{fmt_date(row["next_earn"])} ({d}d){flag}'


def price_cell(quote):
    price = quote["price"]
    day_pct = quote["day_pct"]
    day_class = "scan-z-pos" if day_pct > 0 else "scan-z-neg" if day_pct < 0 else "scan-null"
    direction = "up" if day_pct > 0 else "down" if day_pct < 0 else "unchanged"
    return (f'<span class="scan-price-value">${price:,.2f}</span> '
            f'<span class="{day_class}" aria-label="{direction} {abs(day_pct):.2f} percent today">{day_pct:+.2f}%</span>')


def setup_table(rows, aria, table_id, quotes):
    cells = []
    gloss = {
        "ENTER+": "qualified + persistent",
        "ENTER": "qualified",
        "SHORT+": "short + persistent",
        "SHORT": "short qualified",
        "BREAKING": "fresh short break",
        "WATCH": "watch",
        "AVOID": "not qualified",
        "NO DATA": "insufficient data",
    }
    for r in rows:
        label, key = signal(r)
        sym = r["symbol"]
        safe_sym = html.escape(sym, quote=True)
        safe_sector = html.escape(str(r["sector"]), quote=True)
        detail_id = f"scan-detail-{table_id}-{re.sub(r'[^a-z0-9-]+', '-', sym.lower()).strip('-')}"
        cells.append(f"""                    <tr class="scan-data-row" data-scan-row data-scan-symbol="{safe_sym}" data-day-pct="{quotes[sym]['day_pct']:.8f}">
                        <td class="scan-sym"><button class="scan-row-toggle" type="button" data-scan-toggle aria-expanded="false" aria-controls="{detail_id}" aria-label="Show {safe_sym} setup and sector charts"><span class="scan-row-chevron" aria-hidden="true">›</span><span><span translate="no">{safe_sym}</span><span class="bl-tag">{safe_sector}</span></span></button></td>
                        <td class="scan-num scan-price">{price_cell(quotes[sym])}</td>
                        <td class="scan-num">{znum(r.get('spread_z'))}</td>
                        <td class="scan-num">{earn_cell(r)}</td>
                        <td><span class="scan-signal scan-signal--{key}" title="{html.escape(gloss[label], quote=True)}">{label}</span></td>
                    </tr>
                    <tr class="scan-detail-row" id="{detail_id}" data-scan-detail data-scan-symbol="{safe_sym}" hidden>
                        <td colspan="5"><div class="scan-setup-chart" data-scan-chart="{safe_sym}"></div></td>
                    </tr>""")
    return f"""                <div class="scan-table-wrap">
                <table class="scan-table scan-accordion-table scan-table--decision" aria-label="{aria}">
                    <thead><tr><th>Ticker</th><th class="scan-num" aria-sort="none"><button type="button" class="scan-sort" data-scan-sort-day>Price · Day <span aria-hidden="true">⇅</span></button></th><th class="scan-num">Rel. strength</th><th class="scan-num">Earnings</th><th>Signal</th></tr></thead>
                    <tbody>
{os.linesep.join(cells)}
                    </tbody>
                </table>
                </div>"""


def setup_links(rows, label):
    """Render the qualified subset once without duplicating full chart accordions."""
    if not rows:
        return f'<p class="bl-empty">No qualified {label.lower()} today.</p>'
    links = " · ".join(
        f'<a href="?chart={html.escape(row["symbol"], quote=True)}#scan" translate="no">{html.escape(row["symbol"])}</a>'
        for row in rows
    )
    return f'<p class="scan-qualified-links"><b>{html.escape(label)}</b> · {links}</p>'


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scan", nargs="?", help="vwap-scan JSON; defaults to newest local artifact")
    parser.add_argument("charts", nargs="?", help="matching full scan-charts JSON")
    parser.add_argument("quotes", nargs="?", help="optional current quote JSON")
    parser.add_argument("--risk", default=DEFAULT_RISK_ASSET, help="Risk v2 policy JSON")
    parser.add_argument("--allow-stale-risk", action="store_true", help="Backfill only: shadow-log a mismatched risk date and never hard-gate")
    parser.add_argument("--no-risk", action="store_true", help="Disable mechanical risk gating and publish raw momentum signals")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.scan:
        path = args.scan
    else:
        paths = sorted(glob.glob(SCAN_GLOB))
        if not paths:
            sys.exit(f"No scan JSON matching {SCAN_GLOB}")
        path = paths[-1]
    p = json.load(open(path))
    rows = p.get("rows") or []
    row_symbols = [str(r.get("symbol") or "") for r in rows]
    if len(row_symbols) != len(set(row_symbols)) or any(not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,14}", symbol) for symbol in row_symbols):
        sys.exit("Scan symbols must be unique, uppercase, and contain only letters, digits, dots, or hyphens")
    if args.no_risk:
        risk = disabled_risk_context(p["last_bar"])
    else:
        try:
            risk = load_risk_context(args.risk, p["last_bar"], allow_stale=args.allow_stale_risk)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            sys.exit(str(error))
    rows, risk_decision_counts = apply_risk_policy(rows, risk)
    p = dict(p)
    p["rows"] = rows

    if args.charts:
        chart_path = args.charts
    else:
        chart_path = os.path.join(os.path.dirname(path), os.path.basename(path).replace("vwap-scan-", "scan-charts-"))
    if not os.path.exists(chart_path):
        sys.exit(f"Missing matching full chart JSON: {chart_path}")
    chart_payload = json.load(open(chart_path))
    if chart_payload.get("last_bar") != p["last_bar"]:
        sys.exit("Full chart data and momentum scan do not share the same completed session")
    scan_sha256 = hashlib.sha256(open(path, "rb").read()).hexdigest()
    if chart_payload.get("scan_sha256") != scan_sha256:
        sys.exit("Full chart artifact was not generated from this exact momentum scan JSON")
    charts = chart_payload.get("charts") or []
    symbols = set(row_symbols)
    if len(charts) != len(symbols) or {r.get("symbol") for r in charts} != symbols:
        sys.exit("Full setup chart records must match the scan universe exactly")
    chart_map = {}
    rows_by_symbol = {r["symbol"]: r for r in rows}
    series_keys = ("dates", "o", "h", "l", "c", "ev", "yv", "sp", "dz")
    for record in charts:
        symbol, series = record["symbol"], record.get("series") or {}
        dates = series.get("dates") or []
        try:
            canonical_dates = [dt.date.fromisoformat(value).isoformat() for value in dates]
        except (TypeError, ValueError):
            sys.exit(f"{symbol} chart dates must be strict ISO calendar dates")
        if not dates or dates != canonical_dates or dates != sorted(set(dates)) or dates[-1] != p["last_bar"]:
            sys.exit(f"{symbol} chart dates must be non-empty, unique, increasing, and end on {p['last_bar']}")
        if any(len(series.get(key) or []) != len(dates) for key in series_keys[1:]):
            sys.exit(f"{symbol} full setup chart series are not aligned")
        numeric = [value for key in series_keys[1:] for value in series[key] if value is not None]
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in numeric):
            sys.exit(f"{symbol} full setup chart contains a non-finite value")
        source_row = rows_by_symbol[symbol]
        expected_label = source_row.get("short_verdict") if source_row.get("short_verdict") in ("SHORT+", "SHORT", "BREAKING") else source_row["verdict"]
        if (record.get("sector") != source_row.get("sector")
                or record.get("sector_etf") != source_row.get("etf")
                or record.get("label") != expected_label):
            sys.exit(f"{symbol} chart metadata does not match the momentum scan")
        stats = record.get("stats") or {}
        for key in ("spread_z", "dist_z", "evwap_pct", "evwap_side", "evwap_streak", "earn_anchor", "next_earn", "days_to_earn"):
            if stats.get(key) != source_row.get(key):
                sys.exit(f"{symbol} chart stat {key} does not match the momentum scan")
        for value in stats.values():
            if isinstance(value, float) and not math.isfinite(value):
                sys.exit(f"{symbol} chart stats contain a non-finite value")
        public_label = signal(source_row)[0]
        record = copy.deepcopy(record)
        record["raw_label"] = expected_label
        record["label"] = public_label
        record["risk_decision"] = source_row["risk_decision"]
        chart_map[symbol] = record
    quotes = {}
    for symbol, record in chart_map.items():
        closes = record["series"]["c"]
        if len(closes) < 2 or closes[-1] is None or closes[-2] in (None, 0):
            sys.exit(f"{symbol} needs two valid closes for price and day change")
        quotes[symbol] = {
            "price": float(closes[-1]),
            "day_pct": (float(closes[-1]) / float(closes[-2]) - 1) * 100,
        }
    quote_stamp = None
    if args.quotes:
        quote_payload = json.load(open(args.quotes))
        quote_rows = quote_payload.get("quotes") or {}
        if set(quote_rows) != symbols:
            missing = sorted(symbols - set(quote_rows))
            extra = sorted(set(quote_rows) - symbols)
            sys.exit(f"Live quote symbols must match the scan exactly (missing={missing}, extra={extra})")
        for symbol, quote in quote_rows.items():
            price, day_pct = quote.get("price"), quote.get("day_pct")
            if (isinstance(price, bool) or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0
                    or isinstance(day_pct, bool) or not isinstance(day_pct, (int, float)) or not math.isfinite(day_pct)):
                sys.exit(f"{symbol} live quote is invalid")
            quotes[symbol] = {"price": float(price), "day_pct": float(day_pct)}
        try:
            generated = dt.datetime.fromisoformat(str(quote_payload["generated_at"]))
            if generated.tzinfo is None:
                raise ValueError("timezone required")
        except (KeyError, TypeError, ValueError):
            sys.exit("Live quote generated_at must be a timezone-aware ISO timestamp")
        quote_stamp = generated.astimezone(ZoneInfo("America/Chicago")).strftime("%b %-d, %-I:%M %p CT")
    counts_raw = dict(sorted(Counter(signal(row, public=False)[0] for row in rows).items()))
    counts_public = dict(sorted(Counter(signal(row)[0] for row in rows).items()))
    public_risk = copy.deepcopy(risk)
    asset_json = json.dumps({
        "schema_version": 2,
        "last_bar": p["last_bar"],
        "risk_regime": public_risk,
        "counts_raw": counts_raw,
        "counts_public": counts_public,
        "risk_decision_counts": risk_decision_counts,
        "charts": chart_map,
    }, separators=(",", ":"), allow_nan=False)
    asset_hash = hashlib.sha256(asset_json.encode()).hexdigest()[:12]
    chart_config = json.dumps({"url": f"/trading/scan-charts.json?v={asset_hash}"}, separators=(",", ":"), allow_nan=False)

    last_bar = dt.date.fromisoformat(p["last_bar"]).strftime("%B %-d, %Y")
    longs = [r for r in p["rows"] if signal(r)[0] in LONG_SIGNALS]
    longs.sort(key=lambda r: (signal(r)[0] != "ENTER+", -(r.get("spread_z") or 0)))
    shorts = [r for r in p["rows"] if r.get("short_verdict") in SHORT_SIGNALS]
    shorts.sort(key=lambda r: ({"SHORT+": 0, "SHORT": 1, "BREAKING": 2}[r["short_verdict"]],
                               r.get("spread_z") or 0))
    n_setups = len(longs) + len(shorts)

    ranked_sectors = sorted(p["sectors"], key=lambda s: s["rank"])
    leading = ranked_sectors[:2]
    lagging = ranked_sectors[-2:]
    sectors = "\n".join(
        f"""                        <li class="scan-sector{' scan-sector--hot' if s['hot'] else ''}{' scan-sector--cold' if s['cold'] else ''}">
                            <span class="scan-sector-head"><b>{html.escape(str(s['etf']))}</b><span>#{s['rank']}</span></span>
                            <span class="scan-sector-name">{html.escape(str(s['name']))}</span>
                            <span class="scan-sector-score">{znum(s['z'])} <small>50D Z</small></span>
                        </li>"""
        for s in ranked_sectors)

    all_rows = sorted(p["rows"], key=lambda r: r["symbol"])
    spy = p["spy"]
    regime = f"SPY {spy['close']:.2f}, {'above' if spy['above_sma50'] else 'below'} its 50-day average"
    price_freshness = f"Prices {quote_stamp}" if quote_stamp else f"Prices {last_bar} close"
    setup_parts = []
    if longs:
        setup_parts.append(f"{len(longs)} qualified long{'s' if len(longs) != 1 else ''}")
    if shorts:
        setup_parts.append(f"{len(shorts)} qualified short{'s' if len(shorts) != 1 else ''}")
    setup_summary = " and ".join(setup_parts) if setup_parts else "No qualified setups"
    sector_names = sorted({str(r["sector"]) for r in [*longs, *shorts]})
    sector_clause = f" across {', '.join(sector_names)}" if sector_names else ""
    takeaway = f"{setup_summary}{sector_clause}. {regime}."
    short_block = setup_links(shorts, "Short setups")

    universe_rows = []
    for row in all_rows:
        label, key = signal(row)
        raw_label, _ = signal(row, public=False)
        universe_rows.append({
            "symbol": row["symbol"],
            "sector": row["sector"],
            "price": quotes[row["symbol"]]["price"],
            "day_pct": quotes[row["symbol"]]["day_pct"],
            "spread_z": row.get("spread_z"),
            "dist_z": row.get("dist_z"),
            "evwap_pct": row.get("evwap_pct"),
            "next_earn": row.get("next_earn"),
            "days_to_earn": row.get("days_to_earn"),
            "raw_signal": raw_label,
            "signal": label,
            "signal_key": key,
            "risk_decision": row["risk_decision"],
        })
    universe_json = json.dumps({
        "schema_version": 2,
        "last_bar": p["last_bar"],
        "risk_regime": public_risk,
        "counts_raw": counts_raw,
        "counts_public": counts_public,
        "risk_decision_counts": risk_decision_counts,
        "rows": universe_rows,
    }, separators=(",", ":"), allow_nan=False)
    universe_hash = hashlib.sha256(universe_json.encode()).hexdigest()[:12]
    if risk["label"] == "Disabled":
        overlay_copy = "Subjective risk journal only · no automated risk gate; momentum signals are published unchanged."
    elif not risk["fresh"]:
        overlay_copy = f"Risk input dated {risk['as_of']} does not match this scan; no hard gate was allowed."
    elif risk["label"] == "Watchful":
        overlay_copy = f"Risk {risk['label']} {risk['score']:.2f} · qualified longs stay public · half-size"
    elif risk["label"] == "Elevated" and risk["policy"]["elevated_hard_gate_enabled"]:
        overlay_copy = f"Risk Elevated {risk['score']:.2f} · qualified long entries are gated to WATCH; short signals are unchanged."
    elif risk["label"] == "Elevated":
        overlay_copy = f"Risk Elevated {risk['score']:.2f} · shadow logging only because the hard-gate evidence contract is not active."
    else:
        overlay_copy = f"Risk Contained {risk['score']:.2f} · no momentum overlay action."

    panel = f"""            <section class="trading-panel scan-panel" id="scan-panel" role="tabpanel" tabindex="0" aria-labelledby="scan-tab" hidden>
                <div class="position-head">
                    <h2 id="scan-heading">Momentum</h2>
                    <span>Signals {last_bar} close · {price_freshness}</span>
                </div>
                <p class="trading-takeaway">{html.escape(takeaway)}</p>
                <p class="scan-risk-overlay">{html.escape(overlay_copy)}</p>
                <p class="signal-legend"><b>ENTER+</b> = qualified + persistent · <b>ENTER</b> = qualified · <b>WATCH</b> = watch · <b>AVOID</b> = not qualified</p>
                <div class="sector-summary">
                    <span><b>Leading</b> {' · '.join(html.escape(str(s['name'])) for s in leading)}</span>
                    <span><b>Lagging</b> {' · '.join(html.escape(str(s['name'])) for s in reversed(lagging))}</span>
                    <details open><summary>All sectors · 50-day Z-score</summary><ul class="scan-sectors" aria-label="Sector 50-session z-scores, ranked">
{sectors}
                    </ul></details>
                </div>
                <p class="scan-chart-hint">Open a ticker for its setup and matching sector chart.</p>
                <div class="position-group">
                    <h3>Long setups · {len(longs)}</h3>
{setup_links(longs, "Long setups")}
                </div>
                <div class="position-group">
                    <h3>Short setups · {len(shorts)}</h3>
{short_block}
                </div>
                <details class="scan-universe-disclosure" id="scan-universe" open>
                    <summary>Browse full universe · {len(all_rows)} symbols</summary>
                    <div class="scan-universe-tools"><label for="scan-universe-q">Find symbol</label><input type="search" id="scan-universe-q" name="scan-universe-symbol" placeholder="AAPL…" autocomplete="off" spellcheck="false"></div>
                    <div id="scan-universe-shell" data-url="/trading/scan-universe.json?v={universe_hash}"><p class="bl-empty">Loading universe…</p></div>
                </details>
                <script type="application/json" id="scan-chart-config">{chart_config}</script>
                <details class="trading-method" id="scan-method"><summary>How this works</summary><p>Sector strength is the 50-session z-score of the sector ETF. Spread Z compares each stock with SPY; Dist Z measures distance from YTD VWAP. ENTER needs a hot sector, relative strength, and price above earnings VWAP; the + adds persistence above YTD VWAP. SHORT mirrors that setup in a weak sector. Watchful halves longs; validated Elevated gates them to WATCH; shorts stay. ⚠ marks earnings within about 9 days. Bars are adjusted and intraday price/day marks refresh during regular hours. This is a mechanical screen, not a recommendation.</p></details>
            </section>"""

    for row in sorted(rows, key=lambda item: item["symbol"]):
        decision = row["risk_decision"]
        if decision["action"] == "none":
            continue
        print(json.dumps({
            "event": "momentum_risk_decision",
            "last_bar": p["last_bar"],
            "risk_as_of": risk["as_of"],
            "risk_label": risk["label"],
            "risk_score": risk["score"],
            "symbol": row["symbol"],
            "raw_signal": signal(row, public=False)[0],
            "public_signal": signal(row)[0],
            "action": decision["action"],
            "hard_gate": decision["hard_gate"],
            "would_gate": decision["would_gate"],
            "reason_code": decision["reason_code"],
        }, sort_keys=True, separators=(",", ":")))
    print(json.dumps({
        "event": "momentum_risk_summary",
        "last_bar": p["last_bar"],
        "risk_as_of": risk["as_of"],
        "risk_label": risk["label"],
        "risk_score": risk["score"],
        "fresh": risk["fresh"],
        "counts": risk_decision_counts,
    }, sort_keys=True, separators=(",", ":")))

    page = open(PAGE).read()
    new = re.sub(r"(<!-- AUTO:SCAN:START -->).*?(<!-- AUTO:SCAN:END -->)",
                 lambda m: f"{m.group(1)}\n{panel}\n            {m.group(2)}",
                 page, flags=re.S)
    new = re.sub(r'(<span class="trading-tab-count" id="scan-tab-count">)[^<]*(</span>)',
                 lambda m: f"{m.group(1)}{n_setups}{m.group(2)}", new)
    old_asset = open(CHART_ASSET).read() if os.path.exists(CHART_ASSET) else None
    old_universe = open(UNIVERSE_ASSET).read() if os.path.exists(UNIVERSE_ASSET) else None
    page_changed = new != page
    asset_changed = old_asset != asset_json
    universe_changed = old_universe != universe_json
    if page_changed:
        open(PAGE, "w").write(new)
    if asset_changed:
        open(CHART_ASSET, "w").write(asset_json)
    if universe_changed:
        open(UNIVERSE_ASSET, "w").write(universe_json)
    routed_changed = bool(sync_sections(["momentum"]))
    if not page_changed and not asset_changed and not universe_changed and not routed_changed:
        print(f"[scan] already current: {os.path.basename(path)}, {len(longs)} long / {len(shorts)} short setups, {len(all_rows)} rows")
        return
    print(f"[scan] injected {os.path.basename(path)}: {len(longs)} long / {len(shorts)} short setups, {len(all_rows)} rows")


if __name__ == "__main__":
    main()
