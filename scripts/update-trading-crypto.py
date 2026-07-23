#!/usr/bin/env python3
"""Inject the altcoin dashboard into trading/index.html (AUTO:CRYPTO block).

Reads the newest ~/Documents/trading/scans/crypto-spread-*.json (or a path
given as argv[1]) emitted by ~/Documents/trading/src/crypto_spread.py and
renders the "Crypto spread" tab: spread-Z vs BTC (Allen z-score, the same
spec the equity scan uses against SPY) plus year-anchored VWAPs, all built
from Hyperliquid perp candles (native-venue volume, daily UTC sessions).

Usage: python3 scripts/update-trading-crypto.py [path/to/crypto-spread-YYYY-MM-DD.json]
Run from the repo root.
"""
import datetime as dt
import glob
import html
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "trading", "index.html")
SCAN_GLOB = os.path.expanduser("~/trading/scans/crypto-spread-*.json")

W, H = 560, 210
ML, MR, MT, MB = 10, 52, 12, 24


def fmt(d):
    return dt.date.fromisoformat(d).strftime("%b %-d")


def fmt_price(v):
    return f"${v:,.2f}" if v >= 2 else f"${v:,.4f}"


def fmt_axis(v, hi):
    if hi >= 100:
        return f"{v:,.0f}"
    if hi >= 2:
        return f"{v:,.2f}"
    return f"{v:,.4f}"


def spread_chart(coin):
    dates = coin["series"]["dates"]
    sp = coin["series"]["spread"]
    n = len(dates)
    if n < 2:
        return ""
    zmax = max(1.5, max(abs(v) for v in sp) * 1.15)
    iw, ih = W - ML - MR, H - MT - MB

    def x(i):
        return ML + i / (n - 1) * iw

    def y(v):
        return MT + (zmax - v) / (2 * zmax) * ih

    parts = []
    months = [d[5:7] for d in dates]
    for i in range(1, n):
        if months[i] != months[i - 1]:
            parts.append(f'<line x1="{x(i):.1f}" y1="{MT}" x2="{x(i):.1f}" y2="{MT + ih}" class="cg"/>'
                         f'<text x="{x(i):.1f}" y="{H - 8}" class="ca" text-anchor="middle">{dt.date.fromisoformat(dates[i]).strftime("%b")}</text>')
    parts.append(f'<line x1="{ML}" y1="{y(0):.1f}" x2="{ML + iw}" y2="{y(0):.1f}" class="czero"/>')
    for lvl in (1, -1):
        if abs(lvl) < zmax:
            parts.append(f'<line x1="{ML}" y1="{y(lvl):.1f}" x2="{ML + iw}" y2="{y(lvl):.1f}" class="clvl"/>'
                         f'<text x="{ML + iw + 6}" y="{y(lvl) + 3.5:.1f}" class="ca">{lvl:+d}</text>')
    parts.append(f'<text x="{ML + iw + 6}" y="{y(0) + 3.5:.1f}" class="ca">0</text>')
    for i in range(1, n):
        cls = "cpos" if sp[i] >= 0 else "cneg"
        parts.append(f'<line x1="{x(i - 1):.1f}" y1="{y(sp[i - 1]):.1f}" x2="{x(i):.1f}" y2="{y(sp[i]):.1f}" class="{cls}" stroke-width="1.8"><title>{fmt(dates[i])}: {sp[i]:+.2f}</title></line>')
    last = sp[-1]
    parts.append(f'<text x="{W - 2}" y="{y(last) + 3.5:.1f}" class="ctag" fill="{"#0f8a4d" if last >= 0 else "#c93a4a"}" text-anchor="end">{last:+.2f}</text>')
    side = "leading" if last >= 0 else "lagging"
    return f"""                <figure class="crypto-card">
                    <figcaption><b>{html.escape(coin['sym'])}</b> <span>{html.escape(coin['name'])} · vs BTC</span><em class="{'scan-z-pos' if last >= 0 else 'scan-z-neg'}">{last:+.2f} · {side} {coin['days_side']}d</em></figcaption>
                    <svg viewBox="0 0 {W} {H}" preserveAspectRatio="none" role="img" aria-label="{html.escape(coin['sym'])} spread Z versus BTC, year to date">{''.join(parts)}</svg>
                </figure>"""


