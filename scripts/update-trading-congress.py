#!/usr/bin/env python3
"""Inject Congress YTD STOCK Act flows into trading/index.html (AUTO:CONGRESS block)."""
import datetime as dt
import glob
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "trading", "index.html")
SCAN_GLOBS = [
    os.path.expanduser("~/Documents/trading/scans/congress-ytd-*.json"),
    os.path.join(ROOT, "data", "congress-ytd-*.json"),
]

def money(x):
    if x == 0:
        return "$0"
    a = abs(x)
    s = "−" if x < 0 else ("+" if x > 0 else "")
    if a >= 1e9:
        return f"{s}${a/1e9:,.2f}B"
    if a >= 1e6:
        return f"{s}${a/1e6:,.1f}M"
    if a >= 1e3:
        return f"{s}${a/1e3:,.0f}K"
    return f"{s}${a:,.0f}"

def esc(s):
    return html.escape(str(s or ""))

def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        paths = []
        for g in SCAN_GLOBS:
            paths.extend(glob.glob(g))
        paths = sorted(paths)
        if not paths:
            sys.exit("No congress-ytd-*.json found")
        path = paths[-1]
    p = json.load(open(path))
    s = p["summary"]
    members = p.get("members") or []
    buyers = [m for m in members if m.get("net", 0) > 0][:12]
    sellers = sorted([m for m in members if m.get("net", 0) < 0], key=lambda m: m["net"])[:12]
    cards_src = buyers + sellers
    seen = set()
    cards = []
    for m in cards_src:
        k = m["member"]
        if k in seen:
            continue
        seen.add(k)
        cards.append(m)
    scale_max = max((max(m.get("buy_usd", 0), m.get("sell_usd", 0)) for m in cards), default=1) or 1

    def member_card(m):
        net = m.get("net", 0)
        net_class = "scan-z-pos" if net > 0 else ("scan-z-neg" if net < 0 else "")
        sold_w = max(0, min(100, m.get("sell_usd", 0) / scale_max * 100))
        bought_w = max(0, min(100, m.get("buy_usd", 0) / scale_max * 100))
        chamber = m.get("chamber") or ""
        dst = m.get("state_dst") or ""
        sub = f"{chamber}" + (f" · {dst}" if dst else "") + f" · {m.get('trades', 0)} trades"
        moves_bits = []
        for mv in (m.get("top_moves") or [])[:3]:
            cls = "scan-z-pos" if mv["usd"] >= 0 else "scan-z-neg"
            moves_bits.append(f'<li><span>{esc(mv["name"])}</span><strong class="{cls}">{money(mv["usd"])}</strong></li>')
        moves = "".join(moves_bits) or "<li><span>No ticker-level moves parsed.</span></li>"
        return (
            '                <article class="whale-card">'
            f'\n                    <header class="whale-card-head">'
            f'\n                        <div><h3>{esc(m["member"])}</h3><p>{esc(sub)}</p></div>'
            f'\n                        <div class="whale-net"><span>Net flow</span><strong class="{net_class}">{money(net)}</strong></div>'
            f'\n                    </header>'
            f'\n                    <dl class="whale-flow-stats">'
            f'\n                        <div><dt>Sold</dt><dd class="scan-z-neg">{money(-m.get("sell_usd", 0))}</dd></div>'
            f'\n                        <div><dt>Bought</dt><dd class="scan-z-pos">{money(m.get("buy_usd", 0))}</dd></div>'
            f'\n                        <div><dt>Net</dt><dd class="{net_class}">{money(net)}</dd></div>'
            f'\n                    </dl>'
            f'\n                    <div class="whale-diverge" aria-hidden="true"><span class="whale-sold" style="width:{sold_w:.1f}%"></span><i></i><span class="whale-bought" style="width:{bought_w:.1f}%"></span></div>'
            f'\n                    <h4>Largest ticker flows</h4><ul class="whale-moves">{moves}</ul>'
            f'\n                </article>'
        )

    office_cards = "\n".join(member_card(m) for m in cards)

    def tick_rows(rows, n=15):
        out = []
        for r in rows[:n]:
            net = r.get("net", 0)
            cls = "scan-z-pos" if net > 0 else ("scan-z-neg" if net < 0 else "")
            name = r.get("ticker") or r.get("asset") or "?"
            out.append(
                f'                    <tr><td class="scan-sym">{esc(name)}</td>'
                f'<td class="scan-num">{r.get("buyers", 0)}▲ / {r.get("sellers", 0)}▼</td>'
                f'<td class="scan-num"><span class="{cls}">{money(net)}</span></td></tr>'
            )
        return "\n".join(out)

    def large_rows(rows, n=20):
        out = []
        for r in rows[:n]:
            flow = r.get("flow_est", 0)
            cls = "scan-z-pos" if flow > 0 else ("scan-z-neg" if flow < 0 else "")
            tick = r.get("ticker") or "?"
            link = r.get("source_url") or ""
            if link:
                sym = f'<a href="{esc(link)}" rel="noopener noreferrer" target="_blank">{esc(tick)}</a>'
            else:
                sym = esc(tick)
            out.append(
                f'                    <tr><td class="scan-sym" style="white-space:normal">{esc(r.get("member"))}</td>'
                f'<td>{esc(r.get("chamber"))}</td>'
                f'<td class="scan-sym">{sym}</td>'
                f'<td>{esc(r.get("side"))}</td>'
                f'<td class="scan-num"><span class="{cls}">{esc(r.get("amount_label") or money(flow))}</span></td>'
                f'<td class="scan-num">{esc(r.get("transaction_date"))}</td>'
                f'<td class="scan-num">{esc(r.get("filing_date"))}</td></tr>'
            )
        return "\n".join(out)

    as_of = p.get("as_of") or dt.date.today().isoformat()
    year = p.get("year") or 2026
    net = s.get("net_usd", 0)
    net_cls = "scan-z-pos" if net >= 0 else "scan-z-neg"
    panel_lines = [
        '            <section class="trading-panel congress-panel" id="congress-panel" role="tabpanel" tabindex="0" aria-labelledby="congress-tab" hidden>',
        '                <div class="position-head">',
        f'                    <h2 id="congress-heading">Congress flows</h2>',
        f'                    <span>{year} YTD · as of {esc(as_of)}</span>',
        '                </div>',
        '                <p class="scan-intro">Official STOCK Act periodic transaction reports for sitting House members and Senators year-to-date. Dollar figures are midpoint estimates from disclosure ranges (e.g. $15,001–$50,000 → ~$32.5K), not exact fills. Transaction date ≠ filing date — members can report weeks later. Paper Senate filings are excluded. Descriptive public-filing data, not trade recommendations.</p>',
        '                <section class="whale-summary" aria-label="Congress flow summary">',
        f'                    <div><span>Members</span><strong>{s.get("members", 0)}</strong><small>{s.get("house_members", 0)} House · {s.get("senate_members", 0)} Senate</small></div>',
        f'                    <div><span>Trades</span><strong>{s.get("trades", 0):,}</strong><small>{s.get("house_trades", 0):,} House · {s.get("senate_trades", 0):,} Senate</small></div>',
        f'                    <div><span>Gross sold</span><strong class="scan-z-neg">{money(-s.get("gross_sell_usd", 0))}</strong></div>',
        f'                    <div><span>Gross bought</span><strong class="scan-z-pos">{money(s.get("gross_buy_usd", 0))}</strong></div>',
        f'                    <div><span>Net flow</span><strong class="{net_cls}">{money(net)}</strong><small>{s.get("net_buyers", 0)} net buyers · {s.get("net_sellers", 0)} net sellers</small></div>',
        '                </section>',
        '                <div class="whale-flow-head"><h3>Member flows</h3><p>Top net buyers and sellers · bars share one scale · range midpoints</p></div>',
        '                <section class="whale-flow-grid" aria-label="YTD flows by member">',
        office_cards,
        '                </section>',
        '                <div class="whale-cols">',
        '                <div class="position-group"><h3>Most bought tickers</h3>',
        '                <table class="scan-table" aria-label="Most bought tickers by Congress YTD"><thead><tr><th>Ticker</th><th class="scan-num">Members ▲/▼</th><th class="scan-num">Net $</th></tr></thead>',
        '                <tbody>',
        tick_rows(p.get("top_bought") or []),
        '                </tbody></table></div>',
        '                <div class="position-group"><h3>Most sold tickers</h3>',
        '                <table class="scan-table" aria-label="Most sold tickers by Congress YTD"><thead><tr><th>Ticker</th><th class="scan-num">Members ▲/▼</th><th class="scan-num">Net $</th></tr></thead>',
        '                <tbody>',
        tick_rows(p.get("top_sold") or []),
        '                </tbody></table></div>',
        '                </div>',
        '                <div class="position-group"><h3>Largest disclosed trades</h3>',
        '                <div class="scan-table-wrap">',
        '                <table class="scan-table" aria-label="Largest Congress trades YTD">',
        '                    <thead><tr><th>Member</th><th>Chamber</th><th>Ticker</th><th>Side</th><th class="scan-num">Amount</th><th class="scan-num">Tx date</th><th class="scan-num">Filed</th></tr></thead>',
        '                    <tbody>',
        large_rows(p.get("largest_trades") or []),
        '                    </tbody>',
        '                </table>',
        '                </div></div>',
        '                <p class="trading-note">Sources: House Clerk bulk FD index + PTR PDFs; Senate eFD electronic PTRs. Amounts are statutory ranges; midpoints used only for ranking/aggregation. Spouse/joint/dependent transactions are included when disclosed on the member filing. Not investment advice.</p>',
        '            </section>',
    ]
    panel = "\n".join(panel_lines)

    page = open(PAGE).read()
    if 'id="congress-tab"' not in page:
        page = page.replace(
            '<button class="trading-tab" id="whales-tab"',
            '<button class="trading-tab" id="congress-tab" type="button" role="tab" aria-selected="false" aria-controls="congress-panel">Congress flows <span class="trading-tab-count" id="congress-tab-count">0</span></button>\n                <button class="trading-tab" id="whales-tab"',
            1,
        )
    if "<!-- AUTO:CONGRESS:START -->" not in page:
        page = page.replace(
            "<!-- AUTO:WHALES:START -->",
            "<!-- AUTO:CONGRESS:START -->\n            <!-- AUTO:CONGRESS:END -->\n\n            <!-- AUTO:WHALES:START -->",
            1,
        )
    new = re.sub(
        r"(<!-- AUTO:CONGRESS:START -->).*?(<!-- AUTO:CONGRESS:END -->)",
        lambda m: f"{m.group(1)}\n{panel}\n            {m.group(2)}",
        page,
        flags=re.S,
    )
    new = re.sub(
        r'(<span class="trading-tab-count" id="congress-tab-count">)[^<]*(</span>)',
        lambda m: f"{m.group(1)}{s.get('members', 0)}{m.group(2)}",
        new,
    )
    open(PAGE, "w").write(new)
    print(f"[congress] injected {os.path.basename(path)}: {s.get('members')} members, {s.get('trades')} trades, net {money(net)}")

if __name__ == "__main__":
    main()
