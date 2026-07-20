#!/usr/bin/env python3
"""Inject per-ticker setup VWAP charts into trading/index.html (AUTO:SETUPS block).

Reads the newest ~/Documents/trading/scans/setup-vwap-*.json (or a path given
as argv[1]) emitted by ~/Documents/trading/src/setup_vwap_charts.py and renders
the "Setup charts" tab: one card per momentum-scan setup — daily candles with
the earnings-anchored VWAP (violet, E marks the anchor) and YTD VWAP (dashed),
a spread-Z-vs-SPY subpanel, a dist-Z histogram, and the rule-based read line.

Usage: python3 scripts/update-trading-setups.py [path/to/setup-vwap-YYYY-MM-DD.json]
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
SCAN_GLOB = os.path.expanduser("~/Documents/trading/scans/setup-vwap-*.json")

W = 1120
PX_H, SUB_H, GAP, AXIS_H = 280, 78, 14, 22
ML, MR = 8, 66
H = PX_H + (SUB_H + GAP) * 2 + AXIS_H

UP, DN = "#1a7a3c", "#8f2222"          # candle bodies (house green-live / ox family)
VIOLET, YTD = "#4a3aa7", "#6b655c"     # earnings VWAP / YTD VWAP
POS, NEG, MUT = "#2a78d6", "#e34948", "#a09a90"


def fmt(d):
    return dt.date.fromisoformat(d).strftime("%b %-d")


def card(rec):
    s = rec["series"]
    n = len(s["dates"])
    o, h, l, c = s["o"], s["h"], s["l"], s["c"]
    ev, yv, sp, dz = s["ev"], s["yv"], s["sp"], s["dz"]
    months = [dt.date.fromisoformat(d).month for d in s["dates"]]
    iw = W - ML - MR

    def x(i):
        return ML + (i + 0.5) / n * iw

    cw = max(1.6, iw / n * 0.6)

    lo = min(min(l), min(v for v in ev if v is not None) if any(v is not None for v in ev) else min(l), min(yv))
    hi = max(max(h), max(v for v in ev if v is not None) if any(v is not None for v in ev) else max(h), max(yv))
    pad = (hi - lo) * 0.05
    lo, hi = lo - pad, hi + pad

    def yp(v):
        return (hi - v) / (hi - lo) * (PX_H - 8) + 4

    parts, axis = [], []
    for i in range(1, n):
        if months[i] != months[i - 1]:
            parts.append(f'<line x1="{x(i):.1f}" y1="0" x2="{x(i):.1f}" y2="{H - AXIS_H}" class="sg"/>')
            axis.append(f'<text x="{x(i):.1f}" y="{H - 7}" class="sa" text-anchor="middle">{dt.date.fromisoformat(s["dates"][i]).strftime("%b")}</text>')
    for k in range(4):
        v = lo + (hi - lo) * k / 3
        parts.append(f'<line x1="{ML}" y1="{yp(v):.1f}" x2="{ML + iw}" y2="{yp(v):.1f}" class="sg"/>'
                     f'<text x="{ML + iw + 6}" y="{yp(v) + 3.5:.1f}" class="sa">{v:,.0f}</text>')
    for i in range(n):
        col = UP if c[i] >= o[i] else DN
        parts.append(f'<line x1="{x(i):.1f}" y1="{yp(h[i]):.1f}" x2="{x(i):.1f}" y2="{yp(l[i]):.1f}" stroke="{col}" stroke-width="1"/>')
        top, bot = max(o[i], c[i]), min(o[i], c[i])
        parts.append(f'<rect x="{x(i) - cw / 2:.1f}" y="{yp(top):.1f}" width="{cw:.1f}" height="{max(0.8, yp(bot) - yp(top)):.1f}" fill="{col}"/>')
    parts.append('<polyline points="' + " ".join(
        f"{x(i):.1f},{yp(v):.1f}" for i, v in enumerate(yv)) + f'" fill="none" stroke="{YTD}" stroke-width="1.5" stroke-dasharray="5 4"/>')
    pts = [(i, v) for i, v in enumerate(ev) if v is not None]
    if pts:
        parts.append('<polyline points="' + " ".join(
            f"{x(i):.1f},{yp(v):.1f}" for i, v in pts) + f'" fill="none" stroke="{VIOLET}" stroke-width="2"/>')
        parts.append(f'<text x="{x(pts[0][0]):.1f}" y="{yp(pts[0][1]) - 6:.1f}" class="sa" fill="{VIOLET}" text-anchor="middle">E</text>')
    tags = [(c[-1], "#1a1815", f"{c[-1]:,.2f}")]
    if pts:
        tags.append((pts[-1][1], VIOLET, f"{pts[-1][1]:,.2f}"))
    tags.append((yv[-1], YTD, f"{yv[-1]:,.2f}"))
    for v, col, txt in tags:
        parts.append(f'<text x="{W - 2}" y="{yp(v) + 3.5:.1f}" class="st" fill="{col}" text-anchor="end">{txt}</text>')

    y0 = PX_H + GAP
    zmax = max(2.0, max(abs(v) for v in sp if v is not None) * 1.1 if any(v is not None for v in sp) else 2.0)

    def ys(v):
        return y0 + (zmax - v) / (2 * zmax) * SUB_H

    parts.append(f'<text x="{ML}" y="{y0 + 10}" class="sl">Spread Z vs SPY (50d)</text>')
    parts.append(f'<line x1="{ML}" y1="{ys(0):.1f}" x2="{ML + iw}" y2="{ys(0):.1f}" class="sz"/>')
    for i in range(1, n):
        if sp[i - 1] is None or sp[i] is None:
            continue
        col = UP if sp[i] >= 0 else NEG
        parts.append(f'<line x1="{x(i - 1):.1f}" y1="{ys(sp[i - 1]):.1f}" x2="{x(i):.1f}" y2="{ys(sp[i]):.1f}" stroke="{col}" stroke-width="1.8"/>')
    last_sp = next((v for v in reversed(sp) if v is not None), None)
    if last_sp is not None:
        parts.append(f'<text x="{W - 2}" y="{ys(last_sp) + 3.5:.1f}" class="st" fill="{UP if last_sp >= 0 else NEG}" text-anchor="end">{last_sp:+.1f}</text>')

    y1 = y0 + SUB_H + GAP
    dmax = max(2.5, max(abs(v) for v in dz if v is not None) * 1.1 if any(v is not None for v in dz) else 2.5)

    def yd(v):
        return y1 + (dmax - v) / (2 * dmax) * SUB_H

    parts.append(f'<text x="{ML}" y="{y1 + 10}" class="sl">Dist Z — YTD VWAP</text>')
    parts.append(f'<line x1="{ML}" y1="{yd(0):.1f}" x2="{ML + iw}" y2="{yd(0):.1f}" class="sz"/>')
    for lvl in (1, -1):
        parts.append(f'<line x1="{ML}" y1="{yd(lvl):.1f}" x2="{ML + iw}" y2="{yd(lvl):.1f}" class="sd"/>')
    bw = max(1.2, iw / n * 0.55)
    for i in range(n):
        if dz[i] is None:
            continue
        col = POS if dz[i] > 1 else NEG if dz[i] < -1 else MUT
        parts.append(f'<rect x="{x(i) - bw / 2:.1f}" y="{min(yd(0), yd(dz[i])):.1f}" width="{bw:.1f}" height="{abs(yd(dz[i]) - yd(0)):.1f}" fill="{col}"/>')

    st = rec["stats"]
    bcls = {"ENTER+": "setup-b--long", "ENTER": "setup-b--long", "SHORT+": "setup-b--short",
            "SHORT": "setup-b--short", "BREAKING": "setup-b--break"}.get(rec["label"], "setup-b--watch")
    stats = (f"spread Z <b>{st['spread_z']:+.2f}</b> · dist Z <b>{st['dist_z']:+.2f}</b> · "
             f"vs earn VWAP <b>{st['evwap_pct']:+.2f}%</b> ({'▲' if st['evwap_side'] else '▼'} {st['evwap_streak']}d) · "
             f"next earnings {fmt(st['next_earn']) if st.get('next_earn') else '—'}")
    tip_data = json.dumps({"dates": s["dates"], "c": c, "ev": ev, "yv": yv, "sp": sp, "dz": dz})
    return f"""                <section class="setup-card" data-d='{tip_data}'>
                    <header><b>{rec['symbol']}</b><span>{rec['sector']}</span><span class="setup-b {bcls}">{rec['label']}</span><span class="setup-stats">{stats}</span></header>
                    <p class="setup-read">{rec['read']}</p>
                    <svg viewBox="0 0 {W} {H}" preserveAspectRatio="none" role="img" aria-label="{rec['symbol']} setup chart">{''.join(parts)}{''.join(axis)}
                    <line class="sx" x1="0" y1="0" x2="0" y2="{H - AXIS_H}" visibility="hidden"/></svg>
                    <div class="setup-tip" hidden></div>
                </section>"""


def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        paths = sorted(glob.glob(SCAN_GLOB))
        if not paths:
            sys.exit(f"No JSON matching {SCAN_GLOB}")
        path = paths[-1]
    p = json.load(open(path))
    expected_symbols = [str(r["symbol"]).upper() for r in p["setups"]]
    allowed_labels = {"ENTER+", "ENTER", "SHORT+", "SHORT", "BREAKING"}
    if len(set(expected_symbols)) != len(expected_symbols):
        sys.exit("Duplicate setup symbols in input JSON")
    bad_labels = [r.get("label") for r in p["setups"] if r.get("label") not in allowed_labels]
    if bad_labels:
        sys.exit(f"Unsupported setup labels in input JSON: {bad_labels}")
    last_bar = dt.date.fromisoformat(p["last_bar"]).strftime("%B %-d, %Y")
    cards = "\n".join(card(r) for r in p["setups"])

    panel = f"""            <section class="trading-panel setup-panel" id="setups-panel" role="tabpanel" tabindex="0" aria-labelledby="setups-tab" hidden>
                <div class="position-head">
                    <h2 id="setups-heading">Setup charts</h2>
                    <span>{last_bar} close · candles YTD</span>
                </div>
                <p class="scan-intro">One chart per momentum-scan setup, read through the two cost-basis anchors: the violet line is the earnings-anchored VWAP (what the post-earnings cohort paid; E marks the anchor), the dashed line the YTD VWAP (what the whole year paid). Above both, every cohort is in profit — don't short it. Below the violet line but above the dashed one, sellers own the quarter and the year's buyers are the last defense — a YTD-VWAP break is the trapdoor. Below both is a clear short. Subpanels: 50-session spread Z vs SPY, and distance from the YTD VWAP in z units. Hover for exact values.</p>
{cards}
                <p class="trading-note">Charts are generated from the same daily scan data as the momentum tab. Screens, not recommendations.</p>
                <script>
                (() => {{
                document.querySelectorAll('.setup-card').forEach((cardEl) => {{
                    const d = JSON.parse(cardEl.dataset.d), svg = cardEl.querySelector('svg'),
                        tip = cardEl.querySelector('.setup-tip'), xh = cardEl.querySelector('.sx'),
                        vb = svg.viewBox.baseVal, n = d.dates.length, ML = 8, MR = 66;
                    svg.addEventListener('mousemove', (e) => {{
                        const r = svg.getBoundingClientRect(),
                            vx = (e.clientX - r.left) / r.width * vb.width,
                            i = Math.max(0, Math.min(n - 1, Math.floor((vx - ML) / (vb.width - ML - MR) * n))),
                            px = ML + (i + 0.5) / n * (vb.width - ML - MR);
                        xh.setAttribute('x1', px); xh.setAttribute('x2', px); xh.removeAttribute('visibility');
                        const row = (k, lbl) => d[k][i] == null ? '' : `${{lbl}} ${{d[k][i]}}<br>`;
                        tip.innerHTML = `<b>${{d.dates[i]}}</b><br>close ${{d.c[i]}}<br>${{row('ev', 'earn vwap')}}${{row('yv', 'ytd vwap')}}${{row('sp', 'spread z')}}${{row('dz', 'dist z')}}`;
                        tip.hidden = false;
                        const fr = cardEl.getBoundingClientRect();
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
    new, region_count = re.subn(r"(<!-- AUTO:SETUPS:START -->).*?(<!-- AUTO:SETUPS:END -->)",
                                lambda m: f"{m.group(1)}\n{panel}\n            {m.group(2)}",
                                page, count=1, flags=re.S)
    if region_count != 1:
        sys.exit(f"Expected exactly one AUTO:SETUPS region, found {region_count}")
    new, badge_count = re.subn(r'(<span class="trading-tab-count" id="setups-tab-count">)[^<]*(</span>)',
                               lambda m: f"{m.group(1)}{len(p['setups'])}{m.group(2)}", new, count=1)
    if badge_count != 1:
        sys.exit(f"Expected exactly one setup tab count, found {badge_count}")
    region = re.search(r"<!-- AUTO:SETUPS:START -->(.*?)<!-- AUTO:SETUPS:END -->", new, flags=re.S)
    rendered_symbols = re.findall(r'aria-label="([^\"]+) setup chart"', region.group(1) if region else "")
    if rendered_symbols != expected_symbols:
        sys.exit(f"Setup chart parity failure: expected={expected_symbols} rendered={rendered_symbols}")
    if new == page:
        sys.exit("No changes made — are the AUTO:SETUPS markers present?")
    open(PAGE, "w").write(new)
    print(f"[setups] injected {os.path.basename(path)}: {len(p['setups'])} cards")


if __name__ == "__main__":
    main()
