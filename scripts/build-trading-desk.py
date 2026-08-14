#!/usr/bin/env python3
"""Build the merged Zonted trading desk from checked-in source data.

The default/close mode consumes completed-session artifacts plus a date-matched,
privacy-safe fallback quote file for OTC symbols omitted by primary feeds. Morning mode
accepts an explicit validated quote file, overlays the current session on Desk charts,
and leaves completed-session statistical artifacts untouched.
No network calls are made in any mode.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import math
import re
import statistics
from pathlib import Path
from zoneinfo import ZoneInfo

from trading_shell import normalize_trading_subnav, render_sector_status_pills, replace_sector_status_pills

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "trading/index.html"
PIPELINE = ROOT / "trading/pipeline.html"
HYPOTHESES = ROOT / "trading/hypothesis-source.txt"
POSITIONS = ROOT / "trading/desk-positions.json"
VALUATIONS = ROOT / "trading/hypothesis-valuations.json"
CHARTS = ROOT / "trading/hypothesis-charts.json"
SCAN = ROOT / "trading/scan-charts.json"
VWAP = ROOT / "trading/vwap-charts.json"
MARKET = ROOT / "trading/market-ytd.json"
DESK_CSS = ROOT / "trading/desk.css"
DESK_JS = ROOT / "trading/desk.js"
CHART_MODAL_JS = ROOT / "js/hypothesis-chart-modal.b42a9700.js"
CLOSE_QUOTES = ROOT / "trading/desk-close-quotes.json"
START_POS = "<!-- AUTO:DESK_POSITIONS:START -->"
END_POS = "<!-- AUTO:DESK_POSITIONS:END -->"
START_HYP = "<!-- AUTO:DESK_HYPOTHESES:START -->"
END_HYP = "<!-- AUTO:DESK_HYPOTHESES:END -->"
COLGROUP = '<colgroup><col style="width:18%"><col style="width:7%"><col style="width:6%"><col style="width:10%"><col style="width:5%"><col style="width:6%"><col style="width:6%"><col style="width:23%"><col style="width:13%"><col style="width:6%"></colgroup>'
OTC = {"BYDDY", "NTDOY"}
CT = ZoneInfo("America/Chicago")


def load(path: Path):
    return json.loads(path.read_text())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def content_asset_path(source: Path) -> Path:
    return source.with_name(f"{source.stem}.{digest(source)}{source.suffix}")


def content_asset_ref(source: Path) -> str:
    return f"/trading/{content_asset_path(source).name}"


def emit_content_assets() -> None:
    for source in (DESK_CSS, DESK_JS):
        target = content_asset_path(source)
        if not target.exists() or target.read_bytes() != source.read_bytes():
            target.write_bytes(source.read_bytes())


def money(value: float | None) -> str:
    if value is None:
        return "—"
    return f"${value:,.2f}" if abs(value) < 100 else f"${value:,.0f}"


def pct(value: float, *, signed: bool = True) -> str:
    return f"{value:+.1f}%" if signed else f"{value:.1f}%"


def article_metadata(source: str) -> dict[str, dict[str, str]]:
    pattern = re.compile(
        r'<article class="hypothesis-detail" id="hypothesis-([a-z0-9.-]+)-setup"([^>]*)>', re.S
    )
    out: dict[str, dict[str, str]] = {}
    for raw_symbol, attrs in pattern.findall(source):
        symbol = raw_symbol.upper()
        values = {}
        for key in ("catalyst", "catalyst-name", "trigger", "stance"):
            match = re.search(rf'data-desk-{key}="([^"]+)"', attrs)
            if not match:
                raise ValueError(f"{symbol} is missing data-desk-{key}")
            values[key] = html.unescape(match.group(1))
        out[symbol] = values
    if not out:
        raise ValueError("Expected at least one hypothesis article")
    return out


def validate_status_market(status: dict) -> dict[str, float]:
    values = {key: status.get(key) for key in ("spy", "spy_day_pct", "vix")}
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) for value in values.values()):
        raise ValueError("Status market needs finite SPY, SPY day change, and VIX values")
    normalized = {key: float(status[key]) for key in values}
    if normalized["spy"] <= 0 or normalized["vix"] <= 0 or not -100 < normalized["spy_day_pct"] < 100:
        raise ValueError(f"Implausible status market: {normalized}")
    return normalized


def close_status_market() -> dict[str, float]:
    payload = load(MARKET)
    points = payload.get("points") or []
    if payload.get("schema_version") != 2 or len(points) < 2 or payload.get("as_of") != points[-1].get("date"):
        raise ValueError("Status bar needs a current trailing-one-year market payload")
    latest, previous = points[-1], points[-2]
    return validate_status_market({
        "spy": latest.get("spy"),
        "spy_day_pct": (float(latest["spy"]) / float(previous["spy"]) - 1) * 100,
        "vix": latest.get("vix"),
    })


def quotes_from(path: Path | None) -> tuple[dict[str, dict[str, float]], dt.datetime | None, dict[str, float] | None]:
    if path is None:
        return {}, None, None
    payload = load(path)
    if payload.get("schema_version") != 1:
        raise ValueError("Desk quote payload must use schema_version 1")
    quotes = payload.get("quotes") or {}
    stamp = dt.datetime.fromisoformat(str(payload["generated_at"]).replace("Z", "+00:00"))
    for symbol, quote in quotes.items():
        price = quote.get("price")
        day = quote.get("day_pct")
        if not isinstance(price, (int, float)) or price <= 0:
            raise ValueError(f"Invalid Desk price for {symbol}")
        if not isinstance(day, (int, float)) or not -100 < day < 1000:
            raise ValueError(f"Invalid Desk day change for {symbol}")
        source = quote.get("source")
        if source not in {"alpaca_iex", "robinhood"}:
            raise ValueError(f"Invalid Desk quote source for {symbol}: {source!r}")
    status = payload.get("status_market")
    return quotes, stamp, validate_status_market(status) if isinstance(status, dict) else None


def resolve_quote_path(mode: str, explicit: Path | None, fallback: Path = CLOSE_QUOTES) -> Path | None:
    if explicit is not None:
        return explicit
    if mode == "close" and fallback.is_file():
        return fallback
    return None


def live_stamp(stamp: dt.datetime) -> str:
    return stamp.astimezone(CT).strftime("Live · %B %-d, %Y · %-I:%M %p CT")


def render_status_metrics(page: str, positions: int, status: dict[str, float]) -> str:
    spy = float(status["spy"])
    spy_day = float(status["spy_day_pct"])
    vix = float(status["vix"])
    day_class = "up" if spy_day >= 0 else "down"
    day_text = f"{spy_day:+.1f}%".replace("-", "−")
    metrics = (
        f'\n    <span class="metric" data-status-spy="{spy:.2f}" data-status-spy-day="{spy_day:.4f}"><span class="k">SPY</span>{spy:.2f} <span class="{day_class}">{day_text}</span></span>'
        f'\n    <span class="metric" data-status-vix="{vix:.2f}"><span class="k">VIX</span>{vix:.2f}</span>'
        f'\n    <span class="metric" data-status-open="{positions}"><span class="k">Open</span>{positions}</span>\n  '
    )
    pattern = r'(<div class="status-metrics">\s*<span class="chipset">.*?</span>).*?(</div>)'
    sector_chips = render_sector_status_pills()
    rendered, count = re.subn(
        pattern,
        lambda match: match.group(1) + sector_chips + metrics + match.group(2),
        page,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise ValueError("Status metrics region not found")
    return rendered


def row_market(
    symbol: str,
    hyp_chart: dict,
    scan_chart: dict | None,
    quote: dict | None,
    quote_date: dt.date | None = None,
) -> dict:
    if symbol in OTC and not quote:
        return {"feed": False, "source": "none", "beta": float(hyp_chart["beta_2y_weekly_vs_spy"])}
    dates = list(hyp_chart["dates"])
    closes = [float(v) for v in hyp_chart["close"]]
    if scan_chart:
        series = scan_chart["series"]
        daily_dates = list(series["dates"])
        daily = [float(v) for v in series["c"]]
        if daily_dates[-1] == dates[-1]:
            closes[-1] = daily[-1]
        elif daily_dates[-1] > dates[-1]:
            dates.append(daily_dates[-1])
            closes.append(daily[-1])
        last = daily[-1]
        day = (daily[-1] / daily[-2] - 1) * 100
        spread = float(scan_chart["stats"]["spread_z"])
    else:
        last = closes[-1]
        day = (closes[-1] / closes[-2] - 1) * 100
        spread = math.nan
    if quote:
        last = float(quote["price"])
        day = float(quote["day_pct"])
        if quote_date is None:
            raise ValueError(f"Desk quote for {symbol} has no session date")
        date_text = quote_date.isoformat()
        if date_text == dates[-1]:
            closes[-1] = last
        elif date_text > dates[-1]:
            dates.append(date_text)
            closes.append(last)
        else:
            raise ValueError(f"Desk quote for {symbol} predates chart history")
    return {
        "feed": True,
        "source": str(quote.get("source")) if quote else "market_history",
        "last": last,
        "day": day,
        "spread": spread,
        "beta": float(hyp_chart["beta_2y_weekly_vs_spy"]),
        "dates": dates,
        "closes": closes,
    }


def polyline(values: list[float], width: float, height: float, pad: float, low: float, high: float) -> str:
    span = high - low or 1.0
    points = []
    for index, value in enumerate(values):
        x = pad + index * (width - 2 * pad) / max(len(values) - 1, 1)
        y = pad + (high - value) * (height - 2 * pad) / span
        points.append(f"{x:.1f},{y:.1f}")
    return " ".join(points)


def plot_polyline(values: list[float], x0: float, x1: float, y0: float, y1: float, low: float, high: float) -> str:
    span = high - low or 1.0
    return " ".join(
        f"{x0 + index * (x1 - x0) / max(len(values) - 1, 1):.1f},{y0 + (high - value) * (y1 - y0) / span:.1f}"
        for index, value in enumerate(values)
    )


def ytd_chart(symbol: str, market: dict, entry: float | None = None, kill: float | None = None) -> str:
    if not market.get("feed"):
        return '<div class="desk-no-feed">— <span>No feed</span></div>'
    pairs = [(dt.date.fromisoformat(d), float(c)) for d, c in zip(market["dates"], market["closes"])]
    cutoff = pairs[-1][0] - dt.timedelta(days=365)
    pairs = [(date, close) for date, close in pairs if date >= cutoff]
    dates = [date.isoformat() for date, _ in pairs]
    closes = [float(c) for _, c in pairs]
    base = closes[0]
    levels: list[tuple[str, float, str]] = [("start", base, f"1Y start {money(base)}")]
    if entry is not None:
        levels.append(("entry", entry, f"Entry {money(entry)}"))
    if kill is not None:
        levels.append(("kill", kill, f"Kill {money(kill)}"))
    domain = closes + [level for _kind, level, _label in levels]
    low, high = min(domain), max(domain)
    margin = max((high - low) * .06, .5)
    low = max(0, low - margin)
    high += margin
    width, height = 236.0, 88.0
    left, right, top, bottom = 36.0, 232.0, 6.0, 68.0
    span = high - low or 1
    y = lambda value: top + (high - value) * (bottom - top) / span
    rules = []
    for kind, value, label in levels:
        rule_y = y(value)
        rules.append(f'<line class="desk-ytd-rule desk-ytd-rule--{kind}" x1="{left:.0f}" y1="{rule_y:.1f}" x2="{right:.0f}" y2="{rule_y:.1f}"><title>{html.escape(label)}</title></line>')
    axes = []
    for index in range(3):
        price = high - index * span / 2
        tick_y = y(price)
        digits = 2 if price < 10 else 1 if price < 100 else 0
        axes.append(
            f'<line class="desk-ytd-grid" x1="{left:.0f}" y1="{tick_y:.1f}" x2="{right:.0f}" y2="{tick_y:.1f}"/>'
            f'<text class="desk-ytd-axis-label" x="32" y="{tick_y + 3:.1f}" text-anchor="end">${price:.{digits}f}</text>'
        )
    for index in sorted({0, len(dates) // 2, len(dates) - 1}):
        tick_x = left + index * (right - left) / max(len(dates) - 1, 1)
        parsed = dt.date.fromisoformat(dates[index])
        label = parsed.strftime("%b %-d") + (f" ’{parsed.strftime('%y')}" if index in (0, len(dates) - 1) else "")
        anchor = "start" if index == 0 else "end" if index == len(dates) - 1 else "middle"
        axes.append(f'<text class="desk-ytd-axis-label" x="{tick_x:.1f}" y="84" text-anchor="{anchor}">{label}</text>')
    change = (closes[-1] / base - 1) * 100
    direction = "up" if change >= 0 else "down"
    points = plot_polyline(closes, left, right, top, bottom, low, high)
    attrs = (
        f'data-desk-ytd-chart="{symbol}" data-desk-ytd-entry="{entry if entry is not None else ""}" '
        f'data-desk-ytd-kill="{kill if kill is not None else ""}"'
    )
    return (
        f'<figure class="desk-ytd desk-ytd--{direction}" {attrs}>'
        f'<svg viewBox="0 0 236 88" role="img" tabindex="0" aria-label="{symbol} trailing one-year return {change:+.1f} percent, with price and date axes. Hover or use arrow keys for metrics.">'
        f'{"".join(axes)}{"".join(rules)}<polyline class="desk-ytd-line" points="{points}"/>'
        f'<line class="desk-ytd-hover-line" x1="0" x2="0" y1="{top:.0f}" y2="{bottom:.0f}" hidden/><circle class="desk-ytd-hover-dot" cx="0" cy="0" r="3" hidden/></svg>'
        f'<div class="desk-ytd-tooltip" data-desk-ytd-tooltip role="status" aria-live="polite" hidden></div>'
        f'<figcaption>{change:+.1f}% · trailing 1Y</figcaption></figure>'
    )


def vol(values: list[float]) -> float:
    returns = [b / a - 1 for a, b in zip(values, values[1:]) if a > 0]
    return statistics.stdev(returns) * math.sqrt(252) * 100 if len(returns) > 2 else 0.0


def detail_chart(symbol: str, market: dict, levels: dict, position: dict | None = None, level_labels: dict | None = None) -> str:
    if not market.get("feed"):
        return f'<div class="desk-no-feed desk-no-feed--chart" data-desk-one-year-chart="{symbol}">— <span>No feed · one-year chart unavailable</span></div>'
    pairs = [(dt.date.fromisoformat(date), float(close)) for date, close in zip(market["dates"], market["closes"])]
    cutoff = pairs[-1][0] - dt.timedelta(days=365)
    pairs = [(date, close) for date, close in pairs if date >= cutoff]
    dates = [date.isoformat() for date, _close in pairs]
    values = [close for _date, close in pairs]
    scenarios = {k: float(levels[k]) for k in ("bear", "base", "bull")}
    labels = level_labels or {case: case.title() for case in scenarios}
    domain = values + list(scenarios.values())
    low, high = min(domain), max(domain)
    margin = max((high - low) * .04, 1)
    low, high = max(0, low - margin), high + margin
    width, height = 520.0, 210.0
    left, right, top, bottom = 44.0, 510.0, 10.0, 182.0
    span = high - low or 1
    y = lambda value: top + (high - value) * (bottom - top) / span
    rules = "".join(
        f'<line class="desk-detail-rule desk-detail-rule--{case}" x1="{left:.0f}" y1="{y(price):.1f}" x2="{right:.0f}" y2="{y(price):.1f}"><title>{html.escape(labels[case])} {money(price)}</title></line>'
        for case, price in scenarios.items()
    )
    band_y = min(y(scenarios["bear"]), y(scenarios["bull"]))
    band_h = abs(y(scenarios["bear"]) - y(scenarios["bull"]))
    points = plot_polyline(values, left, right, top, bottom, low, high)
    y_ticks = []
    for index in range(4):
        price = high - index * span / 3
        tick_y = y(price)
        digits = 2 if price < 10 else 1 if price < 100 else 0
        y_ticks.append(
            f'<line class="desk-detail-grid" x1="{left:.0f}" y1="{tick_y:.1f}" x2="{right:.0f}" y2="{tick_y:.1f}"/>'
            f'<text class="desk-detail-axis-label" x="38" y="{tick_y + 3:.1f}" text-anchor="end">${price:.{digits}f}</text>'
        )
    x_ticks = []
    for index in sorted({0, len(dates) // 2, len(dates) - 1}):
        tick_x = left + index * (right - left) / max(len(dates) - 1, 1)
        parsed = dt.date.fromisoformat(dates[index])
        label = parsed.strftime("%b %-d") + (f" ’{parsed.strftime('%y')}" if index in (0, len(dates) - 1) else "")
        anchor = "start" if index == 0 else "end" if index == len(dates) - 1 else "middle"
        x_ticks.append(f'<text class="desk-detail-axis-label" x="{tick_x:.1f}" y="202" text-anchor="{anchor}">{label}</text>')
    kill = float(position["kill"]) if position and position.get("kill") else None
    attrs = (
        f'data-desk-one-year-chart="{symbol}" data-desk-chart-dates="{",".join(dates)}" '
        f'data-desk-chart-closes="{",".join(f"{value:.4f}" for value in values)}" '
        f'data-desk-chart-kill="{kill if kill is not None else ""}"'
    )
    return (
        f'<figure class="desk-detail-chart" {attrs}><svg viewBox="0 0 520 210" role="img" tabindex="0" aria-label="{symbol} one-year price history with price and date axes. Hover or use arrow keys for daily metrics.">'
        f'<rect class="desk-detail-band" x="{left:.0f}" y="{band_y:.1f}" width="{right-left:.0f}" height="{band_h:.1f}"/>{"".join(y_ticks)}{rules}'
        f'<polyline class="desk-detail-price" points="{points}"/>{"".join(x_ticks)}<line class="desk-chart-hover-line" x1="0" x2="0" y1="{top:.0f}" y2="{bottom:.0f}" hidden/>'
        f'<circle class="desk-chart-hover-dot" cx="0" cy="0" r="4" hidden/></svg>'
        f'<div class="desk-chart-tooltip" data-desk-chart-tooltip role="status" aria-live="polite" hidden></div>'
        f'<figcaption>1 year · Beta {market["beta"]:.2f} · Annualized vol {vol(values):.0f}% · Hover for metrics</figcaption></figure>'
    )


def feed_cell(label: str, value: str, cls: str = "") -> str:
    return f'<td class="{cls}" data-label="{label}">{value}</td>'


def position_risk_lines(position: dict) -> str:
    capital = float(position["capital_percent"])
    premium = float(position["premium_at_risk_percent"])
    theta = float(position["theta_percent_per_day"])
    parts = [f"capital {capital:.1f}%"]
    if premium > 0:
        parts.extend((f"premium {premium:.1f}%", f"θ/day {theta:+.2f}%"))
    else:
        parts.append("stock only")
    flag = ""
    if position.get("unstable_delta"):
        flag = f'<span class="desk-position-risk-flag">⚠ {int(position["min_dte"])}-DTE delta</span>'
    metrics = "".join(f"<span>{html.escape(part)}</span>" for part in parts)
    return f'<span class="desk-position-risk-meta">{metrics}</span>{flag}'


def entry_level_display(valuation: dict) -> tuple[str, dict[str, str], str]:
    default_labels = {case: case.title() for case in ("bear", "base", "bull")}
    display = valuation.get("entry_level_display")
    if display is None:
        return "Intrinsic entry levels", default_labels, "base case"
    if not isinstance(display, dict):
        raise ValueError("entry_level_display must be an object")
    heading = display.get("heading")
    labels = display.get("labels")
    comparison = display.get("base_comparison")
    if not isinstance(heading, str) or not heading.strip():
        raise ValueError("entry_level_display needs a heading")
    if not isinstance(labels, dict) or set(labels) != set(default_labels) or not all(isinstance(value, str) and value.strip() for value in labels.values()):
        raise ValueError("entry_level_display labels must name bear/base/bull")
    if not isinstance(comparison, str) or not comparison.strip():
        raise ValueError("entry_level_display needs base_comparison")
    return heading, labels, comparison


def valuation_detail(symbol: str, market: dict, valuation: dict, position: dict | None) -> str:
    levels = valuation["entry_levels"]
    heading, level_labels, comparison = entry_level_display(valuation)
    metrics = "".join(f'<div><span>{html.escape(item["label"])}</span><b>{html.escape(item["value"])}</b></div>' for item in valuation["valuation_metrics"])
    last = market.get("last")
    distance = ((last / float(levels["base"]) - 1) * 100) if isinstance(last, (int, float)) else None
    sector = position["sector"] if position else "See full thesis"
    tiles = "".join(f'<div class="desk-entry-tile desk-entry-tile--{case}"><span>{html.escape(level_labels[case])}</span><b>{money(float(levels[case]))}</b></div>' for case in ("bear", "base", "bull"))
    distance_line = f'Trading {distance:+.0f}% versus {comparison}' if distance is not None else "Market price feed unavailable"
    return f'''<div class="desk-fold-grid">
<div>{detail_chart(symbol, market, levels, position, level_labels)}</div>
<div class="desk-valuation" data-desk-valuation><h4>Valuation</h4>{metrics}<div><span>Last</span><b>{money(last)}</b></div><div><span>Sector</span><b>{html.escape(sector)}</b></div></div>
<div class="desk-entry" data-desk-entry-tiles><h4>{html.escape(heading)}</h4><div class="desk-entry-tiles">{tiles}</div><span class="desk-confidence">{html.escape(valuation["confidence"])} confidence</span><p>{html.escape(distance_line)}</p></div>
</div>'''


def no_feed_market_cells() -> tuple[str, str, str, str]:
    cell = '<div class="desk-no-feed">— <span>No feed</span></div>'
    return cell, cell, cell, cell


def spread_cell(market: dict) -> str:
    spread = market.get("spread")
    return f"{float(spread):+.2f}" if spread is not None and math.isfinite(float(spread)) else no_feed_market_cells()[2]


def thesis_button(symbol: str) -> str:
    return f'<button class="desk-thesis-cell-button" type="button" data-thesis-open="{symbol}" aria-haspopup="dialog" aria-controls="desk-thesis-dialog">Full thesis</button>'


def chart_button(symbol: str) -> str:
    return f'<button class="desk-chart-cell-button" type="button" data-hypothesis-chart-open="{symbol}" aria-haspopup="dialog" aria-controls="hypothesis-chart-dialog" aria-label="Open {symbol} setup chart" title="Open {symbol} setup chart"><span aria-hidden="true">📊</span></button>'


def position_rows(positions: list[dict], metadata: dict, markets: dict, valuations: dict, as_of: dt.date) -> str:
    rows = []
    for position in sorted(positions, key=lambda p: (-float(p["exposure_percent"]), p["symbol"])):
        symbol = position["symbol"]
        market = markets[symbol]
        meta = metadata[symbol]
        catalyst = dt.date.fromisoformat(meta["catalyst"])
        days = max(0, (catalyst - as_of).days)
        kill = position.get("kill")
        if market.get("feed"):
            edge = "up" if market["day"] > .05 else "down" if market["day"] < -.05 else "flat"
            edge_word = {"up":"Up", "down":"Down", "flat":"Flat"}[edge]
            last, day, spread, ytd = money(market["last"]), pct(market["day"]), spread_cell(market), ytd_chart(symbol, market, None, float(kill) if kill else None)
        else:
            edge = "no-feed"
            edge_word = "No feed"
            last, day, spread, ytd = no_feed_market_cells()
        detail_id = f"desk-detail-{symbol.lower()}"
        flair = position.get("flair")
        flair_html = f'<span class="desk-position-flair desk-position-flair--{flair}">{flair.title()}</span>' if flair else ""
        exposure = float(position["exposure_percent"])
        main = f'''<tr class="desk-main-row" data-desk-kind="position" data-desk-symbol="{symbol}" data-exposure-percent="{exposure:.1f}" data-catalyst-date="{meta['catalyst']}" data-edge="{edge}" data-feed-state="{'live' if market.get('feed') else 'no-feed'}" data-feed-source="{html.escape(str(market.get('source', 'none')))}">
<td data-label="Position"><button class="desk-row-toggle" type="button" aria-expanded="false" aria-controls="{detail_id}"><span class="desk-edge-word">{edge_word}</span><span class="desk-position-title"><b>{symbol}</b>{flair_html}</span><small>{html.escape(position['instrument'])}</small><span class="desk-position-exposure">{exposure:.1f}% Δ$ exposure</span>{position_risk_lines(position)}</button></td>
{feed_cell('Last', last, 'desk-num')}{feed_cell('Day', day, 'desk-num' + (' desk-sign--'+edge if market.get('feed') else ''))}{feed_cell('Thesis', thesis_button(symbol))}{feed_cell('Chart', chart_button(symbol), 'desk-chart-cell')}{feed_cell('Beta', f"{market['beta']:.2f}", 'desk-num')}{feed_cell('Spread Z', spread, 'desk-num')}{feed_cell('1Y · levels', ytd)}{feed_cell('Next catalyst', f'<span class="desk-catalyst"><b>{html.escape(meta["catalyst-name"])}</b><small>{catalyst.strftime("%b %-d")}</small></span>')}{feed_cell('In', f'{days}d', 'desk-num')}
</tr>'''
        detail = f'<tr class="desk-detail-row" id="{detail_id}" hidden><td colspan="10">{valuation_detail(symbol, market, valuations[symbol], position)}<p class="desk-row-thesis">{html.escape(position["thesis"])}</p></td></tr>'
        rows.append(main + detail)
    return "\n".join(rows)


def hypothesis_rows(symbols: list[str], metadata: dict, markets: dict, valuations: dict, as_of: dt.date) -> str:
    rows = []
    for symbol in sorted(symbols, key=lambda s: metadata[s]["catalyst"]):
        market = markets[symbol]
        meta = metadata[symbol]
        catalyst = dt.date.fromisoformat(meta["catalyst"])
        days = max(0, (catalyst - as_of).days)
        stance = meta["stance"]
        edge = "no-feed" if not market.get("feed") else "soon" if days <= 7 else "up" if market["day"] >= 0 else "down"
        edge_word = "No feed" if edge == "no-feed" else "Soon" if edge == "soon" else "Up" if edge == "up" else "Down"
        detail_id = f"desk-detail-{symbol.lower()}"
        if market.get("feed"):
            last, day, spread, ytd = money(market["last"]), pct(market["day"]), spread_cell(market), ytd_chart(symbol, market)
        else:
            last, day, spread, ytd = no_feed_market_cells()
        main = f'''<tr class="desk-main-row" data-desk-kind="hypothesis" data-desk-symbol="{symbol}" data-catalyst-date="{meta['catalyst']}" data-edge="{edge}" data-feed-state="{'live' if market.get('feed') else 'no-feed'}" data-feed-source="{html.escape(str(market.get('source', 'none')))}">
<td data-label="Thesis"><button class="desk-row-toggle" type="button" aria-expanded="false" aria-controls="{detail_id}"><span class="desk-edge-word">{edge_word}</span><b>{symbol}</b><span class="desk-stance desk-stance--{stance}">{stance.replace('-', ' ')}</span></button></td>
{feed_cell('Last', last, 'desk-num')}{feed_cell('Day', day, 'desk-num')}{feed_cell('Thesis', thesis_button(symbol))}{feed_cell('Chart', chart_button(symbol), 'desk-chart-cell')}{feed_cell('Beta', f"{market['beta']:.2f}", 'desk-num')}{feed_cell('Spread Z', spread, 'desk-num')}{feed_cell('1Y', ytd)}{feed_cell('Next catalyst', f'<span class="desk-catalyst {"desk-catalyst--soon" if days <= 7 else ""}"><b>{html.escape(meta["catalyst-name"])}</b><small>{catalyst.strftime("%b %-d")}</small></span>')}{feed_cell('In', f'{days}d', 'desk-num')}
</tr>'''
        detail = f'<tr class="desk-detail-row" id="{detail_id}" hidden><td colspan="10">{valuation_detail(symbol, market, valuations[symbol], None)}</td></tr>'
        rows.append(main + detail)
    return "\n".join(rows)


def risk_strip(summary: dict, sleeves: dict) -> str:
    cash_percent = float(summary["cash_percent"])
    cash_label = "Margin debit" if cash_percent < 0 else "Cash liquidity"
    sleeve_html = "".join(
        f'<span><b>{html.escape(name.title())}</b> · Δ$ {float(values["exposure_percent"]):.1f}% · capital {float(values["capital_percent"]):.1f}% · premium {float(values["premium_at_risk_percent"]):.1f}%</span>'
        for name, values in sorted(sleeves.items())
    )
    return (
        '<div class="desk-risk-strip" aria-label="Portfolio risk summary">'
        f'<span>Gross Δ$ <b>{float(summary["gross_delta_leverage"]):.1f}×</b></span>'
        f'<span>Net Δ$ <b>{float(summary["net_delta_exposure_percent"]):.1f}%</b></span>'
        f'<span>Premium risk <b>{float(summary["premium_at_risk_percent"]):.1f}%</b></span>'
        f'<span>Θ/day <b>{float(summary["theta_percent_per_day"]):+.2f}%</b></span>'
        f'<span>{cash_label} <b>{cash_percent:.1f}%</b></span>'
        f'<small>{html.escape(str(summary["quantity_basis"]))}</small>'
        '</div>'
        f'<div class="desk-sleeve-strip" aria-label="Sleeve risk summary">{sleeve_html}</div>'
    )


def table(title: str, subtitle: str, body: str, hypotheses: bool = False, risk_summary: dict | None = None, sleeves: dict | None = None) -> str:
    if hypotheses:
        heads = '<th>Thesis</th><th>Last</th><th>Day</th><th>Thesis</th><th>Chart</th><th>Beta</th><th>Spread Z</th><th>1Y</th><th>Next catalyst</th><th>In</th>'
    else:
        heads = '<th>Position</th><th>Last</th><th>Day</th><th>Thesis</th><th>Chart</th><th>Beta</th><th>Spread Z</th><th>1Y · levels</th><th>Next catalyst</th><th>In</th>'
    extra = risk_strip(risk_summary, sleeves or {}) if risk_summary else ""
    return f'<div class="desk-table-head"><h2>{title}</h2><span>{subtitle}</span></div>{extra}<div class="desk-table-scroll"><table class="desk-blotter-table">{COLGROUP}<thead><tr>{heads}</tr></thead><tbody>{body}</tbody></table></div>'


def modals() -> str:
    config = json.dumps({"url": f"/trading/scan-charts.json?v={digest(SCAN)}", "vwap_url": f"/trading/vwap-charts.json?v={digest(VWAP)}"}, separators=(",", ":"))
    return f'''<dialog class="hyp-chart-dialog" id="hypothesis-chart-dialog" aria-labelledby="hypothesis-chart-dialog-title"><div class="hyp-chart-dialog-frame" data-hypothesis-chart-detail><header class="hyp-chart-dialog-head"><div><span>VWAP setup data</span><h2 id="hypothesis-chart-dialog-title"><span data-hypothesis-chart-title>Setup charts</span></h2></div><button type="button" class="hyp-chart-dialog-close" data-hypothesis-chart-close aria-label="Close chart dialog">×</button></header><div class="hyp-chart-dialog-body"><div class="scan-setup-chart" data-hypothesis-chart-shell></div></div></div></dialog>
<script type="application/json" id="scan-chart-config">{config}</script>
<dialog class="desk-thesis-dialog" id="desk-thesis-dialog" data-thesis-source="/trading/hypothesis-source.txt?v={digest(HYPOTHESES)}" aria-labelledby="desk-thesis-title"><div class="desk-thesis-frame"><header><h2 id="desk-thesis-title">Full thesis</h2><button type="button" data-thesis-close aria-label="Close thesis dialog">×</button></header><div data-thesis-summary></div><div data-thesis-body><p>Loading thesis…</p></div></div></dialog>'''


def sync_shell_assets(stamp: str | None = None, status_metrics: str | None = None) -> None:
    emit_content_assets()
    css_ref = content_asset_ref(DESK_CSS)
    js_ref = content_asset_ref(DESK_JS)
    modal_ref = f'/js/hypothesis-chart-modal.b42a9700.js?v={digest(CHART_MODAL_JS)}'
    gpt = load(ROOT / "trading" / "risk-journal.json")["entries"][0]
    grok = load(ROOT / "trading" / "grok-risk.json")["entries"][0]
    fable_payload = load(ROOT / "trading" / "fable-risk.json")
    fable_rank = {"pre-market": 0, "intraday": 1, "post-close": 2}
    fable = max(fable_payload["entries"] + fable_payload.get("model_entries", []),
                key=lambda e: ((e.get("date") or e["as_of_date"]), fable_rank.get(e.get("session", "pre-market"), 1)))
    models = {
        "gpt": ("GPT", "gpt-risk", float(gpt["risk_appetite"]), gpt["stance"]),
        "grok": ("Grok", "grok-risk", float(grok["risk_appetite"]), grok["stance"]),
        "fable": ("Fable", "fable-risk", float(fable.get("risk_appetite", fable.get("rating"))), fable.get("stance", fable.get("verdict"))),
    }
    model_chips = {}
    for key, (label, route, value, stance) in models.items():
        state = "on" if value > 5 else "off" if value < 5 else "neutral"
        score = f"{value:g}"
        model_chips[key] = (
            f'<a class="chip chip-{key} chip-{state}" href="/trading/{route}/" '
            f'title="{html.escape(label)} risk appetite — {html.escape(str(stance))} · {score}/10">{html.escape(label)} {score}</a>'
        )
    if status_metrics:
        for retired in ("gemini", "meta"):
            status_metrics = re.sub(
                rf'<a class="chip chip-{retired} [^"]+" href="/trading/{retired}-risk/".*?</a>',
                "",
                status_metrics,
                count=1,
            )
    shell_paths = sorted((ROOT / "trading").glob("**/index.html")) + [PIPELINE]
    for path in shell_paths:
        source = path.read_text()
        source = re.sub(r'/trading/desk(?:\.[a-f0-9]{12})?\.css(?:\?v=[a-f0-9]+)?', css_ref, source)
        source = re.sub(r'/trading/desk(?:\.[a-f0-9]{12})?\.js(?:\?v=[a-f0-9]+)?', js_ref, source)
        source = re.sub(r'<a href="/trading/hypotheses/"(?: aria-current="page")?>Hypotheses</a>', '', source)
        source = re.sub(r'<a href="/trading/watchlist/"(?: aria-current="page")?>Watchlist</a>', '', source)
        for retired in ("gemini", "meta"):
            source = re.sub(
                rf'<a class="chip chip-{retired} [^"]+" href="/trading/{retired}-risk/".*?</a>',
                "",
                source,
                count=1,
            )
        for risk_route, label in (("grok-risk", "Grok Risk"), ("gpt-risk", "GPT Risk"), ("fable-risk", "Fable Risk")):
            source = re.sub(rf'<a href="/trading/{risk_route}/"(?: aria-current="page")?>{label}</a>', '', source)
        source = source.replace('/trading/watchlist/?chart=', '/trading/vwap-setups/?chart=')
        source = source.replace('Market · YTD', 'Market · trailing 1Y')
        if '<nav class="subnav"' in source:
            source = normalize_trading_subnav(source, path)
        if '<div class="status-metrics">' in source:
            source = replace_sector_status_pills(source)
        for key, chip in model_chips.items():
            source = re.sub(
                rf'<a class="chip chip-{key} [^"]+" href="/trading/(?:gpt|grok|gemini|meta|fable)-risk/".*?</a>',
                chip,
                source,
                count=1,
            )
        source = re.sub(r'<span class="dot"></span>(?=[A-Za-z]+ [\d.]+</a>)', '', source)
        if stamp:
            source = re.sub(r'(<span class="stamp">).*?(</span>)', rf'\1{stamp}\2', source, count=1)
            source = re.sub(r'(<span class="trading-stamp">).*?(</span>)', rf'\1{stamp}\2', source, count=1)
        if status_metrics and '<div class="status-metrics">' in source:
            source, count = re.subn(r'<div class="status-metrics">.*?</div>', status_metrics, source, count=1, flags=re.S)
            if count != 1:
                raise ValueError(f"Status metrics region could not be replaced in {path.relative_to(ROOT)}")
        # The shared status block comes from the Desk page and may still carry its
        # pre-build fallback chips, so normalize model scores after inserting it.
        for key, chip in model_chips.items():
            source = re.sub(
                rf'<a class="chip chip-{key} [^"]+" href="/trading/(?:gpt|grok|gemini|meta|fable)-risk/".*?</a>',
                chip,
                source,
                count=1,
            )
        path.write_text(source)


def render(mode: str, quote_path: Path | None) -> str:
    page = PAGE.read_text()
    hypothesis_source = HYPOTHESES.read_text()
    metadata = article_metadata(hypothesis_source)
    positions_payload = load(POSITIONS)
    if positions_payload.get("schema_version") != 3:
        raise ValueError("Desk positions must use schema_version 3")
    positions = positions_payload["positions"]
    risk_summary = positions_payload.get("risk_summary")
    if not isinstance(risk_summary, dict):
        raise ValueError("Desk positions need risk_summary")
    sleeves = positions_payload.get("sleeves")
    if not isinstance(sleeves, dict) or not sleeves:
        raise ValueError("Desk positions need sleeve rollups")
    valuation = load(VALUATIONS)["rows"]
    charts_payload = load(CHARTS)
    charts = charts_payload["charts"]
    if set(metadata) != set(valuation) or set(metadata) != set(charts):
        raise ValueError("Desk articles, valuations, and chart symbols must match exactly")
    scan = load(SCAN)["charts"]
    quotes, quote_stamp, live_status = quotes_from(quote_path)
    symbols = sorted(metadata)
    quote_date = quote_stamp.astimezone(CT).date() if quote_stamp else None
    chart_date = dt.date.fromisoformat(charts_payload["as_of"])
    if mode == "close" and quote_date and quote_date != chart_date:
        raise ValueError(
            f"Close fallback quotes must match chart date {chart_date.isoformat()}: {quote_date.isoformat()}"
        )
    markets = {
        symbol: row_market(symbol, charts[symbol], scan.get(symbol), quotes.get(symbol), quote_date)
        for symbol in symbols
    }
    as_of = quote_date if mode == "morning" and quote_date else chart_date
    position_symbols = {p["symbol"] for p in positions}
    tracked = [s for s in symbols if s not in position_symbols]
    for symbol in tracked:
        if metadata[symbol]["stance"] == "open-position":
            metadata[symbol]["stance"] = "constructive"
    pos_body = position_rows(positions, metadata, markets, valuation, as_of)
    hyp_body = hypothesis_rows(tracked, metadata, markets, valuation, as_of)
    if not tracked:
        hyp_body = '<tr class="desk-empty-row"><td colspan="10">New hunt starts empty. Add only researched setups worth tracking.</td></tr>'
    main = f'''<section class="desk-main" data-desk-source-articles="{len(metadata)}">
{START_POS}
{table('Positions', f'{len(positions)} open · sorted by Δ$ exposure', pos_body, risk_summary=risk_summary, sleeves=sleeves)}
{END_POS}
{START_HYP}
{table('Tracked hypotheses', f'{len(tracked)} thesis-only names · sorted by catalyst', hyp_body, True)}
{END_HYP}
</section>'''
    page, count = re.subn(r'<section class="desk-main"[^>]*>.*?</section>', main, page, count=1, flags=re.S)
    if count != 1:
        raise ValueError("Desk main section not found")
    page = re.sub(r'\s*<dialog class="hyp-chart-dialog".*?</dialog>\s*<script type="application/json" id="scan-chart-config">.*?</script>\s*<dialog class="desk-thesis-dialog".*?</dialog>', '', page, flags=re.S)
    page = re.sub(r'\s*<script defer src="/js/hypothesis-chart-modal\.[a-f0-9]{8}\.js(?:\?v=[a-f0-9]+)?"></script>', '', page)
    modal_ref = f'/js/hypothesis-chart-modal.b42a9700.js?v={digest(CHART_MODAL_JS)}'
    page = page.replace('</body>', f'{modals()}\n<script defer src="{modal_ref}"></script>\n</body>', 1)
    page = render_status_metrics(page, len(positions), live_status or close_status_market())
    if mode == "morning" and quote_stamp:
        stamp = live_stamp(quote_stamp)
    else:
        stamp = f"Snapshot · {as_of.strftime('%B %-d, %Y')}"
    page = re.sub(r'(<span class="stamp">).*?(</span>)', rf'\1{stamp}\2', page, count=1)
    page = re.sub(
        r'/trading/desk(?:\.[a-f0-9]{12})?\.css(?:\?v=[a-f0-9]+)?',
        content_asset_ref(DESK_CSS),
        page,
    )
    page = re.sub(
        r'/trading/desk(?:\.[a-f0-9]{12})?\.js(?:\?v=[a-f0-9]+)?',
        content_asset_ref(DESK_JS),
        page,
    )
    return page


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify checked-in artifacts without network access")
    parser.add_argument("--mode", choices=("close", "morning"), default="close")
    parser.add_argument("--quotes", type=Path, help="validated explicit quote JSON; close defaults to trading/desk-close-quotes.json")
    args = parser.parse_args()
    if args.mode == "morning" and args.quotes is None:
        parser.error("--mode morning requires --quotes")
    quote_path = resolve_quote_path(args.mode, args.quotes)
    rendered = render(args.mode, quote_path)
    if args.check:
        if rendered != PAGE.read_text():
            print("[trading-desk] stale: run python3 scripts/build-trading-desk.py")
            return 1
        positions = len(load(POSITIONS)["positions"])
        total = len(article_metadata(HYPOTHESES.read_text()))
        print(f"[trading-desk] current and network-free: {positions} positions + {total - positions} tracked hypotheses")
        return 0
    PAGE.write_text(rendered)
    stamp_match = re.search(r'<span class="stamp">(.*?)</span>', rendered)
    status_match = re.search(r'<div class="status-metrics">.*?</div>', rendered, flags=re.S)
    sync_shell_assets(stamp_match.group(1) if stamp_match else None, status_match.group(0) if status_match else None)
    positions = len(load(POSITIONS)["positions"])
    total = len(article_metadata(HYPOTHESES.read_text()))
    print(f"[trading-desk] built {args.mode}: {positions} positions + {total - positions} tracked hypotheses")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
