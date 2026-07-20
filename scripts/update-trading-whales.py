#!/usr/bin/env python3
"""Inject 13F whale flows into trading/index.html (AUTO:WHALES block).

Reads the newest ~/Documents/trading/scans/whale-13f-*.json (or a path given
as argv[1]) emitted by ~/Documents/trading/src/whale_13f.py and renders the
"13F flows" tab: a diverging buys/sells bar per office (net tick), top moves,
and cross-office most-bought / most-sold tables. Quarterly cadence — 13Fs are
due 45 days after quarter end.

Usage: python3 scripts/update-trading-whales.py [path/to/whale-13f-YYYY-MM-DD.json]
Run from the repo root.
"""
import datetime as dt
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "trading", "index.html")
SCAN_GLOB = os.path.expanduser("~/Documents/trading/scans/whale-13f-*.json")

# drawn native to the site's ~760px content column: labels above the bars,
# so nothing needs a wide left gutter and the svg renders ~1:1 unscaled
ROW_H, CHART_W, MID, BAR_W = 96, 760, 380, 288


def money(x):
    a = abs(x)
    s = "−" if x < 0 else ("+" if x > 0 else "")
    if a >= 1e9:
        return f"{s}${a/1e9:,.2f}B"
    if a >= 1e6:
        return f"{s}${a/1e6:,.0f}M"
    return f"{s}${a/1e3:,.0f}K"


