from __future__ import annotations

import argparse
import json
from pathlib import Path

from rh_radar.config import DATA, ensure_data_dirs, load_config
from rh_radar.rpc import cached_block_timestamp, credits_remaining

LAUNCHES = DATA / "launches.jsonl"
STAMPED = DATA / "launches.stamped.jsonl"


def build_anchors(blocks: list[int], every: int) -> dict[int, int]:
    if not blocks:
        return {}
    lo, hi = min(blocks), max(blocks)
    anchors = {lo, hi}
    for block in range(lo, hi + 1, every):
        anchors.add(block)
    # Also pin exact blocks for endpoints of each launch set sparsely.
    out: dict[int, int] = {}
    for block in sorted(anchors):
        out[block] = cached_block_timestamp(block)
        if len(out) % 25 == 0:
            print(f"[stamp] anchors={len(out)} credits={credits_remaining()}")
    return out


def interpolate_ts(block: int, anchors: dict[int, int]) -> int:
    if block in anchors:
        return anchors[block]
    keys = sorted(anchors)
    # binary search neighbors
    lo, hi = keys[0], keys[-1]
    if block <= lo:
        return anchors[lo]
    if block >= hi:
        return anchors[hi]
    left = keys[0]
    right = keys[-1]
    for key in keys:
        if key <= block:
            left = key
        if key >= block:
            right = key
            break
    if left == right:
        return anchors[left]
    t0, t1 = anchors[left], anchors[right]
    return int(t0 + (t1 - t0) * (block - left) / (right - left))


def main() -> None:
    parser = argparse.ArgumentParser(description="Stamp launch blocks with timestamps via anchor interpolation")
    parser.add_argument("--every", type=int, default=20_000, help="Anchor spacing in blocks")
    parser.add_argument("--exact-sample", type=int, default=0, help="If >0, exact-stamp this many newest launches")
    args = parser.parse_args()
    ensure_data_dirs()
    if not LAUNCHES.exists():
        raise SystemExit(f"missing {LAUNCHES}")

    rows = [json.loads(line) for line in LAUNCHES.read_text().splitlines() if line.strip()]
    rows.sort(key=lambda r: (r["first_liq_block"], r["log_index"]))
    blocks = [r["first_liq_block"] for r in rows]
    print(f"[stamp] launches={len(rows)} block_range={min(blocks)}-{max(blocks)}")
    anchors = build_anchors(blocks, args.every)

    if args.exact_sample:
        sample = rows[-args.exact_sample :]
        for row in sample:
            anchors[row["first_liq_block"]] = cached_block_timestamp(row["first_liq_block"])

    tmp = STAMPED.with_suffix(".tmp")
    with tmp.open("w") as handle:
        for row in rows:
            ts = interpolate_ts(row["first_liq_block"], anchors)
            row["first_liq_ts"] = ts
            row["available_at"] = ts
            row["ts_method"] = "exact" if row["first_liq_block"] in anchors and args.exact_sample and row in rows[-args.exact_sample :] else "anchor_interp"
            handle.write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")
    tmp.replace(STAMPED)
    # Replace launches.jsonl with stamped version for downstream convenience.
    STAMPED.replace(LAUNCHES)
    print(f"[done] stamped {len(rows)} launches; credits={credits_remaining()}")


if __name__ == "__main__":
    main()
