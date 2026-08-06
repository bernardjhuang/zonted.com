#!/usr/bin/env python3
"""Validate and publish one GPT post-close risk journal response.

This adapter intentionally owns only GPT's journal and generated Trading Desk shells.
It never mutates Grok or Fable journal data.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import importlib.util
import json
import pathlib
import subprocess
from typing import Any
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1]
JOURNAL = ROOT / "trading" / "risk-journal.json"
MARKET = ROOT / "trading" / "market-ytd.json"
PAGE = ROOT / "trading" / "gpt-risk" / "index.html"
RISK_MODULE = ROOT / "scripts" / "independent_risk_journal.py"
CHART_START = "<!-- AUTO:GPT_RISK_CHART:START -->"
CHART_END = "<!-- AUTO:GPT_RISK_CHART:END -->"
STANCE_COLORS = {"Risk-on": "#087a42", "Neutral": "#9a621d", "Risk-off": "#c93a4a"}


def load(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def save_atomic(path: pathlib.Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def risk_contract_module():
    spec = importlib.util.spec_from_file_location("independent_risk_journal", RISK_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load independent risk journal contract")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_source_dates(response: dict[str, Any]) -> None:
    cutoff = dt.date.fromisoformat(response["as_of_date"])
    for index, source in enumerate(response["sources"]):
        raw = str(source["as_of"]).strip()[:10]
        try:
            source_date = dt.date.fromisoformat(raw)
        except ValueError:
            continue
        if source_date > cutoff:
            raise ValueError(f"sources[{index}].as_of {source_date} is after journal cutoff {cutoff}")


def adapt_entry(response: dict[str, Any]) -> dict[str, Any]:
    methodology = response["methodology"]
    return {
        "date": response["as_of_date"],
        "author": response["author"],
        "stance": response["stance"],
        "risk_appetite": response["risk_appetite"],
        "lean": f'{response["confidence"]} confidence · {methodology["name"]}',
        "headline": response["headline"],
        "journal": response["journal"],
        "what_supports_risk": response["what_supports_risk"],
        "what_holds_it_back": response["what_holds_it_back"],
        "what_changes_my_mind": response["what_changes_my_mind"],
        "source_note": "Sources: "
        + " · ".join(f'{source["title"]} — {source["url"]}' for source in response["sources"])
        + ". Limitations: "
        + " ".join(response["limitations"]),
        "score_interpretation": response["score_interpretation"],
        "methodology": methodology,
        "sources": response["sources"],
        "limitations": response["limitations"],
    }


def prepend_for_date(entries: list[dict[str, Any]], entry: dict[str, Any]) -> list[dict[str, Any]]:
    return [entry] + [old for old in entries if old.get("date") != entry["date"]]


def fetch_closes(start: str) -> dict[str, list[list[Any]]] | None:
    """Fetch split-adjusted completed-session closes for the chart."""
    try:
        keys: dict[str, str] = {}
        env_path = pathlib.Path.home() / ".config" / "trading" / "alpaca.env"
        for raw in env_path.read_text().splitlines():
            line = raw.strip()
            if line.startswith("export "):
                line = line[7:]
            if "=" in line and not line.startswith("#"):
                name, value = line.split("=", 1)
                keys[name.strip()] = value.strip().strip('"').strip("'")
        request = Request(
            "https://data.alpaca.markets/v2/stocks/bars"
            f"?symbols=SPY,QQQ&timeframe=1Day&start={start}&limit=10000&adjustment=split&feed=sip",
            headers={"APCA-API-KEY-ID": keys["APCA_KEY"], "APCA-API-SECRET-KEY": keys["APCA_SECRET"]},
        )
        bars = json.load(urlopen(request, timeout=20))["bars"]
        closes = {
            symbol: [[bar["t"][:10], round(float(bar["c"]), 2)] for bar in bars[symbol]]
            for symbol in ("SPY", "QQQ")
        }
        now_et = dt.datetime.now(ZoneInfo("America/New_York"))
        if now_et.hour < 16:
            today = now_et.date().isoformat()
            closes = {symbol: [row for row in rows if row[0] != today] for symbol, rows in closes.items()}
        return closes
    except Exception:
        pass

    try:
        closes = {}
        for symbol, stooq in (("SPY", "spy.us"), ("QQQ", "qqq.us")):
            request = Request(
                f"https://stooq.com/q/d/l/?s={stooq}&i=d",
                headers={"User-Agent": "Mozilla/5.0 (compatible; Zonted/1.0)"},
            )
            rows = urlopen(request, timeout=20).read().decode().splitlines()[1:]
            closes[symbol] = [
                [row.split(",")[0], round(float(row.split(",")[4]), 2)]
                for row in rows
                if row[:10] >= start and row.count(",") >= 4
            ]
        return closes if closes["SPY"] and closes["QQQ"] else None
    except Exception:
        return None


def refresh_market(journal: dict[str, Any], required_date: str) -> None:
    """Refresh chart prices and fail closed unless both series reach the journal date."""
    first = min(entry["date"] for entry in journal["entries"])
    start = (dt.date.fromisoformat(first) - dt.timedelta(days=10)).isoformat()
    closes = fetch_closes(start)
    if closes and all(any(date == required_date for date, _ in closes.get(symbol, [])) for symbol in ("SPY", "QQQ")):
        journal["chart"] = {
            "market": {"start": start, "closes": closes, "updated": required_date}
        }
        return

    cached = (journal.get("chart") or {}).get("market") or {}
    cached_closes = cached.get("closes") or {}
    if cached.get("updated") == required_date and all(
        any(date == required_date for date, _ in cached_closes.get(symbol, []))
        for symbol in ("SPY", "QQQ")
    ):
        return
    raise ValueError(f"GPT risk chart prices do not include completed session {required_date}")


def build_chart(journal: dict[str, Any]) -> str:
    """Render GPT ratings against SPY and QQQ returns as an inline SVG."""
    entries = journal.get("entries") or []
    market = (journal.get("chart") or {}).get("market")
    if not entries or not market:
        return ""
    daily = {entry["date"]: entry for entry in entries}
    first = min(daily)
    closes = market["closes"]
    base = {
        symbol: next((close for date, close in reversed(closes[symbol]) if date <= first), None)
        for symbol in ("SPY", "QQQ")
    }
    if not base["SPY"] or not base["QQQ"]:
        return ""
    pct = {
        symbol: [(date, (close / base[symbol] - 1) * 100) for date, close in closes[symbol] if date >= first]
        for symbol in ("SPY", "QQQ")
    }
    dates = sorted(set(daily) | {date for rows in pct.values() for date, _ in rows})
    if len(dates) < 2:
        return ""

    width, height, left, right, top, bottom = 920, 300, 34, 56, 34, 24
    x_index = {date: index for index, date in enumerate(dates)}
    x = lambda date: left + x_index[date] * (width - left - right) / (len(dates) - 1)
    rating_y = lambda rating: top + (10 - rating) * (height - top - bottom) / 10
    all_pct = [value for rows in pct.values() for _, value in rows] or [0]
    low, high = min(min(all_pct), 0), max(max(all_pct), 0)
    padding = max((high - low) * 0.12, 0.4)
    low, high = low - padding, high + padding
    price_y = lambda value: top + (high - value) * (height - top - bottom) / (high - low)

    svg = [
        f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" tabindex="0" '
        'aria-label="GPT risk rating vs SPY and QQQ performance">',
        '<desc>GPT post-close risk ratings on a zero-to-ten scale compared with SPY and QQQ percentage returns.</desc>',
    ]
    for rating in (0, 2.5, 5, 7.5, 10):
        dash = ' stroke-dasharray="5 4"' if rating == 5 else ""
        svg.append(
            f'<line x1="{left}" y1="{rating_y(rating):.1f}" x2="{width - right}" y2="{rating_y(rating):.1f}" '
            f'stroke="{"#c9c6be" if rating == 5 else "#ecebe6"}" stroke-width="1"{dash}/>'
        )
        svg.append(
            f'<text x="{left - 6}" y="{rating_y(rating) + 3.5:.1f}" text-anchor="end" font-size="10" '
            f'fill="#666a70" font-family="IBM Plex Mono,monospace">{rating:g}</text>'
        )
    step = max(1, round((high - low) / 4))
    tick = int(low // step) * step
    while tick <= high:
        if low <= tick <= high:
            tick_label = f"{tick:+g}%" if tick else "0%"
            svg.append(
                f'<text x="{width - right + 6}" y="{price_y(tick) + 3.5:.1f}" font-size="10" '
                f'fill="#666a70" font-family="IBM Plex Mono,monospace">{tick_label}</text>'
            )
        tick += step
    label_every = max(1, len(dates) // 9)
    for date in dates:
        if x_index[date] % label_every == 0:
            label = date[5:].replace("-", "/")
            svg.append(
                f'<text x="{x(date):.1f}" y="{height - 8}" text-anchor="middle" font-size="10" '
                f'fill="#666a70" font-family="IBM Plex Mono,monospace">{label}</text>'
            )
    for symbol, color in (("SPY", "#4a6fa5"), ("QQQ", "#8a5aa5")):
        points = " ".join(f"{x(date):.1f},{price_y(value):.1f}" for date, value in pct[symbol])
        svg.append(
            f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="1.8" '
            'stroke-linejoin="round" stroke-linecap="round"/>'
        )
        end_date, end_value = pct[symbol][-1]
        svg.append(
            f'<text x="{x(end_date) - 4:.1f}" y="{price_y(end_value) - 6:.1f}" text-anchor="end" '
            f'font-size="10" fill="{color}" font-family="IBM Plex Mono,monospace" font-weight="600">{symbol}</text>'
        )
    ratings = [(date, float(daily[date]["risk_appetite"]), daily[date]) for date in sorted(daily)]
    svg.append(
        '<polyline points="'
        + " ".join(f"{x(date):.1f},{rating_y(rating):.1f}" for date, rating, _ in ratings)
        + '" fill="none" stroke="#1c1e22" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>'
    )
    for date, rating, entry in ratings:
        label = f'{date} · model journal · {entry["stance"]} · {rating:g}/10'
        svg.append(
            f'<circle cx="{x(date):.1f}" cy="{rating_y(rating):.1f}" r="4" '
            f'fill="{STANCE_COLORS[entry["stance"]]}" stroke="#fff" stroke-width="1.5" '
            f'tabindex="0" role="img" aria-label="{html.escape(label, quote=True)}"><title>{html.escape(label)}</title></circle>'
        )
    legend = (("#1c1e22", "GPT rating (0–10, left)"), ("#4a6fa5", "SPY %"), ("#8a5aa5", "QQQ %"))
    legend_x = left
    for color, label in legend:
        svg.append(f'<line x1="{legend_x}" y1="12" x2="{legend_x + 16}" y2="12" stroke="{color}" stroke-width="2.4"/>')
        svg.append(
            f'<text x="{legend_x + 21}" y="15.5" font-size="10.5" fill="#5c5f66" '
            f'font-family="IBM Plex Sans,sans-serif">{label}</text>'
        )
        legend_x += 21 + 7 * len(label) + 18
    svg.append("</svg>")
    base_date = next(date for date, _ in reversed(closes["SPY"]) if date <= first)
    return (
        '<div class="card risk-rating-chart"><h2>Rating vs the tape'
        f'<span class="card-r">GPT 0–10 vs SPY &amp; QQQ, % from {base_date} close · prices thru {market["updated"]}</span></h2>'
        '<div class="tw">' + "".join(svg) + "</div></div>"
    )


def render_chart_page(journal: dict[str, Any]) -> None:
    chart = build_chart(journal)
    if not chart:
        raise ValueError("could not render GPT risk chart")
    block = f"{CHART_START}\n{chart}\n{CHART_END}"
    page = PAGE.read_text()
    if CHART_START in page and CHART_END in page:
        page = page[: page.index(CHART_START)] + block + page[page.index(CHART_END) + len(CHART_END) :]
    else:
        page = page.replace('<div id="risk-live">', block + '\n<div id="risk-live">', 1)
    PAGE.write_text(page)


def publish(response_path: pathlib.Path) -> dict[str, Any]:
    response = load(response_path)
    market_date = str(load(MARKET).get("as_of") or "")
    if not market_date:
        raise ValueError("market-ytd.json has no as_of date")
    if response.get("as_of_date") != market_date:
        raise ValueError(
            f'GPT response date {response.get("as_of_date")!r} does not match market date {market_date!r}'
        )
    if response.get("session") != "post-close":
        raise ValueError("GPT journal publisher accepts post-close responses only")

    contract = risk_contract_module()
    contract.validate_entry(
        response,
        contract.MODELS_BY_SLUG["gpt"],
        market_date,
        "post-close",
    )
    if response["decision_status"] != "publishable":
        raise ValueError("refusing to publish an insufficient_data response")
    validate_source_dates(response)

    journal = load(JOURNAL)
    entry = adapt_entry(response)
    journal["updated_at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    journal["entries"] = prepend_for_date(journal.get("entries", []), entry)
    refresh_market(journal, market_date)
    save_atomic(JOURNAL, journal)
    render_chart_page(journal)

    subprocess.run(
        ["python3", "scripts/build-trading-desk.py", "--mode", "close"],
        cwd=ROOT,
        check=True,
    )
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--response", required=True, type=pathlib.Path)
    args = parser.parse_args()
    entry = publish(args.response)
    print(
        f'published GPT risk journal {entry["date"]}: '
        f'{entry["stance"]} ({entry["risk_appetite"]:g}/10)'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
