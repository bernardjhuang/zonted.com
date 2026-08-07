#!/usr/bin/env python3
"""Shared Trading Desk chrome derived from checked-in market artifacts."""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VWAP_CHARTS = ROOT / "trading" / "vwap-charts.json"
SECTOR_ETFS = {"XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"}
SECTOR_NAMES = {
    "XLB": "Materials",
    "XLC": "Communication Services",
    "XLE": "Energy",
    "XLF": "Financials",
    "XLI": "Industrials",
    "XLK": "Technology",
    "XLP": "Consumer Staples",
    "XLRE": "Real Estate",
    "XLU": "Utilities",
    "XLV": "Health Care",
    "XLY": "Consumer Discretionary",
}
NAV_ITEMS = (
    ("/trading/", "Desk"),
    ("/trading/autonomous/", "🤖 Autonomous"),
    ("/trading/themes/", "Themes"),
    ("/trading/vwap-setups/", "VWAP Setups"),
    ("/trading/momentum/", "Momentum"),
    ("/trading/mentality/", "Mentality"),
    ("/trading/performance/", "Performance"),
)


def sector_z_scores(path: Path = VWAP_CHARTS) -> dict[str, float]:
    payload = json.loads(path.read_text())
    scores: dict[str, float] = {}
    for symbol in SECTOR_ETFS:
        markup = (payload.get("charts") or {}).get(symbol)
        if not markup:
            continue
        match = re.search(r"data-d='([^']+)'", markup)
        if match is None:
            continue
        data = json.loads(html.unescape(match.group(1)))
        values = data.get("z50") or []
        if values and values[-1] is not None:
            scores[symbol] = float(values[-1])
    if set(scores) != SECTOR_ETFS:
        missing = ", ".join(sorted(SECTOR_ETFS - set(scores)))
        raise ValueError(f"Status bar needs current 50-day Z-scores for all sectors; missing: {missing}")
    return scores


def rank_sector_pills(scores: dict[str, float]) -> list[dict[str, str | float]]:
    if set(scores) != SECTOR_ETFS:
        raise ValueError("Sector pill ranking needs exactly the 11 US sector ETFs")
    ranked = sorted(scores.items(), key=lambda row: (-row[1], row[0]))
    leaders = [{"kind": "leader", "symbol": symbol, "z": value} for symbol, value in ranked[:2]]
    laggards = [{"kind": "laggard", "symbol": symbol, "z": value} for symbol, value in reversed(ranked[-2:])]
    return leaders + laggards


def render_sector_status_pills(scores: dict[str, float] | None = None) -> str:
    rows = rank_sector_pills(scores or sector_z_scores())
    links = []
    for row in rows:
        symbol = str(row["symbol"])
        kind = str(row["kind"])
        value = float(row["z"])
        title_kind = "Leading" if kind == "leader" else "Lagging"
        title = f"{title_kind} sector — {SECTOR_NAMES[symbol]} · 50-day Z {value:+.2f}"
        links.append(
            f'<a class="sector-chip sector-chip--{kind}" href="/trading/vwap-setups/#sector-qualified-heading" '
            f'data-sector-symbol="{symbol}" data-sector-z="{value:+.2f}" title="{html.escape(title, quote=True)}">'
            f'<b>{symbol}</b><em>{value:+.2f}</em></a>'
        )
    return '<span class="sector-chipset" aria-label="Leading and lagging sectors">' + "".join(links) + "</span>"


def replace_sector_status_pills(source: str, scores: dict[str, float] | None = None) -> str:
    markup = render_sector_status_pills(scores)
    if 'class="sector-chipset"' in source:
        rendered, count = re.subn(
            r'<span class="sector-chipset".*?</span>', markup, source, count=1, flags=re.S
        )
    else:
        rendered, count = re.subn(
            r'(<span class="chipset">.*?</span>)', rf'\1{markup}', source, count=1, flags=re.S
        )
    if count != 1:
        raise ValueError("Trading status bar model chipset not found")
    return rendered


def refresh_sector_status_pills() -> list[Path]:
    scores = sector_z_scores()
    changed: list[Path] = []
    paths = sorted((ROOT / "trading").glob("**/index.html")) + [ROOT / "trading" / "pipeline.html"]
    for path in paths:
        source = path.read_text()
        if '<div class="status-metrics">' not in source:
            continue
        rendered = replace_sector_status_pills(source, scores)
        if rendered != source:
            path.write_text(rendered)
            changed.append(path)
    return changed


def normalize_trading_subnav(source: str, path: Path) -> str:
    relative = path.relative_to(ROOT).as_posix()
    current_href = "/trading/" if relative == "trading/index.html" else None
    for href, _label in NAV_ITEMS[1:]:
        if relative == href.lstrip("/") + "index.html":
            current_href = href
            break
    links = "".join(
        f'<a href="{href}"{current}>{label}</a>'
        for href, label in NAV_ITEMS
        for current in (' aria-current="page"' if href == current_href else '',)
    )
    nav = f'<nav class="subnav" aria-label="Sections"><div class="wrap">{links}</div></nav>'
    rendered, count = re.subn(r'<nav class="subnav" aria-label="Sections">.*?</nav>', nav, source, count=1, flags=re.S)
    if count != 1:
        raise ValueError(f"Trading subnav not found in {relative}")
    return rendered
