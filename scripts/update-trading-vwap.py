#!/usr/bin/env python3
"""Inject YTD sector/country VWAP into classic and routed VWAP surfaces.

Reads the newest ~/trading/scans/sector-vwap-*.json (or a path
specified as argv[1]) emitted by ~/trading/src/sector_vwap_charts.py
and renders the "VWAP" tab: US market/sector/theme charts first, followed by a
separate country section, loaded from trading/vwap-charts.json.

Usage: python3 scripts/update-trading-vwap.py [path/to/sector-vwap-YYYY-MM-DD.json]
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

from sync_trading_desk import sync_sections
from trading_shell import refresh_sector_status_pills

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "trading", "pipeline.html")
CHART_ASSET = os.path.join(ROOT, "trading", "vwap-charts.json")
SCAN_GLOB = os.path.expanduser("~/trading/scans/sector-vwap-*.json")

W, H = 560, 240
ML, MR, MT, MB = 10, 58, 12, 26
COUNTRY_ETFS = {"INDA", "EWY", "EWZ", "MCHI", "KWEB", "EWG", "EZA", "EWJ", "THD", "VNM"}
SECTOR_ETFS = {"XLK", "XLY", "XLV", "XLF", "XLI", "XLE", "XLP", "XLC", "XLU", "XLRE", "XLB"}
THEMATIC_ETFS = {"ESPO": "Gaming"}


def fmt(d):
    return dt.date.fromisoformat(d).strftime("%b %-d")


def ewm(values, span):
    """Small dependency-free equivalent of pandas ewm(adjust=False).mean()."""
    alpha = 2 / (span + 1)
    state = None
    out = []
    for value in values:
        if value is None:
            out.append(state)
            continue
        state = float(value) if state is None else alpha * float(value) + (1 - alpha) * state
        out.append(state)
    return out


def z50(values):
    """TradingView-parity EMA mean/RMS z-score with 3-session smoothing."""
    center = ewm(values, 50)
    diff = [float(value) - mean for value, mean in zip(values, center)]
    variance = ewm([value * value for value in diff], 50)
    raw = [None if value <= 0 else delta / math.sqrt(value)
           for delta, value in zip(diff, variance)]
    return ewm(raw, 3)


def chart(sym, name, dates, close, vwap, w, h, z50=None):
    lo = min(min(close), min(vwap))
    hi = max(max(close), max(vwap))
    pad = (hi - lo) * 0.06 or 1
    lo, hi = lo - pad, hi + pad
    iw, ih = w - ML - MR, h - MT - MB
    n = len(dates)
    if z50 is not None and len(z50) != n:
        raise ValueError(f"{sym} z50 length does not match price history")
    has_z = z50 is not None
    total_h = h + 92 if has_z else h
    z_top, z_bottom = h + 10, total_h - MB
    months = [dt.date.fromisoformat(d).month for d in dates]

    def x(i):
        return ML + i / (n - 1) * iw

    def y(v):
        return MT + (hi - v) / (hi - lo) * ih

    ticks = []
    for i in range(1, n):
        if months[i] != months[i - 1]:
            lbl = dt.date.fromisoformat(dates[i]).strftime("%b")
            ticks.append(f'<line x1="{x(i):.1f}" y1="{MT}" x2="{x(i):.1f}" y2="{MT + ih}" class="vg"/>')
            if has_z:
                ticks.append(f'<line x1="{x(i):.1f}" y1="{z_top}" x2="{x(i):.1f}" y2="{z_bottom}" class="vg"/>')
            ticks.append(f'<text x="{x(i):.1f}" y="{total_h - 8}" class="va" text-anchor="middle">{lbl}</text>')
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
    z_markup = ""
    last_z = None
    if has_z:
        finite_z = [value for value in z50 if value is not None]
        if not finite_z:
            raise ValueError(f"{sym} z50 history is empty")
        z_limit = max(2.0, max(abs(value) for value in finite_z) * 1.08)

        def zy(value):
            return z_top + (z_limit - value) / (2 * z_limit) * (z_bottom - z_top)

        threshold_lines = []
        for value, label in ((1, "+1"), (0, "0"), (-1, "−1")):
            threshold_lines.append(
                f'<line x1="{ML}" y1="{zy(value):.1f}" x2="{ML + iw}" y2="{zy(value):.1f}" class="vzt"/>'
                f'<text x="{ML + iw + 6}" y="{zy(value) + 3.5:.1f}" class="va">{label}</text>')

        def z_class(value):
            return "vzp" if value >= 1 else "vzn" if value <= -1 else "vzm"

        runs, points, active_class = [], [], None
        for i, value in enumerate(z50):
            if value is None:
                if len(points) > 1:
                    runs.append((active_class, points))
                points, active_class = [], None
                continue
            cls = z_class(value)
            if active_class is None:
                active_class, points = cls, [(i, value)]
            elif cls == active_class:
                points.append((i, value))
            else:
                points.append((i, value))
                if len(points) > 1:
                    runs.append((active_class, points))
                active_class, points = cls, [(i, value)]
        if len(points) > 1:
            runs.append((active_class, points))
        z_paths = "".join(
            f'<polyline points="{" ".join(f"{x(i):.1f},{zy(value):.1f}" for i, value in points)}" class="{cls}"/>'
            for cls, points in runs)
        last_z = finite_z[-1]
        last_cls = "scan-z-pos" if last_z >= 1 else "scan-z-neg" if last_z <= -1 else "scan-sec"
        z_markup = (f'<text x="{ML}" y="{z_top - 4}" class="vzl">50D Z SCORE</text>'
                    f'<text x="{ML + iw + 6}" y="{z_top - 4}" class="vzl {last_cls}">{last_z:+.2f}</text>'
                    f'{"".join(threshold_lines)}{z_paths}')

    side = diff[-1] >= 0
    pct = (close[-1] / vwap[-1] - 1) * 100
    data_obj = {"dates": dates, "close": close, "vwap": vwap}
    if has_z:
        data_obj["z50"] = z50
    data = json.dumps(data_obj, separators=(",", ":"))
    aria = f"{sym} 2026 price versus year-to-date VWAP" + (" with 50-session z-score history" if has_z else "")
    z_badge = (f'<strong class="vwap-z-badge {"scan-z-pos" if last_z >= 0 else "scan-z-neg"}">· 50D Z {last_z:+.2f}</strong>'
               if last_z is not None else "")
    return f"""                <figure class="vwap-chart{' vwap-chart--spy' if sym == 'SPY' else ''}" data-sym="{sym}" data-d='{data}'>
                    <figcaption><b>{sym}</b> <span>{name}</span><em class="{'scan-z-pos' if side else 'scan-z-neg'}">{pct:+.1f}% {'above' if side else 'below'}</em>{z_badge}</figcaption>
                    <svg viewBox="0 0 {w} {total_h}" preserveAspectRatio="none" role="img" aria-label="{aria}">
                    {''.join(ticks)}{''.join(fills)}
                    <polyline points="{vw}" class="vlv"/>
                    <polyline points="{price}" class="vlp"/>
                    {''.join(marks)}{z_markup}
                    <line class="vxh" x1="0" y1="{MT}" x2="0" y2="{z_bottom if has_z else MT + ih}" visibility="hidden"/>
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

    spy_summary = [s for s in summary if s["sym"] == "SPY"]
    sector_summary = [s for s in summary if s["sym"] in SECTOR_ETFS]
    thematic_summary = [s for s in summary if s["sym"] in THEMATIC_ETFS]
    if len(spy_summary) != 1 or len(sector_summary) != 11 or any(s.get("z") is None for s in sector_summary):
        sys.exit("Expected SPY plus 11 sector summaries with current Z scores")
    if ({s["sym"] for s in thematic_summary} != set(THEMATIC_ETFS)
            or any(s.get("z") is None or s.get("name") != THEMATIC_ETFS[s["sym"]]
                   for s in thematic_summary)):
        sys.exit("Expected ESPO Gaming theme summary with a current Z score")
    spy_z50 = z50(series["SPY"]["close"])
    series["SPY"]["z50"] = [round(value, 6) if value is not None else None for value in spy_z50]
    spy_summary[0]["z"] = round(next(value for value in reversed(spy_z50) if value is not None), 2)
    def latest_exact_z(item):
        values = series[item["sym"]].get("z50") or []
        return next(float(value) for value in reversed(values) if value is not None)

    us_summary = sorted([*spy_summary, *sector_summary, *thematic_summary],
                        key=lambda s: (-latest_exact_z(s), s["sym"]))
    country_summary = sorted((s for s in summary if s["sym"] in COUNTRY_ETFS),
                             key=lambda s: (-latest_exact_z(s), s["sym"]))
    expected_symbols = {"SPY"} | SECTOR_ETFS | set(THEMATIC_ETFS) | COUNTRY_ETFS
    if len(us_summary) != 13 or {s["sym"] for s in country_summary} != COUNTRY_ETFS:
        sys.exit("Expected SPY + 11 US sector ETFs + ESPO and all 10 country ETFs")
    if any(s.get("z") is None for s in country_summary):
        sys.exit("Expected all 10 country summaries to include current Z scores")
    if set(series) != expected_symbols or {s["sym"] for s in summary} != expected_symbols:
        sys.exit("VWAP summary/series symbols do not match the exact 23-symbol contract")
    summary_by_symbol = {s["sym"]: s for s in summary}
    for sym, values in series.items():
        dates, close, vwap = values.get("dates"), values.get("close"), values.get("vwap")
        if not dates or len(dates) < 2 or len(dates) != len(close or []) or len(dates) != len(vwap or []):
            sys.exit(f"{sym} VWAP history is empty or misaligned")
        if dates != sorted(dates) or len(dates) != len(set(dates)):
            sys.exit(f"{sym} VWAP dates are not strictly increasing")
        if dates[-1] != p["last_bar"]:
            sys.exit(f"{sym} VWAP history is stale: {dates[-1]} != {p['last_bar']}")
        if any(not math.isfinite(float(value)) for value in [*(close or []), *(vwap or [])]):
            sys.exit(f"{sym} VWAP history contains a non-finite value")
        z_values = values.get("z50")
        if sym in expected_symbols:
            if not isinstance(z_values, list) or len(z_values) != len(dates):
                sys.exit(f"{sym} 50-session Z history is missing or misaligned")
            if any(value is not None and not math.isfinite(float(value)) for value in z_values):
                sys.exit(f"{sym} 50-session Z history contains a non-finite value")
            finite_z = [float(value) for value in z_values if value is not None]
            if not finite_z or round(finite_z[-1], 2) != summary_by_symbol[sym].get("z"):
                sys.exit(f"{sym} current 50-session Z does not match its summary")

    def z_cell(item):
        value = item.get("z")
        if value is None:
            return '<span class="scan-sec">—</span>'
        cls = "scan-z-pos" if value >= 0 else "scan-z-neg"
        return f'<span class="{cls}">{value:+.2f}</span>'

    def render_rows(items, scope):
        return "\n".join(
            f"""                    <tr data-vwap-scope="{scope}">
                        <td class="scan-sym"><span translate="no">{html.escape(s['sym'])}</span></td>
                        <td class="scan-sec">{html.escape(s['name'])}</td>
                        <td class="scan-num">{z_cell(s)}</td>
                        <td class="scan-num"><span class="{'scan-z-pos' if s['pct'] >= 0 else 'scan-z-neg'}">{s['pct']:+.1f}%</span></td>
                        <td class="scan-num">{'▲' if s['side'] else '▼'} since {fmt(s['since'])} ({s['held']}d)</td>
                    </tr>"""
            for s in items)

    chart_map = {
        s["sym"]: chart(
            s["sym"], s["name"], series[s["sym"]]["dates"], series[s["sym"]]["close"],
            series[s["sym"]]["vwap"], 1152, 340, z50=series[s["sym"]].get("z50"),
        )
        for s in [*us_summary, *country_summary]
    }
    us_symbols = [s["sym"] for s in us_summary]
    country_symbols = [s["sym"] for s in country_summary]
    asset_json = json.dumps({
        "as_of": p["last_bar"],
        "default": "SPY",
        "groups": {"us": us_symbols, "countries": country_symbols},
        "charts": chart_map,
    }, separators=(",", ":"), allow_nan=False)
    asset_hash = hashlib.sha256(asset_json.encode()).hexdigest()[:12]
    us_above = sum(bool(s["side"]) for s in us_summary)
    leaders = sorted(sector_summary, key=lambda s: (-s["z"], s["sym"]))[:2]
    laggards = sorted(sector_summary, key=lambda s: (s["z"], s["sym"]))[:2]
    us_rows = render_rows(us_summary, "us")
    country_rows = render_rows(country_summary, "countries")
    takeaway = (f"{us_above} of {len(us_summary)} US markets are above YTD VWAP. "
                f"{leaders[0]['name']} leads the 50-day trend; {laggards[0]['name']} lags.")

    panel = f"""            <section class="trading-panel vwap-panel" id="vwap-panel" data-market-as-of="{p['last_bar']}" role="tabpanel" tabindex="0" aria-labelledby="vwap-tab" hidden>
                <div class="position-head">
                    <h2 id="vwap-heading">VWAP</h2>
                    <span>{last_bar} close · anchor Jan 2, 2026</span>
                </div>
                <p class="trading-takeaway">{html.escape(takeaway)}</p>
                <section class="vwap-market-section" aria-labelledby="vwap-us-heading">
                <h3 id="vwap-us-heading">US market + sectors + themes</h3>
                <div class="scan-table-wrap">
                <table class="scan-table scan-table--compact" aria-label="US market, sector, and theme year-to-date VWAP summary">
                    <thead><tr><th>Symbol</th><th>Market</th><th class="scan-num">50D Z</th><th class="scan-num">vs VWAP</th><th class="scan-num">Trend</th></tr></thead>
                    <tbody>
{us_rows}
                    </tbody>
                </table>
                </div>
                <div class="vwap-chart-grid" id="vwap-chart-grid" data-url="/trading/vwap-charts.json?v={asset_hash}" data-symbols="{','.join(us_symbols)}" aria-live="polite">
                    <p class="bl-empty">Loading SPY, 11 sector charts, and ESPO Gaming…</p>
                </div>
                </section>
                <section class="vwap-market-section vwap-country-section" aria-labelledby="vwap-countries-heading">
                <h3 id="vwap-countries-heading">Country markets</h3>
                <p class="data-meta">Country ETFs are separated from US sectors and ranked by 50-day Z-score, descending.</p>
                <div class="scan-table-wrap">
                <table class="scan-table scan-table--compact" aria-label="Country market year-to-date VWAP summary">
                    <thead><tr><th>Symbol</th><th>Country</th><th class="scan-num">50D Z</th><th class="scan-num">vs VWAP</th><th class="scan-num">Trend</th></tr></thead>
                    <tbody>
{country_rows}
                    </tbody>
                </table>
                </div>
                <div class="vwap-chart-grid" id="vwap-country-chart-grid" data-url="/trading/vwap-charts.json?v={asset_hash}" data-symbols="{','.join(country_symbols)}" aria-live="polite">
                    <p class="bl-empty">Loading 10 country charts…</p>
                </div>
                </section>
                <details class="trading-method"><summary>How this works</summary><p>YTD VWAP estimates the average cost basis of shares traded this year. Above it, the average buyer is in profit; below it, the average buyer is underwater. Solid line is close, dashed line is VWAP, and triangles mark crosses. Sector, theme, and country charts show the same smoothed 50-session Z-score beneath price. Descriptive market data, not investment advice.</p></details>
            </section>"""

    page = open(PAGE).read()
    new = re.sub(r"(<!-- AUTO:VWAP:START -->).*?(<!-- AUTO:VWAP:END -->)",
                 lambda m: f"{m.group(1)}\n{panel}\n            {m.group(2)}",
                 page, flags=re.S)
    old_asset = open(CHART_ASSET).read() if os.path.exists(CHART_ASSET) else None
    page_changed = new != page
    asset_changed = old_asset != asset_json
    if page_changed:
        open(PAGE, "w").write(new)
    if asset_changed:
        open(CHART_ASSET, "w").write(asset_json)
    sector_shell_changed = bool(refresh_sector_status_pills())
    routed_changed = bool(sync_sections(["vwap"]))
    if not page_changed and not asset_changed and not sector_shell_changed and not routed_changed:
        print(f"[vwap] already current: {os.path.basename(path)}, {len(summary)} charts, last bar {p['last_bar']}")
        return
    print(f"[vwap] injected {os.path.basename(path)}: {len(summary)} charts, last bar {p['last_bar']}")


if __name__ == "__main__":
    main()
