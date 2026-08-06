#!/usr/bin/env python3
"""Render the latest structured Grok Risk journal entry and the rating vs the tape chart."""
from __future__ import annotations

import html
import json
import os
import pathlib
import re
import urllib.request
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "trading" / "grok-risk.json"
PAGE = ROOT / "trading" / "grok-risk" / "index.html"
START = "<!-- AUTO:GROK_RISK:START -->"
END = "<!-- AUTO:GROK_RISK:END -->"
CHART_START = "<!-- AUTO:GROK_CHART:START -->"
CHART_END = "<!-- AUTO:GROK_CHART:END -->"

VHEX = {"Risk-on": "#087a42", "Neutral": "#b27b20", "Risk-off": "#b4404b"}
SESSION_RANK = {"pre-market": 0, "intraday": 1, "post-close": 2}


def validate(payload: dict) -> dict:
    if payload.get("schema_version") != 1 or payload.get("model") != "Grok 4.5":
        raise ValueError("grok-risk requires schema 1 and model Grok 4.5")
    entries = payload.get("entries") or []
    if not entries:
        raise ValueError("grok-risk requires at least one entry")
    entry = entries[0]
    if entry.get("model_id") != "grok-4.5" or entry.get("stance") not in {"Risk-on", "Neutral", "Risk-off"}:
        raise ValueError("invalid Grok model metadata or stance")
    rating = entry.get("risk_appetite")
    if not isinstance(rating, (int, float)) or not 0 <= float(rating) <= 10:
        raise ValueError("Grok risk appetite must be between 0 and 10")
    return entry


def render(entry: dict) -> str:
    esc = lambda value: html.escape(str(value), quote=True)
    rating = float(entry["risk_appetite"])
    color = {"Risk-on": "#087a42", "Neutral": "#b27b20", "Risk-off": "#b4404b"}[entry["stance"]]
    journal = "".join(f'<p style="font-size:1.05rem;line-height:1.6;margin-bottom:16px;">{esc(value)}</p>' for value in entry["journal"])
    supports = "".join(f"<li>{esc(value)}</li>" for value in entry["what_supports_risk"])
    restraints = "".join(f"<li>{esc(value)}</li>" for value in entry["what_holds_it_back"])
    changes = "".join(f"<li>{esc(value)}</li>" for value in entry["what_changes_my_mind"])
    sources = " · ".join(
        f'<a href="{esc(source["url"])}" rel="noopener">{esc(source["title"])}</a>'
        for source in entry["sources"]
    )
    return f'''<div class="risk-assessment" data-model="Grok 4.5" data-rating="{rating:g}" data-stance="{esc(entry["stance"])}" style="max-width:720px;margin:0 auto;padding:20px 0;">
<h2 style="font-size:1.5rem;margin-bottom:12px;color:{color};">{esc(entry["as_of_date"])} · {esc(entry["stance"])} ({rating:g}/10)</h2>
<p style="font-size:1.05rem;line-height:1.6;margin-bottom:20px;"><strong>{esc(entry["headline"])}</strong></p>
{journal}
<h3 style="margin-top:24px;margin-bottom:8px;">What Supports Risk</h3><ul style="line-height:1.7;margin-bottom:20px;">{supports}</ul>
<h3 style="margin-top:24px;margin-bottom:8px;">What Holds It Back</h3><ul style="line-height:1.7;margin-bottom:20px;">{restraints}</ul>
<h3 style="margin-top:24px;margin-bottom:8px;">What Changes My Mind</h3><ul style="line-height:1.7;margin-bottom:20px;">{changes}</ul>
<details class="trading-method"><summary>Methodology and limitations</summary><p><b>{esc(entry["methodology"]["name"])}</b> — {esc(entry["methodology"]["explanation"])}</p><p>{esc(" · ".join(entry["limitations"]))}</p></details>
<p class="risk-journal-source">Sources: {sources}. This is Grok's model output, not a Zonted mechanical score.</p>
</div>'''


