#!/usr/bin/env python3
"""Inject the YTD VWAP charts into trading/index.html (AUTO:VWAP block).

Reads the newest ~/Documents/trading/scans/sector-vwap-*.json (or a path
given as argv[1]) emitted by ~/Documents/trading/src/sector_vwap_charts.py
and renders the "YTD VWAP" tab panel: summary table + SPY, 11 sector ETFs,
and 10 country ETFs as inline SVG in house colors, with a hover crosshair.

Usage: python3 scripts/update-trading-vwap.py [path/to/sector-vwap-YYYY-MM-DD.json]
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
SCAN_GLOB = os.path.expanduser("~/Documents/trading/scans/sector-vwap-*.json")

W, H = 560, 240
ML, MR, MT, MB = 10, 58, 12, 26
COUNTRY_ETFS = {"INDA", "EWY", "EWZ", "MCHI", "KWEB", "EWG", "EZA", "EWJ", "THD", "VNM"}


def fmt(d):
    return dt.date.fromisoformat(d).strftime("%b %-d")


def chart(sym, name, dates, close, vwap, w, h):
    lo = min(min(close), min(vwap))
    hi = max(max(close), max(vwap))
    pad = (hi - lo) * 0.06 or 1
    lo, hi = lo - pad, hi + pad
    iw, ih = w - ML - MR, h - MT - MB
    n = len(dates)
    months = [dt.date.fromisoformat(d).month for d in dates]

    def x(i):
        return ML + i / (n - 1) * iw

    def y(v):
        return MT + (hi - v) / (hi - lo) * ih

    ticks = []
    for i in range(1, n):
        if months[i] != months[i - 1]:
            lbl = dt.date.fromisoformat(dates[i]).strftime("%b")
            ticks.append(f'<line x1="{x(i):.1f}" y1="{MT}" x2="{x(i):.1f}" y2="{MT + ih}" class="vg"/>'
                         f'<text x="{x(i):.1f}" y="{h - 8}" class="va" text-anchor="middle">{lbl}</text>')
    for k in range(4):
        v = lo + (hi - lo) * k / 3
        f = f"{v:.0f}" if hi >= 100 else f"{v:.1f}"
        ticks.append(f'<line x1="{ML}" y1="{y(v):.1f}" x2="{ML + iw}" y2="{y(v):.1f}" class="vg"/>'
                     f'<text x="{ML + iw + 6}" y="{y(v) + 3.5:.1f}" class="va">{f}</text>')

    diff = [a - b for a, b in zip(close, vwap)]
    fills, marks, run = [], [], [0]

    def flush(run, sign):
        pts = [f"{x(j):.1f},{y(close[j]):.1f}" for j in run] + \
              [f"{x(j):.1f},{y(vwap[j]):.1f}" for j in reversed(run)]
        fills.append(f'<polygon points="{" ".join(pts)}" class="{"vfp" if sign else "vfn"}"/>')

    for i in range(1, n):
        if (diff[i] >= 0) != (diff[i - 1] >= 0):
            run.append(i)
            flush(run, diff[i - 1] >= 0)
            run = [i]
            up, d = diff[i] >= 0, 4.5
            tri = (f"{x(i):.1f},{y(close[i]) - d:.1f} {x(i) - d:.1f},{y(close[i]) + d:.1f} {x(i) + d:.1f},{y(close[i]) + d:.1f}"
                   if up else
                   f"{x(i):.1f},{y(close[i]) + d:.1f} {x(i) - d:.1f},{y(close[i]) - d:.1f} {x(i) + d:.1f},{y(close[i]) - d:.1f}")
            marks.append(f'<polygon points="{tri}" class="{"vmu" if up else "vmd"}"><title>{fmt(dates[i])} cross {"above" if up else "below"}</title></polygon>')
        else:
            run.append(i)
    if len(run) > 1:
        flush(run, diff[-1] >= 0)

    price = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(close))
    vw = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(vwap))
    side = diff[-1] >= 0
    pct = (close[-1] / vwap[-1] - 1) * 100
    data = json.dumps({"dates": dates, "close": close, "vwap": vwap}, separators=(",", ":"))
    return f"""                <figure class="vwap-chart{' vwap-chart--spy' if sym == 'SPY' else ''}" data-sym="{sym}" data-d='{data}'>
                    <figcaption><b>{sym}</b> <span>{name}</span><em class="{'scan-z-pos' if side else 'scan-z-neg'}">{pct:+.1f}% {'above' if side else 'below'}</em></figcaption>
                    <svg viewBox="0 0 {w} {h}" preserveAspectRatio="none" role="img" aria-label="{sym} 2026 price versus year-to-date VWAP">
                    {''.join(ticks)}{''.join(fills)}
                    <polyline points="{vw}" class="vlv"/>
                    <polyline points="{price}" class="vlp"/>
                    {''.join(marks)}
                    <line class="vxh" x1="0" y1="{MT}" x2="0" y2="{MT + ih}" visibility="hidden"/>
                    </svg>
                    <div class="vwap-tip" hidden></div>
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
    series, summary = p["series"], p["summary"]
    last_bar = dt.date.fromisoformat(p["last_bar"]).strftime("%B %-d, %Y")
    spy_up = next(s["last_up"] for s in summary if s["sym"] == "SPY")

    def lead(s):
        if s["sym"] == "SPY" or not s["last_up"] or not spy_up:
            return '<span class="scan-null">—</span>'
        d = (dt.date.fromisoformat(s["last_up"]) - dt.date.fromisoformat(spy_up)).days
        if d == 0:
            return '<span class="scan-sec">with SPY</span>'
        cls = "scan-z-pos" if d < 0 else "scan-sec"
        return f'<span class="{cls}">{"led" if d < 0 else "lagged"} SPY {abs(d)}d</span>'

    ordered = sorted(summary, key=lambda s: (s["sym"] != "SPY", -s["pct"]))
    us_summary = [s for s in ordered if s["sym"] not in COUNTRY_ETFS]
    country_summary = [s for s in ordered if s["sym"] in COUNTRY_ETFS]
    if len(us_summary) != 12 or {s["sym"] for s in country_summary} != COUNTRY_ETFS:
        sys.exit("Expected SPY + 11 US sector ETFs and all 10 country ETFs")

    def render_rows(items):
        return "\n".join(
            f"""                    <tr>
                        <td class="scan-sym">{s['sym']}</td>
                        <td class="scan-sec">{s['name']}</td>
                        <td class="scan-num"><span class="{'scan-z-pos' if s['pct'] >= 0 else 'scan-z-neg'}">{s['pct']:+.1f}%</span></td>
                        <td class="scan-num">{'▲' if s['side'] else '▼'} since {fmt(s['since'])} ({s['held']}d)</td>
                        <td class="scan-num">{fmt(s['last_up']) if s['last_up'] else '—'}</td>
                        <td class="scan-num">{lead(s)}</td>
                        <td class="scan-num">{s['n_cross']}</td>
                    </tr>"""
            for s in items)

    def render_charts(items):
        return "\n".join(
            chart(s["sym"], s["name"], series[s["sym"]]["dates"],
                  series[s["sym"]]["close"], series[s["sym"]]["vwap"],
                  *((1152, 300) if s["sym"] == "SPY" else (W, H)))
            for s in items)

    us_rows, country_rows = render_rows(us_summary), render_rows(country_summary)
    us_charts, country_charts = render_charts(us_summary), render_charts(country_summary)

    panel = f"""            <section class="trading-panel vwap-panel" id="vwap-panel" role="tabpanel" tabindex="0" aria-labelledby="vwap-tab" hidden>
                <div class="position-head">
                    <h2 id="vwap-heading">YTD VWAP</h2>
                    <span>{last_bar} close · anchor Jan 2, 2026</span>
                </div>
                <p class="scan-intro">The year-anchored VWAP is the average cost basis of every share traded in 2026. Price holding above it means the average year-to-date short seller is underwater — stay long while it holds; price holding below means the average buyer is trapped. The cross is the regime flip, and sectors often flip a day or two before SPY does. Solid line is the close, dashed line the YTD VWAP; ▲▼ mark crosses; hover for exact values.</p>
                <section class="vwap-section" aria-labelledby="vwap-us-heading">
                <div class="position-group"><h3 id="vwap-us-heading">US Market &amp; Sector ETFs · {len(us_summary)}</h3></div>
                <div class="scan-table-wrap">
                <table class="scan-table" aria-label="YTD VWAP summary for SPY and 11 US sector ETFs">
                    <thead><tr><th>Symbol</th><th>Name</th><th class="scan-num">vs YTD VWAP</th><th class="scan-num">Current side</th><th class="scan-num">Last ↑ cross</th><th class="scan-num">vs SPY's ↑</th><th class="scan-num">Crosses</th></tr></thead>
                    <tbody>
{us_rows}
                    </tbody>
                </table>
                </div>
                <div class="vwap-grid">
{us_charts}
                </div>
                </section>
                <section class="vwap-section" aria-labelledby="vwap-country-heading">
                <div class="position-group"><h3 id="vwap-country-heading">Country ETFs · {len(country_summary)}</h3></div>
                <div class="scan-table-wrap">
                <table class="scan-table" aria-label="YTD VWAP summary for {len(country_summary)} country ETFs">
                    <thead><tr><th>Symbol</th><th>Country</th><th class="scan-num">vs YTD VWAP</th><th class="scan-num">Current side</th><th class="scan-num">Last ↑ cross</th><th class="scan-num">vs SPY's ↑</th><th class="scan-num">Crosses</th></tr></thead>
                    <tbody>
{country_rows}
                    </tbody>
                </table>
                </div>
                <div class="vwap-grid">
{country_charts}
                </div>
                </section>
                <p class="trading-note">Price and VWAP are computed from consolidated daily bars (typical price × volume, anchored January 2, 2026). Refreshed daily after the close alongside the momentum scan. Descriptive market data, not investment advice.</p>
                <script>
                (() => {{
                document.querySelectorAll('.vwap-chart').forEach((fig) => {{
                    const d = JSON.parse(fig.dataset.d), svg = fig.querySelector('svg'),
                        tip = fig.querySelector('.vwap-tip'), xh = fig.querySelector('.vxh'),
                        vb = svg.viewBox.baseVal, n = d.dates.length, ML = 10, MR = 58;
                    svg.addEventListener('mousemove', (e) => {{
                        const r = svg.getBoundingClientRect(),
                            vx = (e.clientX - r.left) / r.width * vb.width,
                            i = Math.max(0, Math.min(n - 1, Math.round((vx - ML) / (vb.width - ML - MR) * (n - 1)))),
                            px = ML + i / (n - 1) * (vb.width - ML - MR);
                        xh.setAttribute('x1', px); xh.setAttribute('x2', px); xh.removeAttribute('visibility');
                        const diff = (d.close[i] / d.vwap[i] - 1) * 100;
                        tip.innerHTML = `<b>${{d.dates[i]}}</b><br>close ${{d.close[i]}}<br>vwap ${{d.vwap[i].toFixed(2)}}<br><span class="${{diff >= 0 ? 'scan-z-pos' : 'scan-z-neg'}}">${{diff >= 0 ? '+' : ''}}${{diff.toFixed(2)}}%</span>`;
                        tip.hidden = false;
                        const fr = fig.getBoundingClientRect();
                        let lx = e.clientX - fr.left + 14;
                        if (lx + tip.offsetWidth > fr.width - 8) lx = e.clientX - fr.left - tip.offsetWidth - 14;
                        tip.style.left = lx + 'px'; tip.style.top = (e.clientY - fr.top - 10) + 'px';
                    }});
                    svg.addEventListener('mouseleave', () => {{ tip.hidden = true; xh.setAttribute('visibility', 'hidden'); }});
                }});
                }})();
                </script>
            </section>"""

    page = open(PAGE).read()
    new = re.sub(r"(<!-- AUTO:VWAP:START -->).*?(<!-- AUTO:VWAP:END -->)",
                 lambda m: f"{m.group(1)}\n{panel}\n            {m.group(2)}",
                 page, flags=re.S)
    new, tab_count = re.subn(
        r'(<button class="trading-tab" id="vwap-tab".*?<span class="trading-tab-count">)\d+(</span>)',
        rf'\g<1>{len(summary)}\2', new, count=1)
    if tab_count != 1:
        sys.exit("Could not update YTD VWAP tab count")
    if new == page:
        print(f"[vwap] already current: {os.path.basename(path)}, {len(summary)} charts, last bar {p['last_bar']}")
        return
    open(PAGE, "w").write(new)
    print(f"[vwap] injected {os.path.basename(path)}: {len(summary)} charts, last bar {p['last_bar']}")


if __name__ == "__main__":
    main()
