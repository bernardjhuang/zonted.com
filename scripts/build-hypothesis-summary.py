#!/usr/bin/env python3
"""Build the hypotheses summary table from the public hypothesis registry.

The routed hypotheses page owns the ticker list. Valuation inputs are explicit and
frozen until the thesis/model changes; two-year prices refresh from Yahoo on each
build. A new hypothesis cannot deploy without a matching valuation row and chart.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import math
import pathlib
import re
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "trading" / "hypotheses" / "index.html"
VALUATIONS = ROOT / "trading" / "hypothesis-valuations.json"
CHARTS = ROOT / "trading" / "hypothesis-charts.json"
CSS_HREF = "/trading/hypothesis-summary.css?v=1"
START = "<!-- AUTO:HYPOTHESIS_SUMMARY:START -->"
END = "<!-- AUTO:HYPOTHESIS_SUMMARY:END -->"


def extract_hypothesis_symbols(page: str) -> list[str]:
    symbols = [symbol.upper() for symbol in re.findall(
        r'<article class="hypothesis-detail" id="hypothesis-([a-z0-9.-]+)-setup"',
        page,
    )]
    if not symbols or len(symbols) != len(set(symbols)):
        raise ValueError("Hypothesis symbols must be present and unique")
    return symbols


def load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def validate_config(symbols: list[str], config: dict) -> None:
    if config.get("schema_version") != 1:
        raise ValueError("hypothesis-valuations.json must use schema_version 1")
    rows = config.get("rows") or {}
    if list(rows) != symbols:
        missing = [symbol for symbol in symbols if symbol not in rows]
        extra = [symbol for symbol in rows if symbol not in symbols]
        raise ValueError(f"Valuation rows must match hypothesis order; missing={missing}, extra={extra}")
    for symbol, row in rows.items():
        metrics = row.get("valuation_metrics") or []
        levels = row.get("entry_levels") or {}
        if len(metrics) < 2 or any(set(metric) != {"label", "value"} for metric in metrics):
            raise ValueError(f"{symbol} needs at least two label/value valuation metrics")
        if set(levels) != {"bear", "base", "bull"} or any(
            isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0
            for value in levels.values()
        ):
            raise ValueError(f"{symbol} needs positive finite bear/base/bull entry levels")
        if not row.get("method") or row.get("confidence") not in {"low", "medium", "high"}:
            raise ValueError(f"{symbol} needs a method and low/medium/high confidence")


def fetch_chart(symbol: str) -> dict:
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + symbol + "?" + urlencode({
        "range": "2y",
        "interval": "1d",
        "events": "div,splits",
        "includeAdjustedClose": "true",
    })
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Zonted/1.0)"})
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)
    result = (payload.get("chart") or {}).get("result") or []
    if not result:
        raise ValueError(f"Yahoo returned no chart for {symbol}")
    result = result[0]
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators") or {}
    adjusted = ((indicators.get("adjclose") or [{}])[0].get("adjclose") or [])
    closes = adjusted or ((indicators.get("quote") or [{}])[0].get("close") or [])
    points: list[tuple[str, float]] = []
    for timestamp, close in zip(timestamps, closes):
        if close is None:
            continue
        value = float(close)
        if not math.isfinite(value) or value <= 0:
            continue
        date = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).date().isoformat()
        points.append((date, round(value, 4)))
    if len(points) < 80:
        raise ValueError(f"{symbol} returned only {len(points)} valid two-year points")

    # One close per ISO week keeps the checked-in payload and inline SVG compact.
    weekly: dict[tuple[int, int], tuple[str, float]] = {}
    for date, close in points:
        parsed = dt.date.fromisoformat(date)
        iso = parsed.isocalendar()
        weekly[(iso.year, iso.week)] = (date, close)
    sampled = list(weekly.values())
    if sampled[0] != points[0]:
        sampled.insert(0, points[0])
    if sampled[-1] != points[-1]:
        sampled.append(points[-1])
    return {
        "dates": [date for date, _ in sampled],
        "close": [close for _, close in sampled],
    }


def refresh_charts(symbols: list[str], existing: dict) -> dict:
    previous = existing.get("charts") or {}
    charts: dict[str, dict] = {}
    warnings: list[str] = []
    for symbol in symbols:
        try:
            charts[symbol] = fetch_chart(symbol)
        except Exception as error:
            cached = previous.get(symbol)
            if not cached or len(cached.get("dates") or []) < 80:
                raise RuntimeError(f"Could not refresh {symbol} and no valid cached chart exists: {error}") from error
            charts[symbol] = cached
            warnings.append(f"{symbol}: {type(error).__name__}: {error}")
    if warnings:
        print("[hypothesis-summary] chart refresh warnings: " + " | ".join(warnings), file=sys.stderr)
    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "as_of": max(chart["dates"][-1] for chart in charts.values()),
        "charts": charts,
    }


def money(value: float) -> str:
    return f"${value:,.0f}" if float(value).is_integer() else f"${value:,.2f}"


def short_date(value: str) -> str:
    return dt.date.fromisoformat(value).strftime("%b %-d, %Y")


def sparkline(symbol: str, chart: dict) -> str:
    dates = chart["dates"]
    values = [float(value) for value in chart["close"]]
    width, height, pad = 280.0, 76.0, 4.0
    low, high = min(values), max(values)
    spread = high - low or 1.0

    def x(index: int) -> float:
        return pad + index * (width - 2 * pad) / max(len(values) - 1, 1)

    def y(value: float) -> float:
        return pad + (high - value) * (height - 2 * pad) / spread

    points = " ".join(f"{x(index):.1f},{y(value):.1f}" for index, value in enumerate(values))
    change = (values[-1] / values[0] - 1.0) * 100.0
    direction = "is-down" if change < 0 else "is-up"
    change_class = "down" if change < 0 else "up"
    aria = html.escape(
        f"{symbol} adjusted close from {short_date(dates[0])} to {short_date(dates[-1])}; "
        f"{values[0]:.2f} to {values[-1]:.2f}, {change:+.1f} percent",
        quote=True,
    )
    grids = "".join(
        f'<line class="grid" x1="{pad}" y1="{level:.1f}" x2="{width - pad}" y2="{level:.1f}"/>'
        for level in (pad, height / 2, height - pad)
    )
    return f'''<figure class="hyp-summary-chart {direction}">
<svg viewBox="0 0 280 76" preserveAspectRatio="none" role="img" aria-label="{aria}">{grids}<polyline class="line" points="{points}"/><circle class="dot" cx="{x(len(values) - 1):.1f}" cy="{y(values[-1]):.1f}" r="3"/></svg>
<figcaption><span>{html.escape(short_date(dates[0]))}</span><b>${values[-1]:,.2f} <span class="{change_class}">{change:+.1f}%</span></b><span>{html.escape(short_date(dates[-1]))}</span></figcaption>
</figure>'''


def render_summary(symbols: list[str], config: dict, charts: dict) -> str:
    rows = []
    for symbol in symbols:
        record = config["rows"][symbol]
        metrics = "".join(
            f'<span><b>{html.escape(metric["label"])}</b>{html.escape(metric["value"])}</span>'
            for metric in record["valuation_metrics"]
        )
        levels = record["entry_levels"]
        rows.append(f'''<tr data-hypothesis-summary-row="{symbol}">
<td class="hyp-summary-symbol" data-label="Ticker"><a href="#hypothesis-{symbol.lower()}-setup">{symbol}</a><span title="{html.escape(record["method"], quote=True)}">{html.escape(record["confidence"])} confidence</span></td>
<td class="hyp-summary-chart-cell" data-label="2-year stock chart">{sparkline(symbol, charts["charts"][symbol])}</td>
<td class="hyp-summary-metrics" data-label="Valuation">{metrics}</td>
<td class="hyp-summary-level hyp-summary-level--bear" data-label="Bear">{money(levels["bear"])}</td>
<td class="hyp-summary-level hyp-summary-level--base" data-label="Base">{money(levels["base"])}</td>
<td class="hyp-summary-level hyp-summary-level--bull" data-label="Bull">{money(levels["bull"])}</td>
</tr>''')
    as_of = short_date(charts["as_of"])
    valuation_as_of = short_date(config["as_of"])
    return f'''{START}
<section class="hyp-summary" aria-labelledby="hyp-summary-heading">
<div class="hyp-summary-head"><div><h2 id="hyp-summary-heading">Hypothesis valuation scoreboard</h2><p>Two-year price context, current valuation snapshot, and bear / base / bull intrinsic entry levels.</p></div><span class="hyp-summary-asof">Prices through {as_of}</span></div>
<div class="hyp-summary-wrap"><table class="hyp-summary-table">
<thead><tr><th>Ticker</th><th>2-year stock chart</th><th>Valuation</th><th class="num">Bear</th><th class="num">Base</th><th class="num">Bull</th></tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody></table></div>
<p class="hyp-summary-note">Valuation snapshot: {valuation_as_of}. Scenario levels are model outputs, not automatic orders. Financial and foreign issuers use the more appropriate intrinsic-value method where a corporate DCF would be misleading; hover the confidence label for the method.</p>
</section>
{END}'''


def render_page(page: str, config: dict, charts: dict) -> str:
    symbols = extract_hypothesis_symbols(page)
    validate_config(symbols, config)
    if set((charts.get("charts") or {})) != set(symbols):
        raise ValueError("Chart symbols must exactly match hypothesis symbols")
    summary = render_summary(symbols, config, charts)
    if START in page and END in page:
        page = re.sub(re.escape(START) + r".*?" + re.escape(END), summary, page, count=1, flags=re.S)
    else:
        page, count = re.subn(r'(<div class="phead">.*?</div>)', r"\1" + summary, page, count=1, flags=re.S)
        if count != 1:
            raise ValueError("Could not find hypothesis page heading")
    if CSS_HREF not in page:
        page = page.replace(
            '<link rel="stylesheet" href="/trading/desk.css?v=19">',
            '<link rel="stylesheet" href="/trading/desk.css?v=19">\n'
            f'<link rel="stylesheet" href="{CSS_HREF}">',
            1,
        )
    page = re.sub(r'(class="meta">)\d+( theses)', rf'\g<1>{len(symbols)}\2', page, count=1)
    return page


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify checked-in artifacts without network access")
    args = parser.parse_args()

    page = PAGE.read_text()
    config = load_json(VALUATIONS)
    symbols = extract_hypothesis_symbols(page)
    validate_config(symbols, config)
    charts = load_json(CHARTS)
    if not args.check:
        charts = refresh_charts(symbols, charts)
        CHARTS.write_text(json.dumps(charts, separators=(",", ":")) + "\n")
    rendered = render_page(page, config, charts)
    if args.check:
        if rendered != page:
            print("[hypothesis-summary] stale: run python3 scripts/build-hypothesis-summary.py")
            return 1
        print(f"[hypothesis-summary] current: {len(symbols)} hypotheses")
        return 0
    PAGE.write_text(rendered)
    print(f"[hypothesis-summary] built: {len(symbols)} hypotheses, prices through {charts['as_of']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
