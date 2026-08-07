#!/usr/bin/env python3
"""Append one dual-reviewed public entry and render the Autonomous journal."""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "trading" / "autonomous.json"
RENDERER_PATH = ROOT / "scripts" / "update-autonomous-journal.py"


def load_renderer():
    spec = importlib.util.spec_from_file_location("update_autonomous_journal", RENDERER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load autonomous renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def append_entry(existing: dict, incoming: dict, renderer) -> tuple[dict, bool]:
    if incoming.get("schema_version") != 1 or len(incoming.get("entries") or []) != 1:
        raise ValueError("incoming bundle must contain exactly one schema_version 1 entry")
    renderer.validate(incoming)
    renderer.validate(existing)
    entry = incoming["entries"][0]
    entry_id = entry["id"]
    matches = [row for row in existing["entries"] if row["id"] == entry_id]
    if matches:
        if matches[0] != entry:
            raise ValueError(f"entry {entry_id} already exists with different content")
        return existing, False
    combined = {"schema_version": 1, "entries": [entry, *existing["entries"]]}
    renderer.validate(combined)
    return combined, True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("entry", type=pathlib.Path, help="privacy-safe one-entry JSON bundle")
    parser.add_argument("--check-only", action="store_true", help="validate without modifying checked-in artifacts")
    args = parser.parse_args()
    renderer = load_renderer()
    incoming = json.loads(args.entry.read_text())
    existing = json.loads(DATA.read_text())
    combined, changed = append_entry(existing, incoming, renderer)
    if args.check_only:
        print(f"[autonomous-publish] valid · {incoming['entries'][0]['id']} · changed={str(changed).lower()}")
        return 0
    if changed:
        page = renderer.PAGE.read_text()
        updated, count = re.subn(
            re.escape(renderer.START) + r".*?" + re.escape(renderer.END),
            renderer.render(combined["entries"]),
            page,
            count=1,
            flags=re.S,
        )
        if count != 1:
            raise ValueError("autonomous journal render markers are missing")
        DATA.write_text(json.dumps(combined, indent=2, ensure_ascii=False) + "\n")
        renderer.PAGE.write_text(updated)
        print(f"[autonomous-publish] appended {incoming['entries'][0]['id']} · {len(combined['entries'])} total")
    else:
        print(f"[autonomous-publish] already current · {incoming['entries'][0]['id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
