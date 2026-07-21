#!/usr/bin/env python3
"""Inject the altcoin spread-Z panel into trading/index.html (AUTO:CRYPTO block).

Reads the newest ~/Documents/trading/scans/crypto-spread-*.json (or a path
given as argv[1]) emitted by ~/Documents/trading/src/crypto_spread.py and
renders the "Crypto spread" tab: summary table plus one YTD spread-Z chart
per altcoin (HYPE, ETH, SOL), each measured against BTC with the same
EMA-based z-score the equity scan uses against SPY. Daily cadence.

Usage: python3 scripts/update-trading-crypto.py [path/to/crypto-spread-YYYY-MM-DD.json]
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
SCAN_GLOB = os.path.expanduser("~/Documents/trading/scans/crypto-spread-*.json")

W, H = 560, 210
ML, MR, MT, MB = 10, 52, 12, 24


def fmt(d):
    return dt.date.fromisoformat(d).strftime("%b %-d")


def chart(coin):
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
    lo = min(min(close), min(vw)); hi = max(max(close), max(vw))
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
        fmtv = f"{v:,.0f}" if hi >= 100 else f"{v:,.2f}"
        parts.append(f'<line x1="{ML}" y1="{y(v):.1f}" x2="{ML + iw}" y2="{y(v):.1f}" class="cg"/>'
                     f'<text x="{ML + iw + 6}" y="{y(v) + 3.5:.1f}" class="ca">{fmtv}</text>')
    diff = [a - bb for a, bb in zip(close, vw)]
    run = [0]

    def flush(run, sign):
        pts = [f"{x(j):.1f},{y(close[j]):.1f}" for j in run] + [f"{x(j):.1f},{y(vw[j]):.1f}" for j in reversed(run)]
        parts.append(f'<polygon points="{" ".join(pts)}" class="{"cvfp" if sign else "cvfn"}"/>')

    for i in range(1, n):
        if (diff[i] >= 0) != (diff[i - 1] >= 0):
            run.append(i); flush(run, diff[i - 1] >= 0); run = [i]
        else:
            run.append(i)
    if len(run) > 1:
        flush(run, diff[-1] >= 0)
    parts.append('<polyline points="' + " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vw)) + '" fill="none" class="cvlv"/>')
    parts.append('<polyline points="' + " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(close)) + '" fill="none" class="cvlp"/>')
    side = diff[-1] >= 0
    return f"""                <figure class="crypto-card">
                    <figcaption><b>{html.escape(b["sym"])}</b> <span>{html.escape(b["name"])} · {html.escape(b["note"])}</span><em class="{"scan-z-pos" if side else "scan-z-neg"}">{b["pct"]:+.1f}% {"above" if side else "below"} · {b["held"]}d</em></figcaption>
                    <svg viewBox="0 0 {W} {H}" preserveAspectRatio="none" role="img" aria-label="{html.escape(b["sym"])} price versus year-to-date VWAP">{"".join(parts)}</svg>
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
    coins = p["coins"]

    rows = "\n".join(
        f"""                    <tr>
                        <td class="scan-sym">{html.escape(c['sym'])}</td>
                        <td class="scan-sec">{html.escape(c['name'])}</td>
                        <td class="scan-num">${c['price']:,.2f}</td>
                        <td class="scan-num"><span class="{'scan-z-pos' if c['z'] >= 0 else 'scan-z-neg'}">{c['z']:+.2f}</span></td>
                        <td class="scan-num"><span class="{'scan-z-pos' if c['spread'] >= 0 else 'scan-z-neg'}">{c['spread']:+.2f}</span></td>
                        <td class="scan-num">{'▲' if c['spread'] >= 0 else '▼'} {c['days_side']}d</td>
                        <td class="scan-num"><span class="{'scan-z-pos' if c['ratio_ytd_chg'] >= 0 else 'scan-z-neg'}">{c['ratio_ytd_chg']:+.1f}%</span></td>
                    </tr>"""
        for c in sorted(coins, key=lambda c: -c["spread"]))
    charts = "\n".join(chart(c) for c in sorted(coins, key=lambda c: -c["spread"]))

    vw_rows = "\n".join(
        f"""                    <tr>
                        <td class="scan-sym">{html.escape(b['sym'])}</td>
                        <td class="scan-sec">{html.escape(b['name'])} · {html.escape(b['note'])}</td>
                        <td class="scan-num">${b['price']:,.2f}</td>
                        <td class="scan-num">${b['vwap']:,.2f}</td>
                        <td class="scan-num"><span class="{'scan-z-pos' if b['side'] else 'scan-z-neg'}">{b['pct']:+.1f}%</span></td>
                        <td class="scan-num">{'▲' if b['side'] else '▼'} {b['held']}d</td>
                    </tr>"""
        for b in p.get("vwap_etf", []) + p.get("vwap_native", []))
    vw_charts_etf = "\n".join(vwap_chart(b) for b in p.get("vwap_etf", []))
    vw_charts_native = "\n".join(vwap_chart(b) for b in p.get("vwap_native", []))
    vwap_section = f"""
                <div class="position-group"><h3>YTD VWAP · two cohorts</h3>
                <p class="scan-intro">The year's average cost basis, measured twice: spot-ETF buyers (consolidated-tape volume — the tradfi cohort) and Hyperliquid perp traders (native-venue volume — the crypto cohort). Same read as the equity tabs: above the line, the year's buyers are in profit and defend dips; below it, rallies meet trapped sellers.</p>
                <div class="scan-table-wrap">
                <table class="scan-table" aria-label="Crypto year-to-date VWAPs by cohort">
                    <thead><tr><th>Symbol</th><th>Cohort</th><th class="scan-num">Price</th><th class="scan-num">YTD VWAP</th><th class="scan-num">vs VWAP</th><th class="scan-num">Side</th></tr></thead>
                    <tbody>
{vw_rows}
                    </tbody>
                </table>
                </div>
                <div class="crypto-grid">
{vw_charts_etf}
                </div>
                <div class="crypto-grid">
{vw_charts_native}
                </div>
                </div>""" if (p.get("vwap_etf") or p.get("vwap_native")) else ""

    panel = f"""            <section class="trading-panel crypto-panel" id="crypto-panel" role="tabpanel" tabindex="0" aria-labelledby="crypto-tab" hidden>
                <div class="position-head">
                    <h2 id="crypto-heading">Crypto spread</h2>
                    <span>{fmt(p['last_bar'])} UTC close · daily · benchmark BTC {'' if not p.get('btc') else f"${p['btc']['price']:,.0f} · z {p['btc']['z']:+.2f}"}</span>
                </div>
                <p class="scan-intro">Altcoin relative strength measured the way the equity scan measures stocks against SPY: each coin's 50-day EMA z-score minus bitcoin's. Positive and green = the alt is more extended above its own trend than BTC is (vol-adjusted leadership); negative and red = it's lagging the benchmark. Crypto trades around the clock, so sessions are UTC calendar days and the last bar is the most recent complete day. Alt/BTC is the year-to-date change in the price ratio — the buy-and-hold version of the same question.</p>
                <div class="scan-table-wrap">
                <table class="scan-table" aria-label="Altcoin spread Z versus BTC">
                    <thead><tr><th>Coin</th><th>Name</th><th class="scan-num">Price</th><th class="scan-num">Coin Z</th><th class="scan-num">Spread vs BTC</th><th class="scan-num">Side</th><th class="scan-num">Alt/BTC YTD</th></tr></thead>
                    <tbody>
{rows}
                    </tbody>
                </table>
                </div>
                <div class="crypto-grid">
{charts}
                </div>
{vwap_section}
                <p class="trading-note">Spread Z uses the same EMA-based z-score as the momentum scan (EMA-50 mean, EMA-RMS sigma, EMA-3 smoothing), computed on daily UTC closes from Alpaca's crypto feed. A z-spread compares each asset to its own trend — it is relative momentum, not a price-ratio chart. Descriptive market data, not recommendations.</p>
            </section>"""

    page = open(PAGE).read()
    new = re.sub(r"(<!-- AUTO:CRYPTO:START -->).*?(<!-- AUTO:CRYPTO:END -->)",
                 lambda m: f"{m.group(1)}\n{panel}\n            {m.group(2)}",
                 page, flags=re.S)
    new = re.sub(r'(<span class="trading-tab-count" id="crypto-tab-count">)[^<]*(</span>)',
                 lambda m: f"{m.group(1)}{len(coins)}{m.group(2)}", new)
    if new == page:
        sys.exit("No changes made — are the AUTO:CRYPTO markers present?")
    open(PAGE, "w").write(new)
    print(f"[crypto] injected {os.path.basename(path)}: {len(coins)} coins, last bar {p['last_bar']}")


if __name__ == "__main__":
    main()
