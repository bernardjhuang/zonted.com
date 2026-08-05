#!/usr/bin/env python3
"""Append either a mechanical Fable rubric entry or an independent model journal entry."""
import argparse
import glob
import html as html_lib
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "trading", "fable-risk", "index.html")
DATA = os.path.join(ROOT, "trading", "fable-risk.json")
START, END = "<!-- AUTO:FABLE_RISK:START -->", "<!-- AUTO:FABLE_RISK:END -->"
VCLS = {"RISK-ON": "fr-on", "NEUTRAL": "fr-neutral", "RISK-OFF": "fr-off"}
SCLS = {1: ("enter", "+1 on"), 0: ("watch", "0 neutral"), -1: ("short", "−1 off")}
FCLS = {"off": ("short", "leans off"), "watch": ("watch", "watch"), "on": ("enter", "leans on")}
SESSION_RANK = {"pre-market": 0, "intraday": 1, "post-close": 2}


def session_of(entry):
    return entry.get("session", "pre-market")


def rating_of(entry):
    return round((entry["score"] / entry["n_signals"] + 1) * 5, 1)


def render_forward(forward):
    if not forward:
        return ""
    rows = ""
    for item in forward["watch"]:
        cls, label = FCLS[item["lean"]]
        rows += (f'<tr><td>{item["name"]}<span class="sub">{item["why"]}</span></td>'
                 f'<td class="num">{item["detail"]}</td>'
                 f'<td><span class="tag {cls}">{label}</span></td></tr>')
    forecast = forward["forecast"]
    grading = (f'\n<div class="mkt"><span class="lbl"><b>Grading:</b> {forward["grading"]}</span></div>'
               if forward.get("grading") else "")
    return f'''<div class="card"><h2>Forward watch<span class="card-r">rubric v2 · {forward["horizon"]} · advisory, not in the composite</span></h2>
<div class="tw"><table style="min-width:560px"><thead><tr><th>Watch item</th><th class="num">Reading</th><th>Lean</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<div class="mkt"><span class="lbl"><b>Falsifiable call:</b> {forecast["claim"]} — <b>{forecast["prob"]}</b> · resolves {forecast["resolves"]}</span></div>{grading}</div>
'''


def render(entry, open_=True):
    rating = rating_of(entry)
    rows = ""
    for signal in entry["signals"]:
        cls, label = SCLS[int(signal["score"])]
        rows += (f'<tr><td>{signal["name"]}<span class="sub">{signal["rule"]}</span></td>'
                 f'<td class="num">{signal["value"]}</td>'
                 f'<td><span class="tag {cls}">{label}</span></td></tr>')
    sources = " · ".join(f'<a href="{item["u"]}" rel="noopener">{item["t"]}</a>' for item in entry["sources"])
    body = f'''<div class="fr-verdict {VCLS[entry["verdict"]]}">
  <div class="fr-call">{entry["verdict"]}</div>
  <div class="fr-sub">{entry["subtitle"]} · signal sum {entry["score"]:+d} of {entry["n_signals"]} · composite {entry["composite"]}</div>
  <div class="fr-rating" title="0 = maximum risk-off · 10 = maximum risk-on">
    <span class="fr-rating-num">{rating:g}</span><span class="fr-rating-scale">/ 10</span>
    <span class="fr-rating-bar"><span class="fr-rating-fill" style="width:{100 - rating * 10:g}%"></span></span>
    <span class="fr-rating-cap">risk appetite</span>
  </div>
</div>
{''.join(entry["narrative"])}
<div class="card"><h2>Signal ledger<span class="card-r">rubric v1 · each −1 / 0 / +1</span></h2>
<div class="tw"><table style="min-width:560px"><thead><tr><th>Signal</th><th class="num">Reading</th><th>Score</th></tr></thead>
<tbody>{rows}</tbody></table></div></div>
<div class="card"><h2>What flips this call</h2>
<div class="mkt"><span class="lbl"><b>To risk-off:</b> {entry["flips"]["to_off"]}</span></div>
<div class="mkt"><span class="lbl"><b>To risk-on:</b> {entry["flips"]["to_on"]}</span></div></div>
{render_forward(entry.get("forward"))}<p class="footnote">Sources: {sources}</p>'''
    return (f'<details class="fr-entry"{" open" if open_ else ""}>'
            f'<summary><time datetime="{entry["date"]}">{entry["date"]}</time>'
            f'<span class="fr-sumverdict {VCLS[entry["verdict"]]}">{entry["verdict"]}</span>'
            f'<span class="fr-sumsession">{session_of(entry)}</span><span class="fr-sumfor">assessment for {entry["assess_for"]}</span><span class="fr-sumrating">{rating:g}/10</span></summary>'
            f'<div class="fr-body">{body}</div></details>')


