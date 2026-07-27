#!/usr/bin/env python3
"""Render the latest Meta Risk API receipt into its public Trading Desk page."""
from __future__ import annotations

import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "trading" / "meta-risk.json"
PAGE = ROOT / "trading" / "meta-risk" / "index.html"
START = "<!-- AUTO:META_RISK:START -->"
END = "<!-- AUTO:META_RISK:END -->"


def validate(payload: dict) -> dict:
    if payload.get("schema_version") != 1:
        raise ValueError("meta-risk schema_version must be 1")
    if payload.get("model") != "Meta AI muse-spark-1.1":
        raise ValueError("meta-risk model must be Meta AI muse-spark-1.1")
    entries = payload.get("entries") or []
    if not entries:
        raise ValueError("meta-risk requires at least one entry")
    entry = entries[0]
    if entry.get("status") != "completed" or entry.get("http_status") != 200:
        raise ValueError("meta-risk requires a completed HTTP 200 provider receipt")
    if entry.get("rating") is not None:
        raise ValueError("meta-risk rating must stay null unless Meta supplies one")
    if not entry.get("search_queries") or not entry.get("verbatim_response"):
        raise ValueError("meta-risk requires search queries and the verbatim response")
    return entry


def render_response(markdown: str) -> str:
    def inline(value: str) -> str:
        escaped = html.escape(value, quote=True)
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)

    blocks: list[str] = []
    list_items: list[str] = []

    def flush_list() -> None:
        if list_items:
            blocks.append("<ul>" + "".join(f"<li>{item}</li>" for item in list_items) + "</ul>")
            list_items.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line:
            flush_list()
        elif line.startswith("### "):
            flush_list()
            blocks.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("* "):
            list_items.append(inline(line[2:]))
        else:
            flush_list()
            blocks.append(f"<p>{inline(line)}</p>")
    flush_list()
    return "".join(blocks)


def render(payload: dict, entry: dict) -> str:
    esc = lambda value: html.escape(str(value), quote=True)
    queries = "".join(f"<li>{esc(query)}</li>" for query in entry["search_queries"])
    sources = "".join(
        f'<li><a href="{esc(source["url"])}" rel="noopener">{esc(source["title"])}</a></li>'
        for source in entry["sources"]
    )
    usage = entry["usage"]
    return f'''<article class="meta-risk-report" data-model="{esc(payload["model"])}">
  <header class="meta-risk-verdict">
    <div><span class="meta-risk-kicker">Current market stance</span><h2>{esc(entry["stance"])}</h2><p>{esc(entry["summary"])}</p></div>
    <div class="meta-risk-score"><strong>—</strong><span>/ 10</span><small>Meta gave no numeric score</small></div>
  </header>
  <p class="meta-risk-dates">Assessment {esc(entry["as_of"])} · search-grounded API response · model {esc(payload["model"])}</p>
  <section class="meta-risk-prompt"><span>Exact prompt</span><p>{esc(payload["prompt"])}</p></section>
  <details class="meta-risk-exact" open><summary>Exact model response</summary><div class="meta-risk-response">{render_response(entry["verbatim_response"])}</div></details>
  <div class="meta-risk-grid">
    <section><h2>Searches Meta ran</h2><ol>{queries}</ol></section>
    <section><h2>Durable citations attached</h2><ul>{sources}</ul><p>Meta attached five citation spans pointing to {len(entry["sources"])} unique URLs.</p></section>
  </div>
  <details class="trading-method"><summary>Provider receipt</summary><p>HTTP {entry["http_status"]} · {esc(entry["status"])} · response {esc(entry["response_id"])} · {usage["input_tokens"]:,} input tokens · {usage["output_tokens"]:,} output tokens · {usage["reasoning_tokens"]:,} reasoning tokens · {usage["total_tokens"]:,} total tokens. Public structured receipt: <a href="/trading/meta-risk.json">/trading/meta-risk.json</a>.</p></details>
  <section class="meta-risk-integrity"><span>Integrity note</span><p>{esc(entry["integrity_note"])}</p></section>
</article>'''


def main() -> int:
    payload = json.loads(DATA.read_text())
    entry = validate(payload)
    page = PAGE.read_text()
    if START not in page or END not in page:
        raise ValueError("meta-risk page is missing AUTO markers")
    block = f"{START}\n{render(payload, entry)}\n{END}"
    updated = re.sub(re.escape(START) + r".*?" + re.escape(END), block, page, count=1, flags=re.S)
    if updated == page:
        print(f"[meta-risk] already current: {entry['as_of']} · {entry['stance']}")
        return 0
    PAGE.write_text(updated)
    print(f"[meta-risk] rendered: {entry['as_of']} · {entry['stance']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