def qlabel(period):
    d = dt.date.fromisoformat(period)
    return f"Q{(d.month - 1) // 3 + 1} {d.year}"


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        paths = sorted(glob.glob(SCAN_GLOB))
        if not paths:
            sys.exit(f"No JSON matching {SCAN_GLOB}")
        path = paths[-1]
    p = json.load(open(path))
    offices = p["offices"]
    newest = max(o["period"] for o in offices)
    scale_max = max(max(o["buys"], o["sells"]) for o in offices) or 1

    def bl(usd):
        return usd / scale_max * BAR_W

    def short(name, n=22):
        return name if len(name) <= n else name[:n - 1].rstrip() + "…"

    rows = []
    for i, o in enumerate(offices):
        y = i * ROW_H
        by, sy = bl(o["buys"]), bl(o["sells"])
        net_x = MID + max(-BAR_W, min(BAR_W, bl(o["net"])))
        tops = " · ".join(f"{short(m['name'])} {money(m['usd'])}" for m in o["top_moves"][:3])
        stale = f" · ⚠ filings thru {qlabel(o['period'])}" if o["period"] != newest else ""
        rows.append(f"""<g transform="translate(0,{y})">
<text x="0" y="14" class="woff">{o['office']}</text>
<text x="0" y="28" class="wsub">{o['person']} · AUM {money(o['aum']).lstrip('+')} · {o['positions']} pos{stale}</text>
<line x1="{MID}" y1="34" x2="{MID}" y2="58" class="wax"/>
<rect x="{MID - sy:.1f}" y="39" width="{sy:.1f}" height="14" rx="3" class="wsell"><title>sold {money(o['sells'])}</title></rect>
<rect x="{MID}" y="39" width="{by:.1f}" height="14" rx="3" class="wbuy"><title>bought {money(o['buys'])}</title></rect>
<line x1="{net_x:.1f}" y1="35" x2="{net_x:.1f}" y2="57" class="wnet"/>
<text x="{MID - sy - 7:.1f}" y="50" class="wval scan-z-neg" text-anchor="end">{money(-o['sells']) if o['sells'] > 1e5 else ''}</text>
<text x="{MID + by + 7:.1f}" y="50" class="wval scan-z-pos">{money(o['buys']) if o['buys'] > 1e5 else ''}</text>
<text x="{MID}" y="74" class="wtops" text-anchor="middle">net <tspan class="{'scan-z-pos' if o['net'] >= 0 else 'scan-z-neg'}">{money(o['net'])}</tspan> · {tops}</text>
</g>""")
    chart_h = len(offices) * ROW_H

    def cons_rows(rws):
        return "\n".join(
            f"""                    <tr><td class="scan-sym" style="white-space:normal">{r['name']}</td>
                        <td class="scan-num">{r['buyers']}▲ / {r['sellers']}▼</td>
                        <td class="scan-num"><span class="{'scan-z-pos' if r['net'] >= 0 else 'scan-z-neg'}">{money(r['net'])}</span></td></tr>"""
            for r in rws)

    agg = p.get("agg") or {}
    agg_max = max((h["usd"] for h in agg.get("holdings", [])), default=1)
    agg_rows = "\n".join(
        f"""                    <tr><td class="scan-num scan-sec">{i + 1}</td>
                        <td class="scan-sym" style="white-space:normal">{h['name']}</td>
                        <td class="agg-cell"><span class="agg-bar" style="width:{h['usd'] / agg_max * 100:.1f}%"></span></td>
                        <td class="scan-num">{money(h['usd']).lstrip('+')}</td>
                        <td class="scan-num">{h['pct']:.1f}%</td>
                        <td class="scan-num">{h['offices']}</td>
                        <td class="scan-sec" style="white-space:normal">{h['top_holder']}</td></tr>"""
        for i, h in enumerate(agg.get("holdings", [])))
    agg_section = f"""                <div class="position-group"><h3>Where the chips sit · {money(agg.get('total_aum', 0)).lstrip('+')} across {len(offices)} offices · sorted by breadth</h3>
                <div class="scan-table-wrap">
                <table class="scan-table agg-table" aria-label="Aggregate holdings across tracked 13F offices">
                    <thead><tr><th>#</th><th>Issuer</th><th></th><th class="scan-num">Combined $</th><th class="scan-num">% of AUM</th><th class="scan-num">Offices</th><th>Largest holder</th></tr></thead>
                    <tbody>
{agg_rows}
                    </tbody>
                </table>
                </div></div>""" if agg.get("holdings") else ""

    stale_foot = ""
    if p.get("stale"):
        items = " · ".join(f"{s['office']} ({'last 13F ' + qlabel(s['period']) if s['period'] else 'no recent 13F'})"
                           for s in p["stale"])
        stale_foot = f'<p class="trading-note" style="margin-bottom:0;border-top:0;padding-top:0">Not shown: {items}.</p>'

    panel = f"""            <section class="trading-panel whales-panel" id="whales-panel" role="tabpanel" tabindex="0" aria-labelledby="whales-tab" hidden>
                <div class="position-head">
                    <h2 id="whales-heading">13F flows</h2>
                    <span>{qlabel(newest)} filings · quarterly</span>
                </div>
                <p class="scan-intro">Net buying and selling by the most-followed 13F filers, from their latest SEC info tables: share-count changes between the two most recent quarters, priced at quarter-end. Bars diverge from zero — selling left, buying right, the tick marks net flow. 13Fs cover long US positions only and arrive up to 45 days after quarter end, so this is a quarterly, backward-looking map of where the big books moved — not a live signal. Next refresh: ~August 14, when Q2 filings are due.</p>
                <div class="whale-wrap"><svg viewBox="0 0 {CHART_W} {chart_h}" role="img" aria-label="Net 13F flows by investment office">
{''.join(rows)}</svg></div>
{agg_section}
                <div class="whale-cols">
                <div class="position-group"><h3>Most bought across offices</h3>
                <table class="scan-table" aria-label="Most bought issuers across offices"><thead><tr><th>Issuer</th><th class="scan-num">Offices ▲/▼</th><th class="scan-num">Net $</th></tr></thead>
                <tbody>
{cons_rows(p['top_bought'])}
                </tbody></table></div>
                <div class="position-group"><h3>Most sold across offices</h3>
                <table class="scan-table" aria-label="Most sold issuers across offices"><thead><tr><th>Issuer</th><th class="scan-num">Offices ▲/▼</th><th class="scan-num">Net $</th></tr></thead>
                <tbody>
{cons_rows(p['top_sold'])}
                </tbody></table></div>
                </div>
                {stale_foot}
                <p class="trading-note">Method: share-count diffs between each office's two most recent 13F-HR info tables on SEC EDGAR, buys priced at the newer quarter-end, sells at the older. Common shares only — options and principal-amount lines excluded. No shorts, no timing within the quarter, occasional confidential-treatment omissions. Descriptive public-filing data, not recommendations.</p>
            </section>"""

    page = open(PAGE).read()
    new = re.sub(r"(<!-- AUTO:WHALES:START -->).*?(<!-- AUTO:WHALES:END -->)",
                 lambda m: f"{m.group(1)}\n{panel}\n            {m.group(2)}",
                 page, flags=re.S)
    new = re.sub(r'(<span class="trading-tab-count" id="whales-tab-count">)[^<]*(</span>)',
                 lambda m: f"{m.group(1)}{len(offices)}{m.group(2)}", new)
    if new == page:
        sys.exit("No changes made — are the AUTO:WHALES markers present?")
    open(PAGE, "w").write(new)
    print(f"[whales] injected {os.path.basename(path)}: {len(offices)} offices, quarter {newest}")


if __name__ == "__main__":
    main()