def fetch_closes(start):
    """Daily closes for SPY+QQQ from `start`: Alpaca SIP first, Stooq keyless fallback."""
    try:
        keys = {}
        for line in open(os.path.expanduser("~/.config/trading/alpaca.env")):
            line = line.strip()
            if line.startswith("export "):
                line = line[7:]
            if "=" in line and not line.startswith("#"):
                name, value = line.split("=", 1)
                keys[name.strip()] = value.strip().strip('"').strip("'")
        req = urllib.request.Request(
            f"https://data.alpaca.markets/v2/stocks/bars?symbols=SPY,QQQ&timeframe=1Day"
            f"&start={start}&limit=10000&adjustment=split&feed=sip",
            headers={"APCA-API-KEY-ID": keys["APCA_KEY"], "APCA-API-SECRET-KEY": keys["APCA_SECRET"]})
        bars = json.load(urllib.request.urlopen(req, timeout=20))["bars"]
        return {sym: [[b["t"][:10], round(b["c"], 2)] for b in bars[sym]] for sym in ("SPY", "QQQ")}
    except Exception:
        pass
    try:  # Stooq fallback, no key
        out = {}
        for sym, stooq in (("SPY", "spy.us"), ("QQQ", "qqq.us")):
            req = urllib.request.Request(f"https://stooq.com/q/d/l/?s={stooq}&i=d",
                                         headers={"User-Agent": "Mozilla/5.0"})
            rows = urllib.request.urlopen(req, timeout=20).read().decode().splitlines()[1:]
            out[sym] = [[r.split(",")[0], round(float(r.split(",")[4]), 2)]
                        for r in rows if r[:10] >= start and r.count(",") >= 4]
        return out if out["SPY"] else None
    except Exception:
        return None


def refresh_market(data):
    """Refresh the cached SPY/QQQ closes used by the chart; keep the old cache on failure."""
    if not data.get("entries"):
        return
    import datetime
    first = min(e["as_of_date"] for e in data["entries"])
    start = (datetime.date.fromisoformat(first) - datetime.timedelta(days=10)).isoformat()
    closes = fetch_closes(start)
    if closes:  # during market hours Alpaca returns today's forming bar — plot completed sessions only
        now_et = datetime.datetime.now(ZoneInfo("America/New_York"))
        if now_et.hour < 16:
            today = now_et.date().isoformat()
            closes = {sym: [b for b in bars if b[0] != today] for sym, bars in closes.items()}
    if closes and closes["SPY"]:
        data["market"] = {"start": start, "closes": closes,
                          "updated": max(d for d, _ in closes["SPY"])}


