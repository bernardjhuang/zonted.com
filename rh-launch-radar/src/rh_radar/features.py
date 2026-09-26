from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from rh_radar.config import DATA, ensure_data_dirs, load_config
from rh_radar.decode import decode_swap_amounts, topic_address
from rh_radar.rpc import credits_remaining, get_logs

LAUNCHES = DATA / "launches.jsonl"
FEATURES = DATA / "features" / "decision_features.jsonl"


def _estimate_block(first_block: int, first_ts: int, target_ts: int, block_time: float) -> int:
    delta = max(0, target_ts - first_ts)
    return first_block + int(delta / block_time)


def _swap_window_stats(
    pool: str,
    quote: str,
    token: str,
    from_block: int,
    to_block: int,
    swap_topic: str,
) -> dict[str, Any]:
    if to_block < from_block:
        return {
            "swaps": 0,
            "unique_traders": 0,
            "quote_volume_wei": 0,
            "buy_swaps": 0,
            "sell_swaps": 0,
        }
    logs = get_logs(pool, swap_topic, from_block, to_block)
    traders: set[str] = set()
    quote_volume = 0
    buys = sells = 0
    quote_is_token0 = int(quote, 16) < int(token, 16)
    for log in logs:
        sender = topic_address(log["topics"][1])
        recipient = topic_address(log["topics"][2])
        traders.add(sender)
        traders.add(recipient)
        amount0, amount1 = decode_swap_amounts(log["data"])
        quote_delta = amount0 if quote_is_token0 else amount1
        quote_volume += abs(quote_delta)
        # If quote enters the pool (positive quote amount for pool accounting in v3:
        # amount is delta for pool; positive means pool gained that token).
        if quote_delta > 0:
            buys += 1
        elif quote_delta < 0:
            sells += 1
    return {
        "swaps": len(logs),
        "unique_traders": len(traders),
        "quote_volume_wei": quote_volume,
        "buy_swaps": buys,
        "sell_swaps": sells,
    }


def build_creator_priors(rows: list[dict[str, Any]]) -> dict[str, list[int]]:
    by_creator: dict[str, list[int]] = defaultdict(list)
    for row in sorted(rows, key=lambda r: r["first_liq_block"]):
        by_creator[row["creator"]].append(row["first_liq_block"])
    return by_creator


def prior_launch_count(priors: dict[str, list[int]], creator: str, block: int) -> int:
    return sum(1 for b in priors.get(creator, []) if b < block)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build T+3/5/10/20m decision features for a launch sample")
    parser.add_argument("--limit", type=int, default=400, help="Newest N launches to feature (0=all)")
    parser.add_argument("--min-block", type=int, default=0)
    parser.add_argument("--offset", type=int, default=0, help="Skip this many newest before taking limit")
    parser.add_argument(
        "--era-prefix",
        type=str,
        default="pons",
        help="Only include mechanism_era starting with this prefix (empty = all). Default pons avoids v4 poolIds.",
    )
    parser.add_argument(
        "--only-offsets",
        type=str,
        default="",
        help="Comma-separated decision offsets in seconds (default: all configured)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Keep existing feature rows; skip launch_id+decision_offset already present",
    )
    args = parser.parse_args()
    ensure_data_dirs()
    cfg = load_config()
    block_time = float(cfg["approx_block_time_sec"])
    swap_topic = cfg["events"]["uniswap_v3_swap"]["topic0"]
    decision_offsets = list(cfg["decision_offsets_sec"])
    if args.only_offsets.strip():
        decision_offsets = [int(x) for x in args.only_offsets.split(",") if x.strip()]

    rows = [json.loads(line) for line in LAUNCHES.read_text().splitlines() if line.strip()]
    rows = [r for r in rows if r.get("first_liq_ts") and r["first_liq_block"] >= args.min_block]
    if args.era_prefix:
        rows = [r for r in rows if str(r.get("mechanism_era") or "").startswith(args.era_prefix)]
    rows.sort(key=lambda r: r["first_liq_block"])
    priors = build_creator_priors(rows)
    if args.limit:
        end = len(rows) - args.offset if args.offset else len(rows)
        start = max(0, end - args.limit)
        sample = rows[start:end]
    else:
        sample = rows
    print(f"[features] sample={len(sample)} total_stamped={len(rows)}")

    existing: list[dict[str, Any]] = []
    done: set[tuple[str, int]] = set()
    if args.resume and FEATURES.exists():
        for line in FEATURES.read_text().splitlines():
            if not line.strip():
                continue
            feat = json.loads(line)
            existing.append(feat)
            done.add((feat["launch_id"], int(feat["decision_offset_sec"])))
        print(f"[features] resume existing={len(existing)}")

    FEATURES.parent.mkdir(parents=True, exist_ok=True)
    tmp = FEATURES.with_suffix(".tmp")
    written = 0
    with tmp.open("w") as handle:
        for feat in existing:
            handle.write(json.dumps(feat, separators=(",", ":"), sort_keys=True) + "\n")
        for i, row in enumerate(sample):
            creator_prior = prior_launch_count(priors, row["creator"], row["first_liq_block"])
            for offset in decision_offsets:
                if (row["launch_id"], offset) in done:
                    continue
                decision_ts = int(row["first_liq_ts"]) + offset
                decision_block = _estimate_block(row["first_liq_block"], int(row["first_liq_ts"]), decision_ts, block_time)
                stats = _swap_window_stats(
                    row["pool"],
                    row["quote"],
                    row["token"],
                    row["first_liq_block"],
                    decision_block,
                    swap_topic,
                )
                feat = {
                    "launch_id": row["launch_id"],
                    "token": row["token"],
                    "pool": row["pool"],
                    "creator": row["creator"],
                    "factory_name": row["factory_name"],
                    "mechanism_era": row["mechanism_era"],
                    "first_liq_block": row["first_liq_block"],
                    "first_liq_ts": row["first_liq_ts"],
                    "decision_offset_sec": offset,
                    "decision_ts": decision_ts,
                    "decision_block": decision_block,
                    "observed_block": decision_block,
                    "available_at": decision_ts,
                    "msg_value_wei": row.get("msg_value_wei") or 0,
                    "creator_prior_launches": creator_prior,
                    "quote": row["quote"],
                    **{f"flow_{k}": v for k, v in stats.items()},
                }
                handle.write(json.dumps(feat, separators=(",", ":"), sort_keys=True) + "\n")
                written += 1
            if (i + 1) % 25 == 0:
                print(f"[features] {i+1}/{len(sample)} new_rows={written} credits={credits_remaining()}")
    tmp.replace(FEATURES)
    print(f"[done] wrote {written} new feature rows (kept {len(existing)}) -> {FEATURES} credits={credits_remaining()}")


if __name__ == "__main__":
    main()
