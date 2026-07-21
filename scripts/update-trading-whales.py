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
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "trading", "index.html")
SCAN_GLOB = os.path.expanduser("~/Documents/trading/scans/whale-13f-*.json")

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
    offices = sorted(p["offices"], key=lambda office: office["net"], reverse=True)
    newest = max(o["period"] for o in offices)
    scale_max = max(max(o["buys"], o["sells"]) for o in offices) or 1

    office_cards = []
    for o in offices:
        stale = (f'<span class="whale-stale">⚠ Through {qlabel(o["period"])}</span>'
                 if o["period"] != newest else "")
        moves = "".join(
            f'<li><span>{html.escape(move["name"])}</span><strong class="{"scan-z-pos" if move["usd"] >= 0 else "scan-z-neg"}">{money(move["usd"])}</strong></li>'
            for move in o["top_moves"][:3])
        sold_width = o["sells"] / scale_max * 100
        bought_width = o["buys"] / scale_max * 100
        net_class = "scan-z-pos" if o["net"] >= 0 else "scan-z-neg"
        office_cards.append(f"""                <article class="whale-card">
                    <header class="whale-card-head">
                        <div><h3>{html.escape(o['office'])}</h3><p>{html.escape(o['person'])} · AUM {money(o['aum']).lstrip('+')} · {o['positions']} positions {stale}</p></div>
                        <div class="whale-net"><span>Net flow</span><strong class="{net_class}">{money(o['net'])}</strong></div>
                    </header>
                    <dl class="whale-flow-stats">
                        <div><dt>Sold</dt><dd class="scan-z-neg">{money(-o['sells'])}</dd></div>
                        <div><dt>Bought</dt><dd class="scan-z-pos">{money(o['buys'])}</dd></div>
                        <div><dt>Net</dt><dd class="{net_class}">{money(o['net'])}</dd></div>
                    </dl>
                    <div class="whale-diverge" aria-hidden="true"><span class="whale-sold" style="width:{sold_width:.1f}%"></span><i></i><span class="whale-bought" style="width:{bought_width:.1f}%"></span></div>
                    <h4>Largest position changes</h4><ul class="whale-moves">{moves}</ul>
                </article>""")

    gross_bought = sum(o["buys"] for o in offices)
    gross_sold = sum(o["sells"] for o in offices)
    total_net = sum(o["net"] for o in offices)
    net_buyers = sum(o["net"] >= 0 for o in offices)

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
                <p class="scan-intro">Quarter-over-quarter buying and selling from the latest SEC 13F information tables. Read each card left to right: gross sales, gross purchases, then net flow; the bar shows their relative scale and the list isolates each office’s three largest position changes. 13Fs cover long US positions only and arrive up to 45 days after quarter end, so this is a backward-looking allocation map—not a live signal. Next refresh: ~August 14, when Q2 filings are due.</p>
                <section class="whale-summary" aria-label="13F flow summary">
                    <div><span>Gross sold</span><strong class="scan-z-neg">{money(-gross_sold)}</strong></div>
                    <div><span>Gross bought</span><strong class="scan-z-pos">{money(gross_bought)}</strong></div>
                    <div><span>Net across offices</span><strong class="{'scan-z-pos' if total_net >= 0 else 'scan-z-neg'}">{money(total_net)}</strong></div>
                    <div><span>Net buyers</span><strong>{net_buyers} of {len(offices)}</strong></div>
                </section>
                <section class="whale-flow-grid" aria-label="Quarterly flows by investment office">
{os.linesep.join(office_cards)}
                </section>
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
        print(f"[whales] already current: {os.path.basename(path)}, {len(offices)} offices, quarter {newest}")
        return
    open(PAGE, "w").write(new)
    print(f"[whales] injected {os.path.basename(path)}: {len(offices)} offices, quarter {newest}")


if __name__ == "__main__":
    main()
