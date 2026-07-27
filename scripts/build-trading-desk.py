#!/usr/bin/env python3
"""Build the merged Zonted trading desk from checked-in source data.

The default/close mode consumes completed-session artifacts only. Morning mode accepts
an explicit validated quote file and changes intraday fields without touching analytics.
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

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "trading/index.html"
HYPOTHESES = ROOT / "trading/hypotheses/index.html"
POSITIONS = ROOT / "trading/desk-positions.json"
VALUATIONS = ROOT / "trading/hypothesis-valuations.json"
CHARTS = ROOT / "trading/hypothesis-charts.json"
SCAN = ROOT / "trading/scan-charts.json"
VWAP = ROOT / "trading/vwap-charts.json"
DESK_CSS = ROOT / "trading/desk.css"
DESK_JS = ROOT / "trading/desk.js"
CHART_MODAL_JS = ROOT / "js/hypothesis-chart-modal.1b5e1178.js"
START_POS = "<!-- AUTO:DESK_POSITIONS:START -->"
END_POS = "<!-- AUTO:DESK_POSITIONS:END -->"
START_HYP = "<!-- AUTO:DESK_HYPOTHESES:START -->"
END_HYP = "<!-- AUTO:DESK_HYPOTHESES:END -->"
COLGROUP = '<colgroup><col style="width:17%"><col style="width:8%"><col style="width:7%"><col style="width:8%"><col style="width:11%"><col style="width:6.5%"><col style="width:7%"><col style="width:18%"><col style="width:11%"><col style="width:6.5%"></colgroup>'
OTC = {"BYDDY", "NTDOY"}


def load(path: Path):
    return json.loads(path.read_text())


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


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
        for key in ("catalyst", "trigger", "stance"):
            match = re.search(rf'data-desk-{key}="([^"]+)"', attrs)
            if not match:
                raise ValueError(f"{symbol} is missing data-desk-{key}")
            values[key] = html.unescape(match.group(1))
        out[symbol] = values
    if len(out) != 11:
        raise ValueError(f"Expected 11 hypothesis articles, got {len(out)}")
    return out


def quotes_from(path: Path | None) -> tuple[dict[str, dict[str, float]], dt.datetime | None]:
    if path is None:
        return {}, None
    payload = load(path)
    quotes = payload.get("quotes") or {}
    stamp = dt.datetime.fromisoformat(str(payload["generated_at"]).replace("Z", "+00:00"))
    for symbol, quote in quotes.items():
        price = quote.get("price")
        day = quote.get("day_pct")
        if not isinstance(price, (int, float)) or price <= 0:
            raise ValueError(f"Invalid morning price for {symbol}")
        if not isinstance(day, (int, float)) or not -100 < day < 1000:
            raise ValueError(f"Invalid morning day change for {symbol}")
    return quotes, stamp


def row_market(symbol: str, hyp_chart: dict, scan_chart: dict | None, quote: dict | None) -> dict:
    if symbol in OTC:
        return {"feed": False}
    dates = hyp_chart["dates"]
    closes = [float(v) for v in hyp_chart["close"]]
    if scan_chart:
        series = scan_chart["series"]
        daily = [float(v) for v in series["c"]]
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
    return {
        "feed": True,
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


def ytd_chart(symbol: str, market: dict, entry: float | None = None, kill: float | None = None) -> str:
    if not market.get("feed"):
        return '<div class="desk-no-feed">— <span>No feed</span></div>'
    pairs = [(d, c) for d, c in zip(market["dates"], market["closes"]) if d >= "2026-01-01"]
    if not pairs:
        pairs = list(zip(market["dates"], market["closes"]))[-30:]
    dates = [d for d, _ in pairs]
    closes = [float(c) for _, c in pairs]
    base = closes[0]
    values = [(value / base - 1) * 100 for value in closes]
    levels: list[tuple[str, float, str]] = [("zero", 0.0, "YTD 0%")]
    if entry is not None:
        levels.append(("entry", (entry / base - 1) * 100, f"Entry {money(entry)}"))
    if kill is not None:
        levels.append(("kill", (kill / base - 1) * 100, f"Kill {money(kill)}"))
    domain = values + [level for _kind, level, _label in levels]
    low, high = min(domain), max(domain)
    margin = max((high - low) * .08, 1.0)
    low -= margin
    high += margin
    width, height, pad = 118.0, 44.0, 2.0
    span = high - low or 1
    rules = []
    for kind, value, label in levels:
        y = pad + (high - value) * (height - 2 * pad) / span
        rules.append(f'<line class="desk-ytd-rule desk-ytd-rule--{kind}" x1="2" y1="{y:.1f}" x2="116" y2="{y:.1f}"><title>{html.escape(label)}</title></line>')
    change = values[-1]
    direction = "up" if change >= 0 else "down"
    points = polyline(values, width, height, pad, low, high)
    return (
        f'<figure class="desk-ytd desk-ytd--{direction}" data-desk-ytd-chart="{symbol}">'
        f'<svg viewBox="0 0 118 44" role="img" aria-label="{symbol} year-to-date {change:+.1f} percent">'
        f'{"".join(rules)}<polyline class="desk-ytd-line" points="{points}"/></svg>'
        f'<figcaption>{change:+.1f}% YTD</figcaption></figure>'
    )


def vol(values: list[float]) -> float:
    returns = [b / a - 1 for a, b in zip(values, values[1:]) if a > 0]
    return statistics.stdev(returns) * math.sqrt(52) * 100 if len(returns) > 2 else 0.0


def detail_chart(symbol: str, market: dict, levels: dict) -> str:
    if not market.get("feed"):
        return f'<div class="desk-no-feed desk-no-feed--chart" data-desk-two-year-chart="{symbol}">— <span>No feed · two-year chart unavailable</span></div>'
    values = market["closes"]
    scenarios = {k: float(levels[k]) for k in ("bear", "base", "bull")}
    domain = values + list(scenarios.values())
    low, high = min(domain), max(domain)
    margin = max((high - low) * .04, 1)
    low, high = max(0, low - margin), high + margin
    width, height, pad = 420.0, 150.0, 8.0
    span = high - low or 1
    y = lambda value: pad + (high - value) * (height - 2 * pad) / span
    rules = "".join(
        f'<line class="desk-detail-rule desk-detail-rule--{case}" x1="8" y1="{y(price):.1f}" x2="412" y2="{y(price):.1f}"><title>{case.title()} {money(price)}</title></line>'
        for case, price in scenarios.items()
    )
    band_y = min(y(scenarios["bear"]), y(scenarios["bull"]))
    band_h = abs(y(scenarios["bear"]) - y(scenarios["bull"]))
    points = polyline(values, width, height, pad, low, high)
    return (
        f'<figure class="desk-detail-chart" data-desk-two-year-chart="{symbol}"><svg viewBox="0 0 420 150" role="img" aria-label="{symbol} up to two-year price with intrinsic levels">'
        f'<rect class="desk-detail-band" x="8" y="{band_y:.1f}" width="404" height="{band_h:.1f}"/>{rules}'
        f'<polyline class="desk-detail-price" points="{points}"/></svg>'
        f'<figcaption>Up to 2 years · Beta {market["beta"]:.2f} · Annualized vol {vol(values):.0f}%</figcaption></figure>'
    )


def feed_cell(label: str, value: str, cls: str = "") -> str:
    return f'<td class="{cls}" data-label="{label}">{value}</td>'


def beta_label(beta: float) -> str:
    note = "high" if beta >= 2 else "low" if beta <= .75 else ""
    return f'{beta:.2f}{f"<small>{note}</small>" if note else ""}'


def valuation_detail(symbol: str, market: dict, valuation: dict, position: dict | None) -> str:
    levels = valuation["entry_levels"]
    metrics = "".join(f'<div><span>{html.escape(item["label"])}</span><b>{html.escape(item["value"])}</b></div>' for item in valuation["valuation_metrics"])
    last = market.get("last")
    distance = ((last / float(levels["base"]) - 1) * 100) if isinstance(last, (int, float)) else None
    sector = position["sector"] if position else "See full thesis"
    tiles = "".join(f'<div class="desk-entry-tile desk-entry-tile--{case}"><span>{case.title()}</span><b>{money(float(levels[case]))}</b></div>' for case in ("bear", "base", "bull"))
    distance_line = f'Trading {distance:+.0f}% versus the base case' if distance is not None else "Market price feed unavailable"
    canonical = f"/trading/hypotheses/#hypothesis-{symbol.lower()}-setup"
    return f'''<div class="desk-fold-grid">
<div>{detail_chart(symbol, market, levels)}</div>
<div class="desk-valuation" data-desk-valuation><h4>Valuation</h4>{metrics}<div><span>Last</span><b>{money(last)}</b></div><div><span>Sector</span><b>{html.escape(sector)}</b></div></div>
<div class="desk-entry" data-desk-entry-tiles><h4>Intrinsic entry levels</h4><div class="desk-entry-tiles">{tiles}</div><span class="desk-confidence">{html.escape(valuation["confidence"])} confidence</span><p>{html.escape(distance_line)}</p><div class="desk-detail-actions"><button type="button" data-hypothesis-chart-open="{symbol}" aria-haspopup="dialog" aria-controls="hypothesis-chart-dialog">Setup chart</button><button type="button" data-thesis-open="{symbol}" aria-haspopup="dialog" aria-controls="desk-thesis-dialog">Full thesis</button><a href="{canonical}">Canonical thesis</a></div></div>
</div>'''


def no_feed_market_cells() -> tuple[str, str, str, str, str]:
    cell = '<div class="desk-no-feed">— <span>No feed</span></div>'
    return cell, cell, cell, cell, cell


def position_rows(positions: list[dict], metadata: dict, markets: dict, valuations: dict, as_of: dt.date) -> str:
    rows = []
    for position in sorted(positions, key=lambda p: metadata[p["symbol"]]["catalyst"]):
        symbol = position["symbol"]
        market = markets[symbol]
        meta = metadata[symbol]
        catalyst = dt.date.fromisoformat(meta["catalyst"])
        days = max(0, (catalyst - as_of).days)
        pnl = (market["last"] / float(position["entry"]) - 1) * 100
        kill = position.get("kill")
        if kill:
            room = (market["last"] / float(kill) - 1) * 100
            room_html = f'<div class="desk-room {"desk-room--tight" if room < 5 else ""}"><b>{room:.1f}%</b><span style="--room:{min(max(room,0),25)/25*100:.0f}%"></span></div>'
        else:
            room_html = '<div class="desk-room"><b>—</b><small>No hard kill</small></div>'
        edge = "up" if market["day"] > .05 else "down" if market["day"] < -.05 else "flat"
        edge_word = {"up":"Up", "down":"Down", "flat":"Flat"}[edge]
        detail_id = f"desk-detail-{symbol.lower()}"
        main = f'''<tr class="desk-main-row" data-desk-kind="position" data-desk-symbol="{symbol}" data-catalyst-date="{meta['catalyst']}" data-edge="{edge}">
<td data-label="Position"><button class="desk-row-toggle" type="button" aria-expanded="false" aria-controls="{detail_id}"><span class="desk-edge-word">{edge_word}</span><b>{symbol}</b><small>{html.escape(position['instrument'])}</small></button></td>
{feed_cell('Last', money(market['last']), 'desk-num')}{feed_cell('Day', pct(market['day']), 'desk-num desk-sign--'+edge)}{feed_cell('P&L', pct(pnl), 'desk-num')}{feed_cell('Room to kill', room_html)}{feed_cell('Beta', beta_label(market['beta']), 'desk-num')}{feed_cell('Spread Z', f"{market['spread']:+.2f}", 'desk-num')}{feed_cell('YTD · levels', ytd_chart(symbol, market, float(position['entry']), float(kill) if kill else None))}{feed_cell('Next catalyst', f'<span class="desk-catalyst">{catalyst.strftime("%b %-d")}</span>')}{feed_cell('In', f'{days}d', 'desk-num')}
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
            last, day, beta, spread, ytd = money(market["last"]), pct(market["day"]), beta_label(market["beta"]), f'{market["spread"]:+.2f}', ytd_chart(symbol, market)
        else:
            last, day, beta, spread, ytd = no_feed_market_cells()
        main = f'''<tr class="desk-main-row" data-desk-kind="hypothesis" data-desk-symbol="{symbol}" data-catalyst-date="{meta['catalyst']}" data-edge="{edge}" data-feed-state="{'live' if market.get('feed') else 'no-feed'}">
<td data-label="Thesis"><button class="desk-row-toggle" type="button" aria-expanded="false" aria-controls="{detail_id}"><span class="desk-edge-word">{edge_word}</span><b>{symbol}</b><span class="desk-stance desk-stance--{stance}">{stance.replace('-', ' ')}</span></button></td>
{feed_cell('Last', last, 'desk-num')}{feed_cell('Day', day, 'desk-num')}<td colspan="2" data-label="What would move it"><span class="desk-trigger">{html.escape(meta['trigger'])}</span></td>{feed_cell('Beta', beta, 'desk-num')}{feed_cell('Spread Z', spread, 'desk-num')}{feed_cell('YTD', ytd)}{feed_cell('Next catalyst', f'<span class="desk-catalyst {"desk-catalyst--soon" if days <= 7 else ""}">{catalyst.strftime("%b %-d")}</span>')}{feed_cell('In', f'{days}d', 'desk-num')}
</tr>'''
        detail = f'<tr class="desk-detail-row" id="{detail_id}" hidden><td colspan="10">{valuation_detail(symbol, market, valuations[symbol], None)}</td></tr>'
        rows.append(main + detail)
    return "\n".join(rows)


def table(title: str, subtitle: str, body: str, hypotheses: bool = False) -> str:
    if hypotheses:
        heads = '<th>Thesis</th><th>Last</th><th>Day</th><th colspan="2">What would move it</th><th>Beta</th><th>Spread Z</th><th>YTD</th><th>Next catalyst</th><th>In</th>'
    else:
        heads = '<th>Position</th><th>Last</th><th>Day</th><th>P&amp;L</th><th>Room to kill</th><th>Beta</th><th>Spread Z</th><th>YTD · levels</th><th>Next catalyst</th><th>In</th>'
    return f'<div class="desk-table-head"><h2>{title}</h2><span>{subtitle}</span></div><div class="desk-table-scroll"><table class="desk-blotter-table">{COLGROUP}<thead><tr>{heads}</tr></thead><tbody>{body}</tbody></table></div>'


def modals() -> str:
    config = json.dumps({"url": f"/trading/scan-charts.json?v={digest(SCAN)}", "vwap_url": f"/trading/vwap-charts.json?v={digest(VWAP)}"}, separators=(",", ":"))
    return f'''<dialog class="hyp-chart-dialog" id="hypothesis-chart-dialog" aria-labelledby="hypothesis-chart-dialog-title"><div class="hyp-chart-dialog-frame" data-hypothesis-chart-detail><header class="hyp-chart-dialog-head"><div><span>Watchlist scanner data</span><h2 id="hypothesis-chart-dialog-title"><span data-hypothesis-chart-title>Setup charts</span></h2></div><button type="button" class="hyp-chart-dialog-close" data-hypothesis-chart-close aria-label="Close chart dialog">×</button></header><div class="hyp-chart-dialog-body"><div class="scan-setup-chart" data-hypothesis-chart-shell></div></div></div></dialog>
<script type="application/json" id="scan-chart-config">{config}</script>
<dialog class="desk-thesis-dialog" id="desk-thesis-dialog" data-thesis-source="/trading/hypotheses/" aria-labelledby="desk-thesis-title"><div class="desk-thesis-frame"><header><h2 id="desk-thesis-title">Full thesis</h2><button type="button" data-thesis-close aria-label="Close thesis dialog">×</button></header><div data-thesis-summary></div><div data-thesis-body><p>Loading thesis…</p></div></div></dialog>'''


def sync_shell_assets() -> None:
    css_ref = f'/trading/desk.css?v={digest(DESK_CSS)}'
    js_ref = f'/trading/desk.js?v={digest(DESK_JS)}'
    modal_ref = f'/js/hypothesis-chart-modal.1b5e1178.js?v={digest(CHART_MODAL_JS)}'
    for path in sorted((ROOT / "trading").glob("**/index.html")):
        source = path.read_text()
        source = re.sub(r'/trading/desk\.css\?v=[a-f0-9]+', css_ref, source)
        source = re.sub(r'/trading/desk\.js\?v=[a-f0-9]+', js_ref, source)
        source = re.sub(r'<a href="/trading/hypotheses/"(?: aria-current="page")?>Hypotheses</a>', '', source)
        path.write_text(source)


def render(mode: str, quote_path: Path | None) -> str:
    page = PAGE.read_text()
    hypothesis_source = HYPOTHESES.read_text()
    metadata = article_metadata(hypothesis_source)
    positions_payload = load(POSITIONS)
    positions = positions_payload["positions"]
    valuation = load(VALUATIONS)["rows"]
    charts_payload = load(CHARTS)
    charts = charts_payload["charts"]
    scan = load(SCAN)["charts"]
    quotes, quote_stamp = quotes_from(quote_path)
    symbols = sorted(metadata)
    markets = {symbol: row_market(symbol, charts[symbol], scan.get(symbol), quotes.get(symbol)) for symbol in symbols}
    as_of = quote_stamp.date() if quote_stamp else dt.date.fromisoformat(charts_payload["as_of"])
    position_symbols = {p["symbol"] for p in positions}
    tracked = [s for s in symbols if s not in position_symbols]
    pos_body = position_rows(positions, metadata, markets, valuation, as_of)
    hyp_body = hypothesis_rows(tracked, metadata, markets, valuation, as_of)
    main = f'''<section class="desk-main" data-desk-source-articles="{len(metadata)}">
{START_POS}
{table('Positions', f'{len(positions)} open · live price + authored risk levels', pos_body)}
{END_POS}
{START_HYP}
{table('Tracked hypotheses', f'{len(tracked)} thesis-only names · sorted by catalyst', hyp_body, True)}
{END_HYP}
</section>'''
    page, count = re.subn(r'<section class="desk-main"[^>]*>.*?</section>', main, page, count=1, flags=re.S)
    if count != 1:
        raise ValueError("Desk main section not found")
    page = re.sub(r'\s*<dialog class="hyp-chart-dialog".*?</dialog>\s*<script type="application/json" id="scan-chart-config">.*?</script>\s*<dialog class="desk-thesis-dialog".*?</dialog>', '', page, flags=re.S)
    page = re.sub(r'\s*<script defer src="/js/hypothesis-chart-modal\.1b5e1178\.js(?:\?v=[a-f0-9]+)?"></script>', '', page)
    modal_ref = f'/js/hypothesis-chart-modal.1b5e1178.js?v={digest(CHART_MODAL_JS)}'
    page = page.replace('</body>', f'{modals()}\n<script defer src="{modal_ref}"></script>\n</body>', 1)
    if mode == "morning" and quote_stamp:
        stamp = quote_stamp.astimezone().strftime("Live · %-I:%M %p CT")
    else:
        stamp = f"Snapshot · {as_of.strftime('%B %-d, %Y')}"
    page = re.sub(r'(<span class="stamp">).*?(</span>)', rf'\1{stamp}\2', page, count=1)
    return page


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify checked-in artifacts without network access")
    parser.add_argument("--mode", choices=("close", "morning"), default="close")
    parser.add_argument("--quotes", type=Path, help="validated explicit quote JSON for morning mode")
    args = parser.parse_args()
    if args.mode == "morning" and args.quotes is None:
        parser.error("--mode morning requires --quotes")
    rendered = render(args.mode, args.quotes)
    if args.check:
        if rendered != PAGE.read_text():
            print("[trading-desk] stale: run python3 scripts/build-trading-desk.py")
            return 1
        print("[trading-desk] current and network-free: 6 positions + 5 tracked hypotheses")
        return 0
    PAGE.write_text(rendered)
    sync_shell_assets()
    print(f"[trading-desk] built {args.mode}: 6 positions + 5 tracked hypotheses")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
