#!/usr/bin/env python3
"""Inject the latest momentum scan into trading/index.html (AUTO:SCAN block).

Reads the newest ~/Documents/trading/scans/vwap-scan-*.json (or a path given
as argv[1]) emitted by ~/Documents/trading/src/vwap_scan.py, renders the
"Momentum scan" tab panel in house style, and rewrites the marker block plus
the tab-count badge.

Usage: python3 scripts/update-trading-scan.py [path/to/vwap-scan-YYYY-MM-DD.json]
Run from the repo root.
"""
import datetime as dt
import glob
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "trading", "index.html")
SCAN_GLOB = os.path.expanduser("~/Documents/trading/scans/vwap-scan-*.json")


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


def setup_table(rows, aria):
    cells = []
    for r in rows:
        label, key = signal(r)
        cells.append(f"""                    <tr>
                        <td class="scan-sym">{r['symbol']}</td>
                        <td class="scan-sec">{r['sector']}</td>
                        <td class="scan-num">{znum(r.get('spread_z'))}</td>
                        <td class="scan-num">{znum(r.get('dist_z'))}</td>
                        <td class="scan-num">{znum(r.get('evwap_pct'), '%')}</td>
                        <td class="scan-num">{earn_cell(r)}</td>
                        <td><span class="scan-signal scan-signal--{key}">{label}</span></td>
                    </tr>""")
    return f"""                <div class="scan-table-wrap">
                <table class="scan-table" aria-label="{aria}">
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

    last_bar = dt.date.fromisoformat(p["last_bar"]).strftime("%B %-d, %Y")
    longs = [r for r in p["rows"] if r["verdict"] in ("ENTER+", "ENTER")]
    longs.sort(key=lambda r: (r["verdict"] != "ENTER+", -(r.get("spread_z") or 0)))
    shorts = [r for r in p["rows"] if r.get("short_verdict") in ("SHORT+", "SHORT", "BREAKING")]
    shorts.sort(key=lambda r: ({"SHORT+": 0, "SHORT": 1, "BREAKING": 2}[r["short_verdict"]],
                               r.get("spread_z") or 0))
    n_setups = len(longs) + len(shorts)

    sectors = "\n".join(
        f"""                    <li class="scan-sector{' scan-sector--hot' if s['hot'] else ''}{' scan-sector--cold' if s['cold'] else ''}"><b>{s['etf']}</b>{html.escape(s['name'])}<br>{znum(s['z'])} · #{s['rank']}</li>"""
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
                <ul class="scan-sectors" aria-label="Sector 50-session z-scores, ranked">
{sectors}
                </ul>
                <div class="position-group">
                    <h3>Long setups · {len(longs)}</h3>
{setup_table(longs, "Long setups from the momentum scan")}
                </div>
                <div class="position-group">
                    <h3>Short setups · {len(shorts)}</h3>
{setup_table(shorts, "Short setups from the momentum scan")}
                </div>
                <div class="position-group">
                    <h3>Full scan · {len(all_rows)} symbols</h3>
{setup_table(all_rows, "Full momentum scan of the tracked universe")}
                </div>
                <p class="trading-note">Method: sector strength is the 50-session z-score of the sector ETF — the top three with z &gt; 1 are hot, the bottom three with z &lt; −1 freezing. Spread Z is the stock's 50-session z-score minus SPY's. Dist Z is the distance from the year-anchored VWAP in z units. ENTER needs a hot sector, spread Z &gt; 1, and price above its earnings-anchored VWAP; the "+" adds persistence above the yearly VWAP. SHORT is the exact mirror in a freezing sector with a confirmed break (5+ sessions below the earnings VWAP); BREAKING means the break is fresh. AVOID = lagging SPY or 5+ sessions below the earnings VWAP. NO DATA = OTC listings without exchange data. ⚠ marks earnings within ~9 days. This is the raw output of a screen, refreshed daily after the close — not positions, not predictions, and not investment advice.</p>
            </section>"""

    page = open(PAGE).read()
    new = re.sub(r"(<!-- AUTO:SCAN:START -->).*?(<!-- AUTO:SCAN:END -->)",
                 lambda m: f"{m.group(1)}\n{panel}\n            {m.group(2)}",
                 page, flags=re.S)
    new = re.sub(r'(<span class="trading-tab-count" id="scan-tab-count">)[^<]*(</span>)',
                 lambda m: f"{m.group(1)}{n_setups}{m.group(2)}", new)
    if new == page:
        sys.exit("No changes made — are the AUTO:SCAN markers present?")
    open(PAGE, "w").write(new)
    print(f"[scan] injected {os.path.basename(path)}: {len(longs)} long / {len(shorts)} short setups, {len(all_rows)} rows")


if __name__ == "__main__":
    main()
