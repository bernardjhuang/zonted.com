#!/usr/bin/env python3
"""Render the latest Gemini Risk JSON entry into its public Trading Desk page."""
from __future__ import annotations

import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "trading" / "gemini-risk.json"
PAGE = ROOT / "trading" / "gemini-risk" / "index.html"
START = "<!-- AUTO:GEMINI_RISK:START -->"
END = "<!-- AUTO:GEMINI_RISK:END -->"


def validate(payload: dict) -> dict:
    if payload.get("schema_version") != 1:
        raise ValueError("gemini-risk schema_version must be 1")
    if payload.get("model") != "Gemini 3.1 Pro":
        raise ValueError("gemini-risk model must be Gemini 3.1 Pro")
    entries = payload.get("entries") or []
    if not entries:
        raise ValueError("gemini-risk requires at least one entry")
    entry = entries[0]
    rating = float(entry["rating"])
    if not 0 <= rating <= 10:
        raise ValueError("gemini-risk rating must be between 0 and 10")
    if len(entry.get("sections") or []) != 5:
        raise ValueError("gemini-risk entry must have five analysis sections")
    if not all(section.get("title") and section.get("paragraphs") for section in entry["sections"]):
        raise ValueError("gemini-risk sections require titles and paragraphs")
    return entry


def render(entry: dict) -> str:
    esc = lambda value: html.escape(str(value), quote=True)
    cards = []
    for number, section in enumerate(entry["sections"], 1):
        paragraphs = "".join(f"<p>{esc(text)}</p>" for text in section["paragraphs"])
        cards.append(
            f'<section class="gemini-risk-card"><div class="gemini-risk-number">{number:02d}</div>'
            f'<div><h2>{esc(section["title"])}</h2>{paragraphs}</div></section>'
        )
    rating = float(entry["rating"])
    return f'''<article class="gemini-risk-report" data-model="Gemini 3.1 Pro" data-rating="{rating:g}">
  <header class="gemini-risk-verdict">
    <div><span class="gemini-risk-kicker">Current market stance</span><h2>{esc(entry["stance"])}</h2><p>{esc(entry["summary"])}</p></div>
    <div class="gemini-risk-score" aria-label="Risk appetite {rating:g} out of 10"><strong>{rating:g}</strong><span>/ 10</span><small>risk appetite</small></div>
  </header>
  <div class="gemini-risk-scale" aria-hidden="true"><span style="width:{rating * 10:g}%"></span></div>
  <p class="gemini-risk-dates">Assessment {esc(entry["as_of"])} · market data through {esc(entry["market_data_through"])}</p>
  <div class="gemini-risk-grid">{''.join(cards)}</div>
  <section class="gemini-risk-bottom"><span>Bottom line</span><p>{esc(entry["reasoning"])}</p></section>
  <details class="trading-method"><summary>Attribution and citation note</summary><p>{esc(entry["citation_note"])}</p></details>
</article>'''


def main() -> int:
    entry = validate(json.loads(DATA.read_text()))
    page = PAGE.read_text()
    if START not in page or END not in page:
        raise ValueError("gemini-risk page is missing AUTO markers")
    block = f"{START}\n{render(entry)}\n{END}"
    updated = re.sub(re.escape(START) + r".*?" + re.escape(END), block, page, count=1, flags=re.S)
    if updated == page:
        print(f"[gemini-risk] already current: {entry['as_of']} · {entry['rating']}/10")
        return 0
    PAGE.write_text(updated)
    print(f"[gemini-risk] rendered: {entry['as_of']} · {entry['rating']}/10")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