def render_model_entry(entry, open_=True):
    esc = lambda value: html_lib.escape(str(value), quote=True)
    stance = entry["stance"]
    verdict = stance.upper()
    cls = {"Risk-on": "fr-on", "Neutral": "fr-neutral", "Risk-off": "fr-off"}[stance]
    rating = float(entry["risk_appetite"])
    paragraphs = "".join(f"<p>{esc(value)}</p>" for value in entry["journal"])
    supports = "".join(f"<li>{esc(value)}</li>" for value in entry["what_supports_risk"])
    restraints = "".join(f"<li>{esc(value)}</li>" for value in entry["what_holds_it_back"])
    changes = "".join(f"<li>{esc(value)}</li>" for value in entry["what_changes_my_mind"])
    sources = " · ".join(
        f'<a href="{esc(source["url"])}" rel="noopener">{esc(source["title"])}</a>'
        for source in entry["sources"]
    )
    body = f'''<div class="fr-verdict {cls}">
  <div class="fr-call">{esc(verdict)}</div>
  <div class="fr-sub">independent model-selected methodology · {esc(entry["confidence"])} confidence</div>
  <div class="fr-rating" title="0 = maximum risk-off · 10 = maximum risk-on">
    <span class="fr-rating-num">{rating:g}</span><span class="fr-rating-scale">/ 10</span>
    <span class="fr-rating-bar"><span class="fr-rating-fill" style="width:{100 - rating * 10:g}%"></span></span>
    <span class="fr-rating-cap">risk appetite</span>
  </div>
</div>
<h2>{esc(entry["headline"])}</h2>{paragraphs}
<div class="card"><h2>What supports risk</h2><ul>{supports}</ul></div>
<div class="card"><h2>What holds it back</h2><ul>{restraints}</ul></div>
<div class="card"><h2>What changes this call</h2><ul>{changes}</ul></div>
<details class="trading-method"><summary>Methodology and limitations</summary><p><b>{esc(entry["methodology"]["name"])}</b> — {esc(entry["methodology"]["explanation"])}</p><p>{esc(" · ".join(entry["limitations"]))}</p></details>
<p class="footnote">Sources: {sources}</p>'''
    return (f'<details class="fr-entry fr-model-entry"{" open" if open_ else ""}>'
            f'<summary><time datetime="{esc(entry["as_of_date"])}">{esc(entry["as_of_date"])}</time>'
            f'<span class="fr-sumverdict {cls}">{esc(verdict)}</span>'
            f'<span class="fr-sumsession">{esc(entry["session"])} · journal</span>'
            f'<span class="fr-sumfor">independent Claude Fable 5 journal</span>'
            f'<span class="fr-sumrating">{rating:g}/10</span></summary>'
            f'<div class="fr-body">{body}</div></details>')


CHART_START, CHART_END = "<!-- AUTO:FABLE_CHART:START -->", "<!-- AUTO:FABLE_CHART:END -->"
VHEX = {"fr-on": "#087a42", "fr-off": "#c93a4a", "fr-neutral": "#9a621d"}


