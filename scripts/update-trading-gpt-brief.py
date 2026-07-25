#!/usr/bin/env python3
"""Render trading/gpt-brief.json into the GPT brief tab."""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import pathlib
import re
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "trading" / "index.html"
DATA = ROOT / "trading" / "gpt-brief.json"
SCRIPT = ROOT / "js" / "trading-gpt-brief.js"
START = "<!-- AUTO:GPT_BRIEF:START -->"
END = "<!-- AUTO:GPT_BRIEF:END -->"


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate(data: dict) -> None:
    required = {"as_of", "scope", "window_start", "window_end", "summary", "universe", "events", "context", "methodology"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"missing GPT brief fields: {sorted(missing)}")
    if not isinstance(data["universe"], list) or not data["universe"]:
        raise ValueError("universe must be a non-empty list")
    if not isinstance(data["events"], list) or not data["events"]:
        raise ValueError("events must be a non-empty list")
    if data["scope"] != "market-wide":
        raise ValueError("GPT brief scope must be market-wide")
    window_start = dt.date.fromisoformat(data["window_start"])
    window_end = dt.date.fromisoformat(data["window_end"])
    if not 35 <= (window_end - window_start).days <= 42:
        raise ValueError("GPT brief window must span 5–6 weeks")
    if len(data["events"]) > 8:
        raise ValueError("GPT brief must rank at most eight events")
    ids: set[str] = set()
    for event in data["events"]:
        event_required = {
            "id", "date", "date_status", "horizon", "tier", "category", "tickers",
            "title", "confidence", "implication", "direction", "magnitude", "action",
            "invalidation", "watch", "sources",
        }
        absent = event_required - event.keys()
        if absent:
            raise ValueError(f"event missing fields: {sorted(absent)}")
        if event["id"] in ids:
            raise ValueError(f"duplicate event id: {event['id']}")
        ids.add(event["id"])
        confidence = float(event["confidence"])
        if not 0 <= confidence <= 1:
            raise ValueError(f"invalid confidence for {event['id']}")
        if not event["sources"]:
            raise ValueError(f"event has no sources: {event['id']}")
        for source in event["sources"]:
            if not valid_url(source.get("url", "")):
                raise ValueError(f"invalid source URL for {event['id']}")


def render_panel(data: dict) -> str:
    data_version = hashlib.sha256(DATA.read_bytes()).hexdigest()[:12]
    return f'''            <section class="trading-panel brief-panel" id="gpt-brief-panel" role="tabpanel" tabindex="0" aria-labelledby="gpt-brief-tab" hidden>
                <div id="gpt-brief-shell" data-url="/trading/gpt-brief.json?v={data_version}">
                    <p class="trading-note">Loading the latest future catalyst scan…</p>
                </div>
            </section>'''


def main() -> None:
    data = json.loads(DATA.read_text())
    validate(data)
    page = PAGE.read_text()

    if 'id="gpt-brief-tab"' not in page:
        brief_button = '<button class="trading-tab" id="brief-tab" type="button" role="tab" aria-selected="false" aria-controls="brief-panel">Brief</button>'
        gpt_button = '<button class="trading-tab" id="gpt-brief-tab" type="button" role="tab" aria-selected="false" aria-controls="gpt-brief-panel">GPT brief</button>'
        if brief_button not in page:
            raise ValueError("Brief tab anchor not found")
        page = page.replace(brief_button, brief_button + "\n                " + gpt_button, 1)

    if START not in page:
        brief_end = "<!-- AUTO:BRIEF:END -->"
        if brief_end not in page:
            raise ValueError("Brief panel marker not found")
        page = page.replace(brief_end, brief_end + f"\n\n            {START}\n            {END}", 1)

    script_version = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()[:12]
    script_tag = f'<script src="/js/trading-gpt-brief.js?v={script_version}"></script>'
    page = re.sub(
        r'\s*<script src="/js/trading-gpt-brief\.js\?v=[^"]+"></script>',
        f"\n    {script_tag}",
        page,
        count=1,
    ) if "/js/trading-gpt-brief.js?v=" in page else page.replace("</body>", f"    {script_tag}\n</body>", 1)

    panel = render_panel(data)
    new = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        f"{START}\n{panel}\n            {END}",
        page,
        count=1,
        flags=re.S,
    )
    if new == PAGE.read_text():
        print(f"[gpt-brief] already current: {len(data['events'])} events")
        return
    PAGE.write_text(new)
    print(f"[gpt-brief] rendered {len(data['events'])} events as of {data['as_of']}")


if __name__ == "__main__":
    main()
