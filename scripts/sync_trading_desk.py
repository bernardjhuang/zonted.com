#!/usr/bin/env python3
"""Sync cron-owned classic dashboard regions into the routed trading desk pages.

The scheduled generators continue to own ``trading/classic/index.html`` and the
JSON chart assets. This bridge makes the routed production pages consume those
same generated regions so the new layout cannot drift after a cron refresh.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import pathlib
import re
import tempfile
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLASSIC = ROOT / "trading" / "classic" / "index.html"
DESK_SCRIPT = ROOT / "trading" / "desk.js"
BROKER_SCRIPT = ROOT / "js" / "trading-broker-light.js"
GPT_SCRIPT = ROOT / "js" / "trading-gpt-brief.js"
HORIZON_SCRIPT = ROOT / "js" / "trading-horizon.js"


@dataclass(frozen=True)
class Route:
    path: pathlib.Path
    title: str
    description: str
    regions: tuple[str, ...]
    scripts: tuple[pathlib.Path, ...] = ()


ROUTES = {
    "brief": Route(
        ROOT / "trading" / "brief" / "index.html",
        "Brief",
        "The generated trading brief, refreshed from the same source used by the scheduled classic dashboard.",
        ("BRIEF",),
    ),
    "gpt-brief": Route(
        ROOT / "trading" / "gpt-brief" / "index.html",
        "GPT brief",
        "The sector-diverse six-week catalyst radar, loaded from the latest scheduled GPT brief payload.",
        ("GPT_BRIEF",),
        (GPT_SCRIPT,),
    ),
    "horizon": Route(
        ROOT / "trading" / "horizon" / "index.html",
        "Horizon",
        "Cross-agency deep research on dated catalysts still early enough to own — FDA, DEA, CFTC, SEC, DOD, WHO, and the Federal Register.",
        ("HORIZON",),
        (HORIZON_SCRIPT,),
    ),
    "momentum": Route(
        ROOT / "trading" / "momentum" / "index.html",
        "Momentum",
        "The generated momentum scanner and chart universe from the latest completed market session.",
        ("SCAN",),
        (BROKER_SCRIPT,),
    ),
    "vwap": Route(
        ROOT / "trading" / "vwap" / "index.html",
        "VWAP",
        "US sectors, country ETFs, and crypto VWAPs refreshed together from the same after-close pipeline.",
        ("VWAP", "CRYPTO"),
        (BROKER_SCRIPT,),
    ),
    "performance": Route(
        ROOT / "trading" / "performance" / "index.html",
        "Performance",
        "The quantity-free public performance panel from the latest portfolio refresh.",
        ("RESULTS",),
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
    script_tags = "\n".join(
        f'<script defer src="/{script.relative_to(ROOT).as_posix()}?v={digest(script)}"></script>'
        for script in route.scripts
    )
    body = f'''<!-- AUTO:ROUTED_TRADING:START -->
<div class="phead"><h1 id="{heading_id}">{route.title}</h1><p class="take">{route.description}</p><p class="meta">Cron-owned data · source of truth: /trading/classic/ and versioned JSON assets</p></div>
{panels}
<!-- AUTO:ROUTED_TRADING:END -->'''
    return page_prefix(target, classic) + body + "\n</div>\n" + (script_tags + "\n" if script_tags else "") + "</body>\n</html>\n"


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