def fetch_closes(start):
    """Daily closes for SPY+QQQ from `start`: Alpaca SIP first, Stooq keyless fallback."""
    import urllib.request
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
    if not data["entries"]:
        return
    import datetime
    first = min(e["date"] for e in data["entries"])
    start = (datetime.date.fromisoformat(first) - datetime.timedelta(days=10)).isoformat()
    closes = fetch_closes(start)
    if closes:  # during market hours Alpaca returns today's forming bar — plot completed sessions only
        from zoneinfo import ZoneInfo
        now_et = datetime.datetime.now(ZoneInfo("America/New_York"))
        if now_et.hour < 16:
            today = now_et.date().isoformat()
            closes = {sym: [b for b in bars if b[0] != today] for sym, bars in closes.items()}
    if closes and closes["SPY"]:
        data["market"] = {"start": start, "closes": closes,
                          "updated": max(d for d, _ in closes["SPY"])}


def build_chart(data):
    """Inline-SVG chart: Fable rating (left, 0-10) vs SPY/QQQ % (right) since the first entry."""
    market = data.get("market")
    daily = {}  # date -> newest entry that day (post-close > intraday > pre-market)
    for e in data["entries"]:
        if e["date"] not in daily or SESSION_RANK.get(session_of(e), 1) > SESSION_RANK.get(session_of(daily[e["date"]]), 1):
            daily[e["date"]] = e
    if not daily or not market:
        return ""
    first = min(daily)
    closes = market["closes"]
    base = {sym: next((c for d, c in reversed(closes[sym]) if d <= first), None) for sym in ("SPY", "QQQ")}
    if not base["SPY"] or not base["QQQ"]:
        return ""
    pct = {sym: [(d, (c / base[sym] - 1) * 100) for d, c in closes[sym] if d >= first]
           for sym in ("SPY", "QQQ")}
    journal = [(m["as_of_date"], float(m["risk_appetite"]), m["stance"]) for m in data.get("model_entries", [])]
    dates = sorted({d for d in daily} | {d for s in pct.values() for d, _ in s} | {d for d, _, _ in journal})
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
           f'aria-label="Fable risk rating vs SPY and QQQ performance">']
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
    rpts = [(d, rating_of(daily[d]), daily[d]) for d in sorted(daily)]
    svg.append('<polyline points="' + " ".join(f"{px(d):.1f},{ry(r):.1f}" for d, r, _ in rpts) +
               '" fill="none" stroke="#1c1e22" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>')
    for d, r, e in rpts:
        color = VHEX[VCLS[e["verdict"]]]
        svg.append(f'<circle cx="{px(d):.1f}" cy="{ry(r):.1f}" r="4" fill="{color}" stroke="#fff" stroke-width="1.5">'
                   f'<title>{d} · {session_of(e)} · {e["verdict"]} · {rating_of(e):g}/10</title></circle>')
    for d, r, stance in journal:
        svg.append(f'<circle cx="{px(d):.1f}" cy="{ry(r):.1f}" r="4.5" fill="none" stroke="#1c1e22" stroke-width="1.6">'
                   f'<title>{d} · model journal · {stance} · {r:g}/10</title></circle>')
    legend = [("#1c1e22", "Fable rating (0–10, left)"), ("#4a6fa5", "SPY %"), ("#8a5aa5", "QQQ %")]
    lx = L
    for color, label in legend + ([(None, "○ model journal")] if journal else []):
        if color:
            svg.append(f'<line x1="{lx}" y1="12" x2="{lx + 16}" y2="12" stroke="{color}" stroke-width="2.4"/>')
            svg.append(f'<text x="{lx + 21}" y="15.5" font-size="10.5" fill="#5c5f66" '
                       f'font-family="IBM Plex Sans,sans-serif">{label}</text>')
            lx += 21 + 7 * len(label) + 18
        else:
            svg.append(f'<text x="{lx}" y="15.5" font-size="10.5" fill="#5c5f66" '
                       f'font-family="IBM Plex Sans,sans-serif">{label}</text>')
    svg.append("</svg>")
    basedate = next(d for d, _ in reversed(closes["SPY"]) if d <= first)
    return (f'<div class="card fr-chartcard"><h2>Rating vs the tape'
            f'<span class="card-r">Fable 0–10 vs SPY &amp; QQQ, % from {basedate} close · prices thru {market["updated"]}</span></h2>'
            f'<div class="tw">' + "".join(svg) + "</div></div>")