def build_grok_chart(data):
    """Inline-SVG chart: Grok rating (left, 0-10) vs SPY/QQQ % (right) since the first entry."""
    market = data.get("market")
    daily = {}  # date -> newest entry that day (post-close > intraday > pre-market)
    for e in data.get("entries", []):
        d = e["as_of_date"]
        if d not in daily or SESSION_RANK.get(e.get("session", "post-close"), 1) > SESSION_RANK.get(daily[d].get("session", "post-close"), 1):
            daily[d] = e
    if not daily or not market:
        return ""
    first = min(daily)
    closes = market["closes"]
    base = {sym: next((c for d, c in reversed(closes[sym]) if d <= first), None) for sym in ("SPY", "QQQ")}
    if not base["SPY"] or not base["QQQ"]:
        return ""
    pct = {sym: [(d, (c / base[sym] - 1) * 100) for d, c in closes[sym] if d >= first]
           for sym in ("SPY", "QQQ")}
    dates = sorted({d for d in daily} | {d for s in pct.values() for d, _ in s})
    if len(dates) < 2:
        return ""
    x_of = {d: i for i, d in enumerate(dates)}
    W, H, L, R, T, B = 920, 300, 34, 56, 34, 24
    px = lambda d: L + x_of[d] * (W - L - R) / (len(dates) - 1)
    ry = lambda r: T + (10 - r) * (H - T - B) / 10
    allpct = [v for s in pct.values() for _, v in s] or [0]
    lo, hi = min(min(allpct), 0), max(max(allpct), 0)
    pad = max((hi - lo) * 0.12, 0.4)
    lo, hi = lo - pad, hi + pad
    py = lambda v: T + (hi - v) * (H - T - B) / (hi - lo)
    svg = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-label="Grok risk rating vs SPY and QQQ performance">']
    for r in (0, 2.5, 5, 7.5, 10):  # left grid: rating scale
        dash = ' stroke-dasharray="5 4"' if r == 5 else ""
        svg.append(f'<line x1="{L}" y1="{ry(r):.1f}" x2="{W - R}" y2="{ry(r):.1f}" '
                   f'stroke="{"#c9c6be" if r == 5 else "#ecebe6"}" stroke-width="1"{dash}/>')
        svg.append(f'<text x="{L - 6}" y="{ry(r) + 3.5:.1f}" text-anchor="end" '
                   f'font-size="10" fill="#666a70" font-family="IBM Plex Mono,monospace">{r:g}</text>')
    step = max(1, round((hi - lo) / 4))
    tick = int(lo // step) * step
    while tick <= hi:  # right ticks: percent scale
        if lo <= tick <= hi:
            svg.append(f'<text x="{W - R + 6}" y="{py(tick) + 3.5:.1f}" font-size="10" fill="#666a70" '
                       f'font-family="IBM Plex Mono,monospace">{f"{tick:+g}%" if tick else "0%"}</text>')
        tick += step
    for d in dates:  # sparse date labels
        if x_of[d] % max(1, len(dates) // 9) == 0:
            label = d[5:].replace("-", "/")
            svg.append(f'<text x="{px(d):.1f}" y="{H - 8}" text-anchor="middle" font-size="10" '
                       f'fill="#666a70" font-family="IBM Plex Mono,monospace">{label}</text>')
    for sym, color in (("SPY", "#4a6fa5"), ("QQQ", "#8a5aa5")):
        pts = " ".join(f"{px(d):.1f},{py(v):.1f}" for d, v in pct[sym])
        svg.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="1.8" '
                   f'stroke-linejoin="round" stroke-linecap="round"/>')
        d_end, v_end = pct[sym][-1]
        svg.append(f'<text x="{px(d_end) - 4:.1f}" y="{py(v_end) - 6:.1f}" text-anchor="end" font-size="10" '
                   f'fill="{color}" font-family="IBM Plex Mono,monospace" font-weight="600">{sym}</text>')
    rpts = [(d, float(daily[d]["risk_appetite"]), daily[d]) for d in sorted(daily)]
    svg.append('<polyline points="' + " ".join(f"{px(d):.1f},{ry(r):.1f}" for d, r, _ in rpts) +
               '" fill="none" stroke="#1c1e22" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>')
    for d, r, e in rpts:
        color = VHEX.get(e["stance"], "#1c1e22")
        svg.append(f'<circle cx="{px(d):.1f}" cy="{ry(r):.1f}" r="4" fill="{color}" stroke="#fff" stroke-width="1.5">'
                   f'<title>{d} · {e.get("session", "post-close")} · {e["stance"]} · {r:g}/10</title></circle>')
    legend = [("#1c1e22", "Grok rating (0–10, left)"), ("#4a6fa5", "SPY %"), ("#8a5aa5", "QQQ %")]
    lx = L
    for color, label in legend:
        svg.append(f'<line x1="{lx}" y1="12" x2="{lx + 16}" y2="12" stroke="{color}" stroke-width="2.4"/>')
        svg.append(f'<text x="{lx + 21}" y="15.5" font-size="10.5" fill="#5c5f66" '
                   f'font-family="IBM Plex Sans,sans-serif">{label}</text>')
        lx += 21 + 7 * len(label) + 18
    svg.append("</svg>")
    basedate = next(d for d, _ in reversed(closes["SPY"]) if d <= first)
    return (f'<div class="card fr-chartcard"><h2>Rating vs the tape'
            f'<span class="card-r">Grok 0–10 vs SPY & QQQ, % from {basedate} close · prices thru {market["updated"]}</span></h2>'
            f'<div class="tw">' + "".join(svg) + "</div></div>")


def main() -> int:
    payload = json.loads(DATA.read_text())
    entry = validate(payload)
    if "market" not in payload:
        refresh_market(payload)
        DATA.write_text(json.dumps(payload, indent=2) + "\n")
    page = PAGE.read_text()
    block = f"{START}\n{render(entry)}\n{END}"
    updated = re.sub(re.escape(START) + r".*?" + re.escape(END), block, page, count=1, flags=re.S)
    if updated == page:
        print(f"[grok-risk] already current: {entry['as_of_date']} · {entry['risk_appetite']}/10")
    else:
        PAGE.write_text(updated)
        print(f"[grok-risk] rendered: {entry['as_of_date']} · {entry['risk_appetite']}/10")
    page = updated

    # Build and insert chart
    chart = build_grok_chart(payload)
    if chart:
        chart_block = f"{CHART_START}\n{chart}\n{CHART_END}"
        if CHART_START in page:
            page = page[:page.index(CHART_START)] + chart_block + page[page.index(CHART_END) + len(CHART_END):]
        else:
            page = page.replace(START, chart_block + "\n\n" + START, 1)
        PAGE.write_text(page)
        print(f"[grok-risk] chart updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
