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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "trading", "index.html")
CHART_ASSET = os.path.join(ROOT, "trading", "scan-charts.json")
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


def setup_table(rows, aria, table_id):
    cells = []
    for r in rows:
        label, key = signal(r)
        sym = r["symbol"]
        safe_sym = html.escape(sym, quote=True)
        safe_sector = html.escape(str(r["sector"]), quote=True)
        detail_id = f"scan-detail-{table_id}-{re.sub(r'[^a-z0-9-]+', '-', sym.lower()).strip('-')}"
        cells.append(f"""                    <tr class="scan-data-row" data-scan-row data-scan-symbol="{safe_sym}">
                        <td class="scan-sym"><button class="scan-row-toggle" type="button" data-scan-toggle aria-expanded="false" aria-controls="{detail_id}" aria-label="Show {safe_sym} setup chart"><span class="scan-row-chevron" aria-hidden="true">›</span><span translate="no">{safe_sym}</span></button></td>
                        <td class="scan-sec">{safe_sector}</td>
                        <td class="scan-num">{znum(r.get('spread_z'))}</td>
                        <td class="scan-num">{znum(r.get('dist_z'))}</td>
                        <td class="scan-num">{znum(r.get('evwap_pct'), '%')}</td>
                        <td class="scan-num">{earn_cell(r)}</td>
                        <td><span class="scan-signal scan-signal--{key}">{label}</span></td>
                    </tr>
                    <tr class="scan-detail-row" id="{detail_id}" data-scan-detail data-scan-symbol="{safe_sym}" hidden>
                        <td colspan="7"><div class="scan-setup-chart" data-scan-chart="{safe_sym}"></div></td>
                    </tr>""")
    return f"""                <div class="scan-table-wrap">
                <table class="scan-table scan-accordion-table" aria-label="{aria}">
                    <thead><tr><th>Ticker</th><th>Sector</th><th class="scan-num">Spread Z</th><th class="scan-num">Dist Z</th><th class="scan-num">vs Earn VWAP</th><th class="scan-num">Next earnings</th><th>Signal</th></tr></thead>
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
        if record.get("sector") != source_row.get("sector") or record.get("label") != expected_label:
            sys.exit(f"{symbol} chart metadata does not match the momentum scan")
        stats = record.get("stats") or {}
        for key in ("spread_z", "dist_z", "evwap_pct", "evwap_side", "evwap_streak", "earn_anchor", "next_earn", "days_to_earn"):
            if stats.get(key) != source_row.get(key):
                sys.exit(f"{symbol} chart stat {key} does not match the momentum scan")
        for value in stats.values():
            if isinstance(value, float) and not math.isfinite(value):
                sys.exit(f"{symbol} chart stats contain a non-finite value")
        chart_map[symbol] = record
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

    sectors = "\n".join(
        f"""                    <li class="scan-sector{' scan-sector--hot' if s['hot'] else ''}{' scan-sector--cold' if s['cold'] else ''}"><b>{html.escape(str(s['etf']))}</b>{html.escape(str(s['name']))}<br>{znum(s['z'])} · #{s['rank']}</li>"""
        for s in p["sectors"])

    all_rows = sorted(p["rows"], key=lambda r: r["symbol"])
    spy = p["spy"]
    regime = f"SPY {spy['close']:.2f}, {'above' if spy['above_sma50'] else 'below'} its 50-day average"

    panel = f"""            <section class="trading-panel scan-panel" id="scan-panel" role="tabpanel" tabindex="0" aria-labelledby="scan-tab" hidden>
                <div class="position-head">
                    <h2 id="scan-heading">Momentum scan</h2>
                    <span>{last_bar} close · daily</span>
                </div>
                <p class="scan-intro">A mechanical relative-strength screen across the {len(all_rows)}-symbol universe: sector 50-session z-scores find the hot (and freezing) ponds, a stock-vs-SPY spread z-score finds the strongest and weakest fish in them, and earnings-anchored VWAP does the timing. Regime: {regime}. Method notes at the bottom.</p>
                <p class="scan-chart-hint">Click any ticker row to open the same full chart used in Setup Charts: YTD candles, earnings and YTD VWAPs, Spread Z, Dist Z, and the rule-based read. Only one chart stays open at a time.</p>
                <ul class="scan-sectors" aria-label="Sector 50-session z-scores, ranked">
{sectors}
                </ul>
                <div class="position-group">
                    <h3>Long setups · {len(longs)}</h3>
{setup_table(longs, "Long setups from the momentum scan", "long")}
                </div>
                <div class="position-group">
                    <h3>Short setups · {len(shorts)}</h3>
{setup_table(shorts, "Short setups from the momentum scan", "short")}
                </div>
                <div class="position-group">
                    <h3>Full scan · {len(all_rows)} symbols</h3>
                    <p class="scan-skip-full"><a href="#scan-method">Skip past the {len(all_rows)}-row table</a></p>
{setup_table(all_rows, "Full momentum scan of the tracked universe", "full")}
                </div>
                <script type="application/json" id="scan-chart-config">{chart_config}</script>
                <p class="trading-note" id="scan-method" tabindex="-1">Method: sector strength is the 50-session z-score of the sector ETF — the top three with z &gt; 1 are hot, the bottom three with z &lt; −1 freezing. Spread Z is the stock's 50-session z-score minus SPY's. Dist Z is the distance from the year-anchored VWAP in z units. ENTER needs a hot sector, spread Z &gt; 1, and price above its earnings-anchored VWAP; the "+" adds persistence above the yearly VWAP. SHORT is the exact mirror in a freezing sector with a confirmed break (5+ sessions below the earnings VWAP); BREAKING means the break is fresh. AVOID = lagging SPY or 5+ sessions below the earnings VWAP. NO DATA = fewer than 60 completed sessions. Bars are Alpaca SIP adjusted; BYDDY, MPNGY, NTDOY, and TCEHY use Yahoo adjusted-bar fallback. ⚠ marks earnings within ~9 days. This is the raw output of a screen, refreshed daily after the close — not positions, not predictions, and not investment advice.</p>
            </section>"""

    page = open(PAGE).read()
    new = re.sub(r"(<!-- AUTO:SCAN:START -->).*?(<!-- AUTO:SCAN:END -->)",
                 lambda m: f"{m.group(1)}\n{panel}\n            {m.group(2)}",
                 page, flags=re.S)
    new = re.sub(r'(<span class="trading-tab-count" id="scan-tab-count">)[^<]*(</span>)',
                 lambda m: f"{m.group(1)}{n_setups}{m.group(2)}", new)
    old_asset = open(CHART_ASSET).read() if os.path.exists(CHART_ASSET) else None
    page_changed, asset_changed = new != page, old_asset != asset_json
    if not page_changed and not asset_changed:
        print(f"[scan] already current: {os.path.basename(path)}, {len(longs)} long / {len(shorts)} short setups, {len(all_rows)} rows")
        return
    if page_changed:
        open(PAGE, "w").write(new)
    if asset_changed:
        open(CHART_ASSET, "w").write(asset_json)
    print(f"[scan] injected {os.path.basename(path)}: {len(longs)} long / {len(shorts)} short setups, {len(all_rows)} rows")


if __name__ == "__main__":
    main()