def refresh_fable_chip(data):
    """Point the sitewide Fable nav chip at the newest entry (either type)."""
    newest = max(data["entries"] + data["model_entries"],
                 key=lambda e: ((e.get("date") or e["as_of_date"]), SESSION_RANK.get(session_of(e), 1)))
    value = float(newest.get("risk_appetite", newest.get("rating")))
    stance = str(newest.get("stance", newest.get("verdict")))
    state = "on" if value > 5 else "off" if value < 5 else "neutral"
    chip = (f'<a class="chip chip-fable chip-{state}" href="/trading/fable-risk/" '
            f'title="Fable risk appetite — {html_lib.escape(stance)} · {value:g}/10">Fable {value:g}</a>')
    pattern = r'<a class="chip chip-fable [^"]+" href="/trading/fable-risk/".*?</a>'
    for path in sorted(glob.glob(os.path.join(ROOT, "trading", "**", "index.html"), recursive=True)) + [os.path.join(ROOT, "trading", "pipeline.html")]:
        if not os.path.exists(path):
            continue
        source = open(path).read()
        updated = re.sub(pattern, chip, source)
        if updated != source:
            open(path, "w").write(updated)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entry")
    args = parser.parse_args()
    entry = json.load(open(args.entry))
    data = {"schema_version": 1, "entries": [], "model_entries": []}
    if os.path.exists(DATA):
        data = json.load(open(DATA))
        data.setdefault("model_entries", [])
    if entry.get("prompt_version") == "zonted-independent-risk-v1":
        data["model_entries"] = [existing for existing in data["model_entries"]
                                 if (existing["as_of_date"], existing["session"]) != (entry["as_of_date"], entry["session"])]
        data["model_entries"].insert(0, entry)
    else:
        entry["rating"] = rating_of(entry)
        entry["session"] = session_of(entry)
        data["entries"] = [existing for existing in data["entries"]
                           if (existing["date"], session_of(existing)) != (entry["date"], entry["session"])]
        data["entries"].insert(0, entry)
    refresh_market(data)  # both entry types refresh the chart's price cache; failure keeps the old cache
    with open(DATA, "w") as handle:
        json.dump(data, handle, indent=1)
        handle.write("\n")

    page = open(PAGE).read()
    start, end = page.index(START) + len(START), page.index(END)
    combined = [(item.get("date") or item["as_of_date"], SESSION_RANK.get(session_of(item), 1), renderer, item)
                for items, renderer in ((data["entries"], render), (data["model_entries"], render_model_entry))
                for item in items]
    combined.sort(key=lambda row: row[:2], reverse=True)
    rendered = [renderer(item, index == 0) for index, (_, _, renderer, item) in enumerate(combined)]
    block = "\n" + "\n".join(rendered) + "\n"
    page = page[:start] + block + page[end:]
    chart = build_chart(data)
    if chart:
        chart_block = f"{CHART_START}\n{chart}\n{CHART_END}"
        if CHART_START in page:
            page = page[:page.index(CHART_START)] + chart_block + page[page.index(CHART_END) + len(CHART_END):]
        else:
            page = page.replace(START, chart_block + "\n\n" + START, 1)
    open(PAGE, "w").write(page)
    refresh_fable_chip(data)
    if entry.get("prompt_version"):
        print(f"fable-risk: {entry['as_of_date']} {entry['stance']} ({entry['risk_appetite']}/10) · independent model journal")
    else:
        print(f"fable-risk: {entry['date']} {entry['verdict']} ({entry['composite']}) · {len(data['entries'])} mechanical entries")


if __name__ == "__main__":
    main()
