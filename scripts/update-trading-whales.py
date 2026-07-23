#!/usr/bin/env python3
"""Inject 13F whale flows into trading/index.html (AUTO:WHALES block).

Reads the newest ~/trading/scans/whale-13f-*.json (or a path given
as argv[1]) emitted by ~/trading/src/whale_13f.py and renders the
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
SCAN_GLOB = os.path.expanduser("~/trading/scans/whale-13f-*.json")

def money(x):
    if x == 0:
        return "$0"
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
        stale = (f'<span class="whale-stale">Older filing · {qlabel(o["period"])}</span>'
                 if o["period"] != newest else "")
        moves = "".join(
            f'<li><span>{html.escape(move["name"])}</span><strong class="{"scan-z-pos" if move["usd"] >= 0 else "scan-z-neg"}">{money(move["usd"])}</strong></li>'
            for move in o["top_moves"][:3])
        if not moves:
            moves = '<li><span>No reportable share-count changes.</span></li>'
        sold_width = max(0, min(100, o["sells"] / scale_max * 100))
        bought_width = max(0, min(100, o["buys"] / scale_max * 100))
        net_class = "scan-z-pos" if o["net"] > 0 else ("scan-z-neg" if o["net"] < 0 else "")
        office_cards.append(f"""                <details class="whale-card">
                    <summary class="whale-card-head">
                        <span><b>{html.escape(o['office'])}</b><small>{html.escape(o['person'])} · AUM {money(o['aum']).lstrip('+')} · {o['positions']} positions {stale}</small></span>
                        <span class="whale-net"><span>Net flow</span><strong class="{net_class}">{money(o['net'])}</strong></span>
                    </summary>
                    <dl class="whale-flow-stats">
                        <div><dt>Sold</dt><dd class="scan-z-neg">{money(-o['sells'])}</dd></div>
                        <div><dt>Bought</dt><dd class="scan-z-pos">{money(o['buys'])}</dd></div>
                        <div><dt>Net</dt><dd class="{net_class}">{money(o['net'])}</dd></div>
                    </dl>
                    <div class="whale-diverge" aria-hidden="true"><span class="whale-sold" style="width:{sold_width:.1f}%"></span><i></i><span class="whale-bought" style="width:{bought_width:.1f}%"></span></div>
                    <h4>Largest position changes</h4><ul class="whale-moves">{moves}</ul>
                </details>""")

    gross_bought = sum(o["buys"] for o in offices)
    gross_sold = sum(o["sells"] for o in offices)
    total_net = gross_bought - gross_sold
    combined_aum = sum(o["aum"] for o in offices)
    net_buyers = sum(o["net"] > 0 for o in offices)

    def cons_rows(rws):
        return "\n".join(
            f"""                    <tr><td class="scan-sym" style="white-space:normal">{html.escape(r['name'])}</td>
                        <td class="scan-num">{r['buyers']}▲ / {r['sellers']}▼</td>
                        <td class="scan-num"><span class="{'scan-z-pos' if r['net'] > 0 else ('scan-z-neg' if r['net'] < 0 else '')}">{money(r['net'])}</span></td></tr>"""
            for r in rws)

    agg = p.get("agg") or {}
    agg_max = max((h["usd"] for h in agg.get("holdings", [])), default=1)
    agg_rows = "\n".join(
        f"""                    <tr><td class="scan-num scan-sec">{i + 1}</td>
                        <td class="scan-sym" style="white-space:normal">{html.escape(h['name'])}</td>
                        <td class="agg-cell"><span class="agg-bar" style="width:{h['usd'] / agg_max * 100:.1f}%"></span></td>
                        <td class="scan-num">{money(h['usd']).lstrip('+')}</td>
                        <td class="scan-num">{h['pct']:.1f}%</td>
                        <td class="scan-num">{h['offices']}</td>
                        <td class="scan-sec" style="white-space:normal">{html.escape(h['top_holder'])}</td></tr>"""
        for i, h in enumerate(agg.get("holdings", [])))
    agg_section = f"""                <details class="data-disclosure"><summary>View shared holdings · {len(agg.get('holdings', []))}</summary>
                <div class="scan-table-wrap">
                <table class="scan-table agg-table" aria-label="Aggregate holdings across tracked 13F offices">
                    <thead><tr><th>#</th><th>Issuer</th><th></th><th class="scan-num">Combined $</th><th class="scan-num">% of AUM</th><th class="scan-num">Offices</th><th>Largest holder</th></tr></thead>
                    <tbody>
{agg_rows}
                    </tbody>
                </table>
                </div></details>""" if agg.get("holdings") else ""

    stale_foot = ""
    if p.get("stale"):
        items = " · ".join(f"{html.escape(s['office'])} ({'last 13F ' + qlabel(s['period']) if s['period'] else 'no recent 13F'})"
                           for s in p["stale"])
        stale_foot = f'<p class="trading-note" style="margin-bottom:0;border-top:0;padding-top:0">Not shown: {items}.</p>'

    panel = f"""            <section class="trading-panel whales-panel" id="whales-panel" role="tabpanel" tabindex="0" aria-labelledby="whales-tab" hidden>
                <div class="position-head">
                    <h2 id="whales-heading">13F</h2>
                    <span>{qlabel(newest)} filings · quarterly</span>
                </div>
                <p class="trading-takeaway">Tracked managers {'bought' if total_net >= 0 else 'sold'} {money(abs(total_net)).lstrip('+−')} net; {net_buyers} of {len(offices)} were net buyers.</p>
                <p class="data-meta">Combined AUM {money(combined_aum).lstrip('+')} · gross bought {money(gross_bought)} · gross sold {money(-gross_sold)}</p>
                {stale_foot}
                <div class="whale-cols whale-consensus">
                <div class="position-group"><h3>Most bought across offices · top 20</h3>
                <table class="scan-table" aria-label="Most bought issuers across offices"><thead><tr><th>Issuer</th><th class="scan-num">Offices ▲/▼</th><th class="scan-num">Net $</th></tr></thead>
                <tbody>
{cons_rows(p['top_bought'][:20])}
                </tbody></table></div>
                <div class="position-group"><h3>Most sold across offices · top 20</h3>
                <table class="scan-table" aria-label="Most sold issuers across offices"><thead><tr><th>Issuer</th><th class="scan-num">Offices ▲/▼</th><th class="scan-num">Net $</th></tr></thead>
                <tbody>
{cons_rows(p['top_sold'][:20])}
                </tbody></table></div>
                </div>
                <div class="whale-flow-head"><h3>Manager flows</h3><p>Sorted by net flow · open a manager for details</p></div>
                <section class="whale-flow-grid" aria-label="Quarterly flows by investment office">
{os.linesep.join(office_cards)}
                </section>
{agg_section}
                <details class="trading-method"><summary>How this works</summary><p>13F filings show quarter-over-quarter changes in long US holdings and arrive up to 45 days after quarter end. Flows estimate share-count changes using quarter-end prices. They exclude shorts, hide timing within the quarter, and may omit confidential positions. This is a backward-looking allocation map, not a live signal.</p></details>
            </section>"""

    page = open(PAGE).read()
    new = re.sub(r"(<!-- AUTO:WHALES:START -->).*?(<!-- AUTO:WHALES:END -->)",
                 lambda m: f"{m.group(1)}\n{panel}\n            {m.group(2)}",
                 page, flags=re.S)
    if new == page:
        print(f"[whales] already current: {os.path.basename(path)}, {len(offices)} offices, quarter {newest}")
        return
    open(PAGE, "w").write(new)
    print(f"[whales] injected {os.path.basename(path)}: {len(offices)} offices, quarter {newest}")


if __name__ == "__main__":
    main()