def vwap_chart(b):
    dates, close, vw = b["series"]["dates"], b["series"]["close"], b["series"]["vwap"]
    n = len(dates)
    if n < 2:
        return ""
    lo = min(min(close), min(vw))
    hi = max(max(close), max(vw))
    pad = (hi - lo) * 0.06 or 1
    lo, hi = lo - pad, hi + pad
    iw, ih = W - ML - MR, H - MT - MB

    def x(i):
        return ML + i / (n - 1) * iw

    def y(v):
        return MT + (hi - v) / (hi - lo) * ih

    parts = []
    months = [d[5:7] for d in dates]
    for i in range(1, n):
        if months[i] != months[i - 1]:
            parts.append(f'<line x1="{x(i):.1f}" y1="{MT}" x2="{x(i):.1f}" y2="{MT + ih}" class="cg"/>'
                         f'<text x="{x(i):.1f}" y="{H - 8}" class="ca" text-anchor="middle">{dt.date.fromisoformat(dates[i]).strftime("%b")}</text>')
    for k in range(4):
        v = lo + (hi - lo) * k / 3
        parts.append(f'<line x1="{ML}" y1="{y(v):.1f}" x2="{ML + iw}" y2="{y(v):.1f}" class="cg"/>'
                     f'<text x="{ML + iw + 6}" y="{y(v) + 3.5:.1f}" class="ca">{fmt_axis(v, hi)}</text>')
    diff = [a - bb for a, bb in zip(close, vw)]
    run = [0]

    def flush(run, sign):
        pts = [f"{x(j):.1f},{y(close[j]):.1f}" for j in run] + [f"{x(j):.1f},{y(vw[j]):.1f}" for j in reversed(run)]
        parts.append(f'<polygon points="{" ".join(pts)}" class="{"cvfp" if sign else "cvfn"}"/>')

    for i in range(1, n):
        if (diff[i] >= 0) != (diff[i - 1] >= 0):
            run.append(i)
            flush(run, diff[i - 1] >= 0)
            run = [i]
        else:
            run.append(i)
    if len(run) > 1:
        flush(run, diff[-1] >= 0)
    parts.append('<polyline points="' + " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vw)) + '" fill="none" class="cvlv"/>')
    parts.append('<polyline points="' + " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(close)) + '" fill="none" class="cvlp"/>')
    side = diff[-1] >= 0
    return f"""                <figure class="crypto-card">
                    <figcaption><b>{html.escape(b["sym"])}</b> <span>{html.escape(b["name"])} · YTD VWAP</span><em class="{"scan-z-pos" if side else "scan-z-neg"}">{b["pct"]:+.1f}% {"above" if side else "below"} · {b["held"]}d</em></figcaption>
                    <svg viewBox="0 0 {W} {H}" preserveAspectRatio="none" role="img" aria-label="{html.escape(b["sym"])} price versus year-to-date VWAP">{"".join(parts)}</svg>
                </figure>"""


def combined_chart(coin, vwap):
    spread_card = spread_chart(coin)
    vwap_card = vwap_chart(vwap)
    spread_match = re.search(r"<svg[^>]*>(.*)</svg>", spread_card, re.S)
    vwap_match = re.search(r"<svg[^>]*>(.*)</svg>", vwap_card, re.S)
    if not spread_match or not vwap_match:
        raise ValueError(f"Could not compose {coin['sym']} crypto chart")
    total_h = H * 2 + 24
    spread = coin["spread"]
    side = "leading" if spread >= 0 else "lagging"
    return f"""                <figure class="crypto-card crypto-card--combined" data-symbol="{html.escape(coin['sym'])}" data-spread-z="{spread:.6f}">
                    <figcaption><b>{html.escape(coin['sym'])}</b> <span>{html.escape(coin['name'])} · YTD VWAP + Spread Z vs BTC</span><em class="{'scan-z-pos' if spread >= 0 else 'scan-z-neg'}">z {spread:+.2f} · {side} · {vwap['pct']:+.1f}% vs vwap</em></figcaption>
                    <svg viewBox="0 0 {W} {total_h}" preserveAspectRatio="none" role="img" aria-label="{html.escape(coin['sym'])} price versus YTD VWAP with spread Z versus BTC below">
                        <text x="{ML}" y="10" class="crypto-subtitle">PRICE · YTD VWAP</text>
                        <g>{vwap_match.group(1)}</g>
                        <line x1="{ML}" y1="{H + 10}" x2="{W - MR}" y2="{H + 10}" class="cg"/>
                        <text x="{ML}" y="{H + 22}" class="crypto-subtitle">SPREAD Z VS BTC</text>
                        <g transform="translate(0,{H + 24})">{spread_match.group(1)}</g>
                    </svg>
                </figure>"""


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        paths = sorted(glob.glob(SCAN_GLOB))
        if not paths:
            sys.exit(f"No JSON matching {SCAN_GLOB}")
        path = paths[-1]
    p = json.load(open(path))
    expected = {"ZEC", "ETH", "SOL", "HYPE", "XRP", "BNB", "DOGE"}
    raw_coins = p.get("coins", [])
    if {coin.get("sym") for coin in raw_coins} != expected or len(raw_coins) != len(expected):
        sys.exit("Expected exactly the seven tracked crypto symbols")
    coins = sorted(raw_coins, key=lambda c: (-c["spread"], c["sym"]))
    vwap_by_symbol = {item["sym"]: item for item in p.get("vwap_native", [])}
    if set(vwap_by_symbol) != expected or len(p.get("vwap_native", [])) != len(expected):
        sys.exit("Crypto spread and VWAP symbol sets do not match")
    for coin in coins:
        series = coin.get("series", {})
        dates, spread = series.get("dates", []), series.get("spread", [])
        if len(dates) < 2 or len(dates) != len(spread) or dates != sorted(set(dates)):
            sys.exit(f"Invalid spread history for {coin['sym']}")
        if dates[-1] != p["last_bar"] or not all(math.isfinite(value) for value in spread):
            sys.exit(f"Stale or non-finite spread history for {coin['sym']}")
        if round(spread[-1], 6) != round(coin["spread"], 6):
            sys.exit(f"Current spread does not match history for {coin['sym']}")
        vwap = vwap_by_symbol[coin["sym"]]
        vseries = vwap.get("series", {})
        vd, close, basis = vseries.get("dates", []), vseries.get("close", []), vseries.get("vwap", [])
        if len(vd) < 2 or not (len(vd) == len(close) == len(basis)) or vd != sorted(set(vd)):
            sys.exit(f"Invalid VWAP history for {coin['sym']}")
        if vd[-1] != p["last_bar"] or not all(math.isfinite(value) for value in close + basis):
            sys.exit(f"Stale or non-finite VWAP history for {coin['sym']}")
    vwaps = [vwap_by_symbol[coin["sym"]] for coin in coins]

    rows = "\n".join(
        f"""                    <tr>
                        <td class="scan-sym">{html.escape(c['sym'])}</td>
                        <td class="scan-sec">{html.escape(c['name'])}</td>
                        <td class="scan-num">{fmt_price(c['price'])}</td>
                        <td class="scan-num">{fmt_price(b['vwap'])}</td>
                        <td class="scan-num"><span class="{'scan-z-pos' if b['side'] else 'scan-z-neg'}">{b['pct']:+.1f}%</span></td>
                        <td class="scan-num">{'▲' if b['side'] else '▼'} {b['held']}d</td>
                        <td class="scan-num"><span class="{'scan-z-pos' if c['z'] >= 0 else 'scan-z-neg'}">{c['z']:+.2f}</span></td>
                        <td class="scan-num"><span class="{'scan-z-pos' if c['spread'] >= 0 else 'scan-z-neg'}">{c['spread']:+.2f}</span></td>
                        <td class="scan-num">{'▲' if c['spread'] >= 0 else '▼'} {c['days_side']}d</td>
                        <td class="scan-num"><span class="{'scan-z-pos' if c['ratio_ytd_chg'] >= 0 else 'scan-z-neg'}">{c['ratio_ytd_chg']:+.1f}%</span></td>
                    </tr>"""
        for c in coins for b in [vwap_by_symbol[c["sym"]]])
    charts = "\n".join(combined_chart(c, vwap_by_symbol[c["sym"]]) for c in coins)

    panel = f"""            <section class="trading-panel crypto-panel" id="crypto-panel" role="tabpanel" tabindex="0" aria-labelledby="crypto-tab" hidden>
                <div class="position-head">
                    <h2 id="crypto-heading">Crypto spread</h2>
                    <span>{fmt(p['last_bar'])} UTC close · daily · benchmark BTC {'' if not p.get('btc') else f"${p['btc']['price']:,.0f} · z {p['btc']['z']:+.2f}"}</span>
                </div>
                <p class="scan-intro">Altcoin relative strength measured the way the equity scan measures stocks against SPY: each coin's 50-day EMA z-score minus bitcoin's. Positive and green = the alt is more extended above its own trend than BTC is (vol-adjusted leadership); negative and red = it's lagging the benchmark. The table and combined charts are ranked by current Spread Z descending. All data is daily UTC perp candles from Hyperliquid; the last bar is the most recent complete day.</p>
                <p class="scan-intro">YTD VWAP is the year's average cost basis per coin, volume-weighted on Hyperliquid's perp markets. Above the line, the year's buyers are in profit and defend dips; below it, rallies meet trapped sellers.</p>
                <div class="scan-table-wrap">
                <table class="scan-table" aria-label="Altcoin spread Z versus BTC and year-to-date VWAPs">
                    <thead><tr><th>Coin</th><th>Name</th><th class="scan-num">Price</th><th class="scan-num">YTD VWAP</th><th class="scan-num">vs VWAP</th><th class="scan-num">VWAP side</th><th class="scan-num">Coin Z</th><th class="scan-num">Spread vs BTC</th><th class="scan-num">Spread side</th><th class="scan-num">Alt/BTC YTD</th></tr></thead>
                    <tbody>
{rows}
                    </tbody>
                </table>
                </div>
                <div class="position-group"><h3>Combined charts · ranked by Spread Z</h3></div>
                <div class="crypto-grid">
{charts}
                </div>
                <p class="trading-note">Spread Z uses the same EMA-based z-score as the momentum scan (EMA-50 mean, EMA-RMS sigma, EMA-3 smoothing). All prices and volume are daily UTC perp candles from Hyperliquid's public API — perp volume tracks spot closely and is the deepest liquidity for these names; crypto has no consolidated tape. A z-spread compares each asset to its own trend — it is relative momentum, not a price-ratio chart. Descriptive market data, not recommendations.</p>
            </section>"""

    page = open(PAGE).read()
    new = re.sub(r"(<!-- AUTO:CRYPTO:START -->).*?(<!-- AUTO:CRYPTO:END -->)",
                 lambda m: f"{m.group(1)}\n{panel}\n            {m.group(2)}",
                 page, flags=re.S)
    new = re.sub(r'(<span class="trading-tab-count" id="crypto-tab-count">)[^<]*(</span>)',
                 lambda m: f"{m.group(1)}{len(coins)}{m.group(2)}", new)
    if new == page:
        print(f"[crypto] already current: {os.path.basename(path)}, {len(coins)} coins, {len(vwaps)} vwaps, last bar {p['last_bar']}")
        return
    open(PAGE, "w").write(new)
    print(f"[crypto] injected {os.path.basename(path)}: {len(coins)} coins, {len(vwaps)} vwaps, last bar {p['last_bar']}")


if __name__ == "__main__":
    main()
