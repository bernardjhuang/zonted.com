#!/usr/bin/env python3
"""Validate trading/horizon.json and sync it into the Horizon tab."""
from __future__ import annotations

import hashlib
import html
import json
import pathlib
import re
from urllib.parse import urlparse

from sync_trading_desk import sync_sections

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "trading" / "classic" / "index.html"
DATA = ROOT / "trading" / "horizon.json"
SCRIPT = ROOT / "js" / "trading-horizon.js"
START = "<!-- AUTO:HORIZON:START -->"
END = "<!-- AUTO:HORIZON:END -->"

REQUIRED_ROOT = {
    "as_of",
    "scope",
    "cadence",
    "summary",
    "agencies_scanned",
    "theses",
    "context",
    "methodology",
}
REQUIRED_THESIS = {
    "id",
    "title",
    "agency",
    "niche",
    "primary_tickers",
    "secondary_tickers",
    "announcement_date",
    "next_decision",
    "date_status",
    "narrative_stage",
    "priority",
    "weeks_remaining_estimate",
    "confidence",
    "what_happened",
    "transmission",
    "company_exposure",
    "asymmetry",
    "catalyst_chain",
    "second_order",
    "invalidation",
    "watch",
    "sources",
}
ALLOWED_STAGES = {"early", "building", "crowded"}
ALLOWED_PRIORITIES = {"P0", "P1", "P2"}
ALLOWED_DATE_STATUS = {"confirmed", "window", "process", "imminent"}


def esc(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def valid_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate(data: dict) -> None:
    missing = REQUIRED_ROOT - data.keys()
    if missing:
        raise ValueError(f"missing horizon fields: {sorted(missing)}")
    if data["scope"] != "cross-agency-horizon-theses":
        raise ValueError("horizon scope must be cross-agency-horizon-theses")
    if "06:30" not in str(data["cadence"]):
        raise ValueError("horizon cadence must mention 06:30")
    if not isinstance(data["agencies_scanned"], list) or len(data["agencies_scanned"]) < 5:
        raise ValueError("agencies_scanned must list at least five agencies")
    if not isinstance(data["theses"], list) or not data["theses"]:
        raise ValueError("theses must be a non-empty list")
    if len(data["theses"]) > 10:
        raise ValueError("horizon must rank at most ten theses")

    ids: set[str] = set()
    agencies: set[str] = set()
    for thesis in data["theses"]:
        absent = REQUIRED_THESIS - thesis.keys()
        if absent:
            raise ValueError(f"thesis missing fields: {sorted(absent)}")
        if thesis["id"] in ids:
            raise ValueError(f"duplicate thesis id: {thesis['id']}")
        ids.add(thesis["id"])
        if not thesis["primary_tickers"]:
            raise ValueError(f"thesis has no primary tickers: {thesis['id']}")
        if thesis["narrative_stage"] not in ALLOWED_STAGES:
            raise ValueError(f"invalid narrative_stage for {thesis['id']}")
        if thesis["priority"] not in ALLOWED_PRIORITIES:
            raise ValueError(f"invalid priority for {thesis['id']}")
        if thesis["date_status"] not in ALLOWED_DATE_STATUS:
            raise ValueError(f"invalid date_status for {thesis['id']}")
        confidence = float(thesis["confidence"])
        if not 0 <= confidence <= 1:
            raise ValueError(f"invalid confidence for {thesis['id']}")
        if int(thesis["weeks_remaining_estimate"]) < 0:
            raise ValueError(f"invalid weeks_remaining_estimate for {thesis['id']}")
        if not thesis["catalyst_chain"] or len(thesis["catalyst_chain"]) < 3:
            raise ValueError(f"catalyst_chain needs at least three steps: {thesis['id']}")
        if not thesis["watch"]:
            raise ValueError(f"thesis has no watch items: {thesis['id']}")
        if not thesis["sources"]:
            raise ValueError(f"thesis has no sources: {thesis['id']}")
        for source in thesis["sources"]:
            if not valid_url(source.get("url", "")):
                raise ValueError(f"invalid source URL for {thesis['id']}")
        agencies.add(str(thesis["agency"]).strip())

    if len(agencies) < 4:
        raise ValueError("horizon must cover at least four agencies")
    if sum(1 for thesis in data["theses"] if thesis["agency"] == "FDA") > 4:
        raise ValueError("FDA may not occupy more than four theses")
    if sum(1 for thesis in data["theses"] if thesis["narrative_stage"] == "early") < 1:
        raise ValueError("horizon needs at least one early-stage thesis")


def render_panel(data: dict) -> str:
    data_version = hashlib.sha256(DATA.read_bytes()).hexdigest()[:12]
    return f'''            <section class="trading-panel brief-panel" id="horizon-panel" role="tabpanel" tabindex="0" aria-labelledby="horizon-tab" hidden>
                <div id="horizon-shell" data-url="/trading/horizon.json?v={data_version}">
                    <p class="trading-note">Loading the latest cross-agency horizon scan…</p>
                </div>
            </section>'''


def ensure_tab(page: str) -> str:
    if 'id="horizon-tab"' in page:
        return page
    gpt_button = '<button class="trading-tab" id="gpt-brief-tab" type="button" role="tab" aria-selected="false" aria-controls="gpt-brief-panel">GPT brief</button>'
    horizon_button = '<button class="trading-tab" id="horizon-tab" type="button" role="tab" aria-selected="false" aria-controls="horizon-panel">Horizon</button>'
    if gpt_button not in page:
        raise ValueError("GPT brief tab anchor not found")
    return page.replace(gpt_button, gpt_button + "\n                " + horizon_button, 1)


def ensure_markers(page: str) -> str:
    if START in page:
        return page
    gpt_end = "<!-- AUTO:GPT_BRIEF:END -->"
    if gpt_end not in page:
        raise ValueError("GPT brief panel marker not found")
    return page.replace(gpt_end, gpt_end + f"\n\n            {START}\n            {END}", 1)


def ensure_script(page: str) -> str:
    script_version = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()[:12]
    script_tag = f'<script src="/js/trading-horizon.js?v={script_version}"></script>'
    if "/js/trading-horizon.js?v=" in page:
        return re.sub(
            r'\s*<script src="/js/trading-horizon\.js\?v=[^"]+"></script>',
            f"\n    {script_tag}",
            page,
            count=1,
        )
    return page.replace("</body>", f"    {script_tag}\n</body>", 1)


def main() -> None:
    data = json.loads(DATA.read_text())
    validate(data)
    page = PAGE.read_text()
    page = ensure_tab(page)
    page = ensure_markers(page)
    page = ensure_script(page)

    panel = render_panel(data)
    new = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        f"{START}\n{panel}\n            {END}",
        page,
        count=1,
        flags=re.S,
    )
    page_changed = new != PAGE.read_text()
    if page_changed:
        PAGE.write_text(new)
    routed_changed = bool(sync_sections(["horizon"]))
    if not page_changed and not routed_changed:
        print(f"[horizon] already current: {len(data['theses'])} theses")
        return
    print(f"[horizon] rendered {len(data['theses'])} theses as of {data['as_of']}")


if __name__ == "__main__":
    main()
