#!/usr/bin/env python3
"""Synchronize the canonical ticker hypotheses into the preserved classic dashboard."""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "trading" / "hypothesis-source.html"
CLASSIC = ROOT / "trading" / "classic" / "index.html"
VALUATIONS = ROOT / "trading" / "hypothesis-valuations.json"
CHARTS = ROOT / "trading" / "hypothesis-charts.json"
PANEL_PATTERN = re.compile(
    r'<section class="trading-panel hypothesis-panel" id="hypotheses-panel".*?</section>\s*'
    r'(?=<!-- AUTO:SCAN:START -->)',
    re.S,
)
ARTICLE_PATTERN = re.compile(
    r'<article class="hypothesis-detail" id="hypothesis-([a-z0-9.-]+)-setup".*?</article>',
    re.S,
)


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", fragment))).strip()


def _attribute(fragment: str, name: str) -> str:
    match = re.search(rf'{re.escape(name)}="([^"]+)"', fragment)
    if match is None:
        raise ValueError(f"Missing {name}")
    return html.unescape(match.group(1))


def _extract(pattern: str, fragment: str, label: str) -> str:
    match = re.search(pattern, fragment, re.S)
    if match is None:
        raise ValueError(f"Missing {label}")
    return match.group(1)


def _classic_article(article: str) -> str:
    rendered, count = re.subn(
        r'<details class="hyp-fold"><summary>.*?</summary>',
        "",
        article,
        count=1,
        flags=re.S,
    )
    if count != 1:
        raise ValueError("Canonical hypothesis article is missing its disclosure")
    rendered, count = re.subn(r"</details>(?=</article>$)", "", rendered, count=1)
    if count != 1:
        raise ValueError("Canonical hypothesis disclosure did not close at article end")
    rendered = re.sub(r'\s*<p class="hypothesis-bottom-line">.*?</p>', "", rendered, count=1, flags=re.S)
    rendered = re.sub(r'\s*<p class="hypothesis-sources">.*?</p>', "", rendered, count=1, flags=re.S)
    return rendered


def _card(symbol: str, article: str, chart: dict) -> str:
    status = _text(_extract(r'<span class="hypothesis-status">(.*?)</span>', article, f"{symbol} status"))
    bottom_line = _extract(r'<p class="hypothesis-bottom-line">(.*?)</p>', article, f"{symbol} bottom line")
    trigger = _attribute(article, "data-desk-trigger")
    dates = chart.get("dates") or []
    closes = chart.get("close") or []
    if not dates or len(dates) != len(closes):
        raise ValueError(f"{symbol} chart history is missing")
    last_date = dates[-1]
    last_close = float(closes[-1])
    return f'''                    <article class="portfolio-card hypothesis-card is-open" data-hypothesis-symbol="{html.escape(symbol, quote=True)}">
                        <div class="portfolio-card-head">
                            <h2>{html.escape(symbol)}</h2>
                            <span class="hypothesis-status">{html.escape(status)}</span>
                        </div>
                        <p class="hypothesis-price"><strong>${last_close:,.2f} close</strong><span>{html.escape(last_date)} completed session</span></p>
                        <p class="portfolio-label">Thesis</p>
                        <p class="portfolio-copy">{bottom_line}</p>
                        <p class="portfolio-label">Monitoring</p>
                        <p class="portfolio-copy">{html.escape(trigger)}</p>
                    </article>'''


def render_panel(source: str, valuations: dict, charts: dict) -> str:
    matches = list(ARTICLE_PATTERN.finditer(source))
    symbols = [match.group(1).upper() for match in matches]
    expected = list(valuations.get("rows") or {})
    if symbols != expected:
        raise ValueError(f"Canonical article/config order mismatch: {symbols} != {expected}")
    if set(symbols) != set(charts.get("charts") or {}):
        raise ValueError("Canonical article/chart membership mismatch")

    complete_articles = {
        match.group(1).upper(): match.group(0)
        for match in matches
    }

    cards = "\n".join(
        _card(symbol, complete_articles[symbol], charts["charts"][symbol])
        for symbol in symbols
    )
    details = "\n".join(
        "                    " + _classic_article(complete_articles[symbol]).replace("\n", "\n                    ")
        for symbol in symbols
    )
    as_of = str(valuations["as_of"])
    display_date = f"{as_of[5:7]}/{as_of[8:10]}/{as_of[:4]}"
    return f'''<section class="trading-panel hypothesis-panel" id="hypotheses-panel" role="tabpanel" tabindex="0" aria-labelledby="hypotheses-tab" hidden>
                <div class="position-head">
                    <h2 id="hypotheses-heading">Ticker hypotheses</h2>
                    <span>{len(symbols)} active theses · updated {display_date}</span>
                </div>
                <p class="trading-takeaway">Theses being built and monitored before and after entry. The trigger, catalyst, and kill conditions have to be explicit.</p>
                <div class="portfolio-grid" aria-label="Ticker hypotheses">
{cards}
                </div>
                <div class="portfolio-details">
{details}
                </div>
                <p class="trading-note">Research framework, not a trade recommendation. Current holdings appear in Portfolio; prices and regulatory status can change quickly.</p>
            </section>

            '''


def render_classic(classic: str, source: str, valuations: dict, charts: dict) -> str:
    panel = render_panel(source, valuations, charts)
    rendered, count = PANEL_PATTERN.subn(panel, classic, count=1)
    if count != 1:
        raise ValueError("Classic hypothesis panel was not found exactly once")
    return rendered


def atomic_write(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    os.replace(temp_path, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    source = SOURCE.read_text()
    classic = CLASSIC.read_text()
    valuations = json.loads(VALUATIONS.read_text())
    charts = json.loads(CHARTS.read_text())
    rendered = render_classic(classic, source, valuations, charts)
    if args.check:
        if rendered != classic:
            raise SystemExit("Classic hypotheses are stale; run scripts/sync-classic-hypotheses.py")
        print(f"[classic-hypotheses] current: {len(valuations['rows'])} hypotheses")
        return 0
    atomic_write(CLASSIC, rendered)
    print(f"[classic-hypotheses] built: {len(valuations['rows'])} hypotheses")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
