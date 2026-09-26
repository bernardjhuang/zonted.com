#!/usr/bin/env python3
"""Stamp only launches missing first_liq_ts (e.g. newly harvested InstantLaunch)."""
from __future__ import annotations

import json
from pathlib import Path

from rh_radar.config import DATA, ensure_data_dirs
from rh_radar.rpc import cached_block_timestamp, credits_remaining
from rh_radar.stamp import build_anchors, interpolate_ts

LAUNCHES = DATA / "launches.jsonl"


def main() -> None:
    ensure_data_dirs()
    rows = [json.loads(line) for line in LAUNCHES.read_text().splitlines() if line.strip()]
    need = [r for r in rows if not r.get("first_liq_ts")]
    print(f"[stamp-missing] total={len(rows)} need_stamp={len(need)}")
    if not need:
        return
    blocks = [r["first_liq_block"] for r in need]
    anchors = build_anchors(blocks, every=50_000)
    need_sorted = sorted(need, key=lambda r: r["first_liq_block"])
    exact_tail = need_sorted[-200:]
    exact_blocks = {r["first_liq_block"] for r in exact_tail}
    for row in exact_tail:
        anchors[row["first_liq_block"]] = cached_block_timestamp(row["first_liq_block"])
    by_id = {r["launch_id"]: r for r in rows}
    for row in need:
        ts = interpolate_ts(row["first_liq_block"], anchors)
        row["first_liq_ts"] = ts
        row["available_at"] = ts
        row["ts_method"] = "exact" if row["first_liq_block"] in exact_blocks else "anchor_interp"
        by_id[row["launch_id"]] = row
    out = sorted(by_id.values(), key=lambda r: (r["first_liq_block"], r.get("log_index") or 0))
    tmp = LAUNCHES.with_suffix(".tmp")
    with tmp.open("w") as handle:
        for row in out:
            handle.write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")
    tmp.replace(LAUNCHES)
    stamped = sum(1 for r in out if r.get("first_liq_ts"))
    print(f"[done] stamped_new={len(need)} stamped_total={stamped} credits={credits_remaining()}")


if __name__ == "__main__":
    main()
