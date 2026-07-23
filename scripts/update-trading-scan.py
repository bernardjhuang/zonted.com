#!/usr/bin/env python3
"""Inject the latest momentum scan into trading/index.html (AUTO:SCAN block).

Reads the newest ~/trading/scans/vwap-scan-*.json (or a path given
as argv[1]) plus its matching scan-charts JSON emitted by setup_vwap_charts.py, renders the
"Momentum scan" tab panel in house style, and rewrites the marker block plus
the tab-count badge.

Usage: python3 scripts/update-trading-scan.py [vwap-scan.json] [scan-charts.json]
Run from the repo root.
"""
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "trading", "index.html")
CHART_ASSET = os.path.join(ROOT, "trading", "scan-charts.json")
UNIVERSE_ASSET = os.path.join(ROOT, "trading", "scan-universe.json")
SCAN_GLOB = os.path.expanduser("~/trading/scans/vwap-scan-*.json")


def znum(x, suffix="", dash="—"):
    """Signed mono number colored by sign."""
    if x is None:
        return f'<span class="scan-null">{dash}</span>'
    cls = "scan-z-pos" if x >= 0 else "scan-z-neg"
    return f'<span class="{cls}">{x:+.2f}{suffix}</span>'


def signal(row):
    """Public signal label: short verdicts win over the long-side AVOID."""
    sv = row.get("short_verdict")
    if sv in ("SHORT+", "SHORT", "BREAKING"):
        return sv, "short"
    v = row["verdict"]
    key = {"ENTER+": "enter", "ENTER": "enter", "WATCH": "watch",
           "AVOID": "avoid", "NO DATA": "nodata"}[v]
    return v, key


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


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
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

    if len(sys.argv) > 2:
        chart_path = sys.argv[2]
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
    if len(sys.argv) > 3:
        quote_payload = json.load(open(sys.argv[3]))
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
    asset_json = json.dumps({"last_bar": p["last_bar"], "charts": chart_map}, separators=(",", ":"), allow_nan=False)
    asset_hash = hashlib.sha256(asset_json.encode()).hexdigest()[:12]
    chart_config = json.dumps({"url": f"/trading/scan-charts.json?v={asset_hash}"}, separators=(",", ":"), allow_nan=False)

    last_bar = dt.date.fromisoformat(p["last_bar"]).strftime("%B %-d, %Y")
    longs = [r for r in p["rows"] if r["verdict"] in ("ENTER+", "ENTER")]
    longs.sort(key=lambda r: (r["verdict"] != "ENTER+", -(r.get("spread_z") or 0)))
    shorts = [r for r in p["rows"] if r.get("short_verdict") in ("SHORT+", "SHORT", "BREAKING")]
    shorts.sort(key=lambda r: ({"SHORT+": 0, "SHORT": 1, "BREAKING": 2}[r["short_verdict"]],
                               r.get("spread_z") or 0))
    n_setups = len(longs) + len(shorts)

    ranked_sectors = sorted(p["sectors"], key=lambda s: s["rank"])
    leading = ranked_sectors[:2]
    lagging = ranked_sectors[-2:]
    sectors = "\n".join(
        f"""                        <li class="scan-sector{' scan-sector--hot' if s['hot'] else ''}{' scan-sector--cold' if s['cold'] else ''}"><b>{html.escape(str(s['etf']))}</b>{html.escape(str(s['name']))}<br>{znum(s['z'])} · #{s['rank']}</li>"""
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
    short_block = setup_table(shorts, "Short setups from the momentum scan", "short", quotes) if shorts else '<p class="bl-empty">No qualified shorts today.</p>'

    universe_rows = []
    for row in all_rows:
        label, key = signal(row)
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
            "signal": label,
            "signal_key": key,
        })
    universe_json = json.dumps({"last_bar": p["last_bar"], "rows": universe_rows}, separators=(",", ":"), allow_nan=False)
    universe_hash = hashlib.sha256(universe_json.encode()).hexdigest()[:12]

    panel = f"""            <section class="trading-panel scan-panel" id="scan-panel" role="tabpanel" tabindex="0" aria-labelledby="scan-tab" hidden>
                <div class="position-head">
                    <h2 id="scan-heading">Momentum</h2>
                    <span>Signals {last_bar} close · {price_freshness}</span>
                </div>
                <p class="trading-takeaway">{html.escape(takeaway)}</p>
                <p class="signal-legend"><b>ENTER+</b> = qualified + persistent · <b>ENTER</b> = qualified · <b>WATCH</b> = watch · <b>AVOID</b> = not qualified</p>
                <div class="sector-summary">
                    <span><b>Leading</b> {' · '.join(html.escape(str(s['name'])) for s in leading)}</span>
                    <span><b>Lagging</b> {' · '.join(html.escape(str(s['name'])) for s in reversed(lagging))}</span>
                    <details><summary>View all sectors</summary><ul class="scan-sectors" aria-label="Sector 50-session z-scores, ranked">
{sectors}
                    </ul></details>
                </div>
                <p class="scan-chart-hint">Open a ticker for its setup and matching sector chart.</p>
                <div class="position-group">
                    <h3>Long setups · {len(longs)}</h3>
{setup_table(longs, "Long setups from the momentum scan", "long", quotes)}
                </div>
                <div class="position-group">
                    <h3>Short setups · {len(shorts)}</h3>
{short_block}
                </div>
                <details class="scan-universe-disclosure" id="scan-universe">
                    <summary>Browse full universe · {len(all_rows)} symbols</summary>
                    <div class="scan-universe-tools"><label for="scan-universe-q">Find symbol</label><input type="search" id="scan-universe-q" name="scan-universe-symbol" placeholder="AAPL…" autocomplete="off" spellcheck="false"></div>
                    <div id="scan-universe-shell" data-url="/trading/scan-universe.json?v={universe_hash}"><p class="bl-empty">Open to load the universe.</p></div>
                </details>
                <script type="application/json" id="scan-chart-config">{chart_config}</script>
                <details class="trading-method" id="scan-method"><summary>How this works</summary><p>Sector strength is the 50-session z-score of the sector ETF. Spread Z compares each stock with SPY; Dist Z measures distance from YTD VWAP. ENTER needs a hot sector, relative strength, and price above earnings VWAP; the + adds persistence above YTD VWAP. SHORT mirrors that setup in a weak sector. ⚠ marks earnings within about 9 days. Bars are adjusted and intraday price/day marks refresh during regular hours. This is a mechanical screen, not a recommendation.</p></details>
            </section>"""

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
    if not page_changed and not asset_changed and not universe_changed:
        print(f"[scan] already current: {os.path.basename(path)}, {len(longs)} long / {len(shorts)} short setups, {len(all_rows)} rows")
        return
    if page_changed:
        open(PAGE, "w").write(new)
    if asset_changed:
        open(CHART_ASSET, "w").write(asset_json)
    if universe_changed:
        open(UNIVERSE_ASSET, "w").write(universe_json)
    print(f"[scan] injected {os.path.basename(path)}: {len(longs)} long / {len(shorts)} short setups, {len(all_rows)} rows")


if __name__ == "__main__":
    main()
