#!/usr/bin/env python3
"""Sync cron-owned classic dashboard regions into the routed trading desk pages.

The scheduled generators continue to own ``trading/classic/index.html`` and the
JSON chart assets. This bridge makes the routed production pages consume those
same generated regions so the new layout cannot drift after a cron refresh.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import pathlib
import re
import tempfile
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLASSIC = ROOT / "trading" / "classic" / "index.html"
DESK_SCRIPT = ROOT / "trading" / "desk.js"
BROKER_SCRIPT = ROOT / "js" / "trading-broker-light.js"
SCAN_CHARTS = ROOT / "trading" / "scan-charts.json"
VWAP_CHARTS = ROOT / "trading" / "vwap-charts.json"
CHART_MODAL_SCRIPT = ROOT / "js" / "hypothesis-chart-modal.b42a9700.js"
CHART_MODAL_STYLE = ROOT / "trading" / "hypothesis-summary.6e6f3b19.css"
PERFORMANCE_SCRIPT = ROOT / "js" / "trading-performance.js"
PERFORMANCE_STYLE = ROOT / "trading" / "performance-tape.css"


@dataclass(frozen=True)
class Route:
    path: pathlib.Path
    title: str
    description: str
    regions: tuple[str, ...]
    scripts: tuple[pathlib.Path, ...] = ()
    styles: tuple[pathlib.Path, ...] = ()
    meta: str = "Cron-owned data · source of truth: /trading/classic/ and versioned JSON assets"
    view: str = "source"


ROUTES = {
    "setups": Route(
        ROOT / "trading" / "vwap-setups" / "index.html",
        "VWAP Setups",
        "Breaks above or below both earnings VWAP and YTD VWAP stay active for three trading sessions.",
        ("SCAN",),
        (CHART_MODAL_SCRIPT, BROKER_SCRIPT),
        (CHART_MODAL_STYLE,),
        view="dual-vwap",
    ),
    "vwap": Route(
        ROOT / "trading" / "momentum" / "index.html",
        "Momentum",
        "US sectors, country ETFs, and crypto momentum versus VWAP, refreshed together from the same after-close pipeline.",
        ("VWAP", "CRYPTO"),
        (BROKER_SCRIPT,),
    ),
    "performance": Route(
        ROOT / "trading" / "performance" / "index.html",
        "Performance",
        "The quantity-free public performance panel from the latest portfolio refresh.",
        ("RESULTS",),
        (PERFORMANCE_SCRIPT,),
        (PERFORMANCE_STYLE,),
    ),
}


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def extract_region(classic: str, name: str, heading_id: str) -> str:
    pattern = rf"<!-- AUTO:{re.escape(name)}:START -->(.*?)<!-- AUTO:{re.escape(name)}:END -->"
    match = re.search(pattern, classic, re.S)
    if not match:
        raise ValueError(f"classic dashboard is missing AUTO:{name}")
    panel = match.group(1).strip()
    panel = re.sub(r'(<section\b[^>]*?)\s+hidden(?=[ >])', r"\1", panel, count=1)
    panel = re.sub(r'(<section\b[^>]*?)\s+aria-labelledby="[^"]+"', rf'\1 aria-labelledby="{heading_id}"', panel, count=1)
    return panel


def dual_vwap_side(close, earnings_vwap, ytd_vwap):
    if close is None or earnings_vwap is None or ytd_vwap is None:
        return None
    if close > earnings_vwap and close > ytd_vwap:
        return "long"
    if close < earnings_vwap and close < ytd_vwap:
        return "short"
    return None


def dual_vwap_setups(charts: dict, window: int = 3) -> dict[str, list[dict]]:
    """Return independent long/short break events active for ``window`` bars."""
    result: dict[str, list[dict]] = {"long": [], "short": []}
    for symbol, record in charts.items():
        series = record.get("series") or {}
        dates = series.get("dates") or []
        closes = series.get("c") or []
        earnings = series.get("ev") or []
        ytd = series.get("yv") or []
        if not dates or not (len(dates) == len(closes) == len(earnings) == len(ytd)):
            continue
        sides = [dual_vwap_side(c, e, y) for c, e, y in zip(closes, earnings, ytd)]
        latest = len(dates) - 1
        current_side = sides[latest]
        for side in result:
            triggers = [i for i, value in enumerate(sides) if i > 0 and value == side and sides[i - 1] != side]
            if not triggers:
                continue
            trigger = triggers[-1]
            age = latest - trigger
            if age >= window:
                continue
            result[side].append({
                "symbol": symbol,
                "company_name": record.get("company_name") or symbol,
                "sector": record.get("sector") or "",
                "sector_etf": record.get("sector_etf") or "",
                "trigger_date": dates[trigger],
                "day": age + 1,
                "current_side": current_side,
            })
    for rows in result.values():
        rows.sort(key=lambda row: (row["trigger_date"], row["symbol"]), reverse=True)
    return result


def _replace_once(pattern: str, replacement: str, text: str, label: str) -> str:
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise ValueError(f"unable to replace {label} in dual-VWAP route")
    return updated


def _short_date(iso: str) -> str:
    months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
    return f"{months[int(iso[5:7]) - 1]} {int(iso[8:10])}"


def sector_z_scores() -> dict[str, float]:
    payload = json.loads(VWAP_CHARTS.read_text())
    scores: dict[str, float] = {}
    for symbol, markup in (payload.get("charts") or {}).items():
        match = re.search(r"data-d='([^']+)'", markup)
        if match is None:
            continue
        data = json.loads(html.unescape(match.group(1)))
        values = data.get("z50") or []
        if values and values[-1] is not None:
            scores[symbol] = float(values[-1])
    return scores


def _dual_vwap_links(rows: list[dict], label: str) -> str:
    if not rows:
        return f'<p class="scan-qualified-links"><b>{label}</b> · None active</p>'
    side_label = {"long": "above both", "short": "below both", None: "between VWAPs"}
    links = []
    for row in rows:
        symbol = html.escape(row["symbol"], quote=True)
        company_name = html.escape(row["company_name"])
        sector_etf = html.escape(row["sector_etf"], quote=True)
        sector_z = row["sector_z"]
        direction = "up" if sector_z > 0 else "down" if sector_z < 0 else "flat"
        status = side_label[row["current_side"]]
        links.append(
            f'<button type="button" class="dual-vwap-chart-launch" data-hypothesis-chart-open="{symbol}" data-sector-direction="{direction}" '
            f'aria-haspopup="dialog" aria-controls="hypothesis-chart-dialog" '
            f'aria-label="Open {symbol} {company_name} setup and sector charts" translate="no"><b>{symbol}</b>'
            f'<span>{_short_date(row["trigger_date"])} · day {row["day"]}/3</span><em>{company_name}</em>'
            f'<small>{sector_etf} {sector_z:+.2f} · {status} now</small></button>'
        )
    return f'<div class="dual-vwap-list" aria-label="{label}">' + "".join(links) + "</div>"


def _momentum_setups(charts: dict, scores: dict[str, float]) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {"long": [], "short": []}
    long_labels = {"ENTER+", "ENTER"}
    short_labels = {"SHORT+", "SHORT", "BREAKING"}
    for symbol, record in charts.items():
        label = record.get("label")
        side = "long" if label in long_labels else "short" if label in short_labels else None
        if side is None:
            continue
        sector_etf = str(record.get("sector_etf") or "")
        if sector_etf not in scores:
            raise ValueError(f"missing sector Z-score for momentum setup {symbol}: {sector_etf}")
        result[side].append({
            "symbol": symbol,
            "company_name": record.get("company_name") or symbol,
            "sector": record.get("sector") or "",
            "sector_etf": sector_etf,
            "sector_z": scores[sector_etf],
            "label": label,
            "spread_z": (record.get("stats") or {}).get("spread_z"),
        })
    return result


def _momentum_links(rows: list[dict], label: str) -> str:
    if not rows:
        return f'<p class="scan-qualified-links"><b>{label}</b> · None active</p>'
    links = []
    for row in rows:
        symbol = html.escape(row["symbol"], quote=True)
        company_name = html.escape(row["company_name"])
        sector = html.escape(row["sector"])
        sector_etf = html.escape(row["sector_etf"], quote=True)
        sector_z = row["sector_z"]
        direction = "up" if sector_z > 0 else "down" if sector_z < 0 else "flat"
        spread = row["spread_z"]
        spread_copy = f" · Spread Z {spread:+.2f}" if isinstance(spread, (int, float)) else ""
        links.append(
            f'<button type="button" class="sector-setup-chart-launch" data-hypothesis-chart-open="{symbol}" data-sector-direction="{direction}" '
            f'aria-haspopup="dialog" aria-controls="hypothesis-chart-dialog" '
            f'aria-label="Open {symbol} {company_name} setup and sector charts" translate="no"><b>{symbol}</b>'
            f'<span>{html.escape(row["label"])}</span><em>{company_name}</em>'
            f'<small>{sector} · {sector_etf} {sector_z:+.2f}{spread_copy}</small></button>'
        )
    return f'<div class="sector-setup-list" aria-label="{label}">' + "".join(links) + "</div>"


def _chart_modal() -> str:
    return '''<dialog class="hyp-chart-dialog" id="hypothesis-chart-dialog" aria-labelledby="hypothesis-chart-dialog-title">
<div class="hyp-chart-dialog-frame" data-hypothesis-chart-detail>
<header class="hyp-chart-dialog-head"><div><span>VWAP setup data</span><h2 id="hypothesis-chart-dialog-title"><span data-hypothesis-chart-title>Setup charts</span></h2></div><button type="button" class="hyp-chart-dialog-close" data-hypothesis-chart-close aria-label="Close chart dialog">×</button></header>
<div class="hyp-chart-dialog-body"><div class="scan-setup-chart" data-hypothesis-chart-shell></div></div>
<p class="hyp-chart-dialog-note">Completed-session Spread Z, VWAP, and sector Z-score data from this VWAP Setups page.</p>
</div>
</dialog>'''


def render_dual_vwap_panel(panel: str) -> str:
    payload = json.loads(SCAN_CHARTS.read_text())
    setups = dual_vwap_setups(payload.get("charts") or {})
    scores = sector_z_scores()
    for rows in setups.values():
        for row in rows:
            if row["sector_etf"] not in scores:
                raise ValueError(f'missing sector Z-score for {row["symbol"]}: {row["sector_etf"]}')
            row["sector_z"] = scores[row["sector_etf"]]
    last_bar = html.escape(payload.get("last_bar") or "latest completed session")
    long_rows, short_rows = setups["long"], setups["short"]
    momentum = _momentum_setups(payload.get("charts") or {}, scores)
    sector_match = re.search(r'<div class="sector-summary">.*?</div>', panel, re.S)
    if sector_match is None:
        raise ValueError("dual-VWAP source panel is missing sector summary")
    sector_summary = sector_match.group(0)
    panel = panel[:sector_match.start()] + panel[sector_match.end():]
    panel = _replace_once(
        r'<div class="position-head">.*?</div>',
        f'<div class="position-head"><h2 id="scan-heading">Dual-VWAP breaks</h2><span>Signals through {last_bar} close</span></div>',
        panel,
        "position heading",
    )
    panel = _replace_once(
        r'<p class="trading-takeaway">.*?</p>',
        f'<p class="trading-takeaway">{len(long_rows)} active long and {len(short_rows)} active short dual-VWAP breaks. Each signal remains listed for its trigger session plus the next two trading sessions.</p>',
        panel,
        "takeaway",
    )
    panel = _replace_once(
        r'<p class="scan-risk-overlay">.*?</p>',
        '<p class="scan-risk-overlay">Close-only trigger · no sector, relative-strength, or risk-regime gate.</p>',
        panel,
        "risk overlay",
    )
    panel = _replace_once(
        r'<p class="signal-legend">.*?</p>',
        '<p class="signal-legend"><b>LONG</b> = close newly above both VWAPs · <b>SHORT</b> = close newly below both · active for 3 trading sessions even if price reverses</p>',
        panel,
        "legend",
    )
    setup_block = f'''<div class="position-group">
                    <h3>Long setups · {len(long_rows)}</h3>
{_dual_vwap_links(long_rows, "Long setups")}
                </div>
                <div class="position-group">
                    <h3>Short setups · {len(short_rows)}</h3>
{_dual_vwap_links(short_rows, "Short setups")}
                </div>'''
    panel = _replace_once(
        r'<div class="position-group">\s*<h3>Long setups.*?</div>\s*<div class="position-group">\s*<h3>Short setups.*?</div>',
        setup_block,
        panel,
        "setup lists",
    )
    dual_method = '<details class="trading-method" id="scan-method"><summary>How this works</summary><p>A long trigger fires when the daily close moves from anywhere else to above both the earnings-anchored VWAP and YTD VWAP. A short trigger is the mirror below both. The trigger day is day 1; the ticker remains active through day 3 even if it moves back between or through the VWAPs. A fast reversal can briefly appear on both lists. Missing earnings VWAP means no signal. This is a mechanical screen, not a recommendation.</p></details>'
    panel = _replace_once(
        r'<details class="trading-method" id="scan-method">.*?</details>',
        dual_method,
        panel,
        "method",
    )
    momentum_longs, momentum_shorts = momentum["long"], momentum["short"]
    sector_names = sorted({row["sector"] for row in momentum_longs + momentum_shorts})
    sector_clause = f" across {', '.join(html.escape(name) for name in sector_names)}" if sector_names else ""
    momentum_section = f'''<section class="sector-qualified-setups" aria-labelledby="sector-qualified-heading">
                <div class="position-head"><h2 id="sector-qualified-heading">Sector-qualified momentum</h2><span>Signals through {last_bar} close</span></div>
                <p class="trading-takeaway">{len(momentum_longs)} qualified long and {len(momentum_shorts)} qualified short setups{sector_clause}.</p>
                <p class="scan-risk-overlay">Cards follow the sector ETF: green is positive 50-day Z, red is negative 50-day Z.</p>
                {sector_summary}
                <p class="scan-chart-hint">Open a ticker for its setup and matching sector chart.</p>
                <div class="position-group">
                    <h3>Long setups · {len(momentum_longs)}</h3>
{_momentum_links(momentum_longs, "Sector-qualified long setups")}
                </div>
                <div class="position-group">
                    <h3>Short setups · {len(momentum_shorts)}</h3>
{_momentum_links(momentum_shorts, "Sector-qualified short setups")}
                </div>
                <details class="trading-method" id="sector-setup-method"><summary>How sector-qualified setups work</summary><p>Sector strength is the 50-session z-score of the sector ETF. Spread Z compares each stock with SPY; Dist Z measures distance from YTD VWAP. ENTER needs a hot sector, relative strength, and price above earnings VWAP; the + adds persistence above YTD VWAP. SHORT mirrors that setup in a weak sector. Earnings within about 9 days are flagged in the full universe. This is a mechanical screen, not a recommendation.</p></details>
            </section>'''
    method_match = re.search(r'<details class="trading-method" id="scan-method">.*?</details>', panel, re.S)
    if method_match is None:
        raise ValueError("dual-VWAP route is missing rendered method")
    method_html = method_match.group(0)
    panel = panel[:method_match.start()] + panel[method_match.end():]
    universe_marker = '<details class="scan-universe-disclosure" id="scan-universe" open>'
    universe_index = panel.find(universe_marker)
    if universe_index < 0:
        raise ValueError("dual-VWAP route is missing universe table")
    panel = panel[:universe_index] + method_html + "\n" + momentum_section + "\n                " + panel[universe_index:]
    config_match = re.search(r'<script type="application/json" id="scan-chart-config">(.*?)</script>', panel)
    if config_match is None:
        raise ValueError("dual-VWAP route is missing scan chart config")
    chart_config = json.loads(config_match.group(1))
    chart_config["vwap_url"] = f"/trading/vwap-charts.json?v={digest(VWAP_CHARTS)}"
    encoded_config = json.dumps(chart_config, separators=(",", ":"))
    panel = panel[:config_match.start(1)] + encoded_config + panel[config_match.end(1):]
    return panel + "\n" + _chart_modal()


def page_prefix(target: str, classic: str) -> str:
    marker = '<div class="wrap">'
    if marker not in target:
        raise ValueError("routed page is missing its content wrapper")
    prefix = target.rsplit(marker, 1)[0] + marker + "\n"
    stamp = re.search(r'<span class="trading-stamp">([^<]+)</span>', classic)
    if stamp:
        prefix = re.sub(
            r'<span class="stamp">.*?</span>',
            f'<span class="stamp">{stamp.group(1)}</span>',
            prefix,
            count=1,
            flags=re.S,
        )
    return prefix


def render_route(target: str, classic: str, route: Route) -> str:
    heading_id = "desk-route-heading"
    panels = "\n\n".join(extract_region(classic, name, heading_id) for name in route.regions)
    if route.view == "dual-vwap":
        panels = render_dual_vwap_panel(panels)
    script_tags = "\n".join(
        f'<script defer src="/{script.relative_to(ROOT).as_posix()}?v={digest(script)}"></script>'
        for script in route.scripts
    )
    prefix = page_prefix(target, classic)
    for style in route.styles:
        # digest like the scripts above: without it a CSS edit never reaches
        # browsers that already cached the unversioned file.
        path = style.relative_to(ROOT).as_posix()
        tag = f'<link rel="stylesheet" href="/{path}?v={digest(style)}">'
        # drop any prior link to this stylesheet (versioned or not) so the
        # digest is refreshed in place instead of stacking duplicates
        prefix = re.sub(rf'[ \t]*<link rel="stylesheet" href="/{re.escape(path)}(?:\?v=[a-f0-9]+)?">\n?', '', prefix)
        prefix = prefix.replace("</head>", tag + "\n</head>", 1)
    body = f'''<!-- AUTO:ROUTED_TRADING:START -->
<div class="phead"><h1 id="{heading_id}">{route.title}</h1><p class="take">{route.description}</p><p class="meta">{route.meta}</p></div>
{panels}
<!-- AUTO:ROUTED_TRADING:END -->'''
    rendered = prefix + body + "\n</div>\n" + (script_tags + "\n" if script_tags else "") + "</body>\n</html>\n"
    return re.sub(r'(?m)^[ \t]+$', '', rendered)


def atomic_write(path: pathlib.Path, content: str) -> None:
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(content)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def sync_sections(sections: list[str], check: bool = False) -> list[pathlib.Path]:
    classic = CLASSIC.read_text()
    changed: list[pathlib.Path] = []
    for section in sections:
        route = ROUTES[section]
        before = route.path.read_text()
        after = render_route(before, classic, route)
        if after == before:
            continue
        changed.append(route.path)
        if not check:
            atomic_write(route.path, after)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--section", action="append", choices=sorted(ROUTES), dest="sections")
    parser.add_argument("--check", action="store_true", help="report stale routed pages without writing")
    args = parser.parse_args()
    sections = args.sections or list(ROUTES)
    changed = sync_sections(sections, check=args.check)
    relative = [path.relative_to(ROOT).as_posix() for path in changed]
    if args.check:
        if changed:
            print("[trading-routes] stale: " + ", ".join(relative))
            return 1
        print(f"[trading-routes] current: {', '.join(sections)}")
        return 0
    if changed:
        print("[trading-routes] synced: " + ", ".join(relative))
    else:
        print(f"[trading-routes] already current: {', '.join(sections)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
