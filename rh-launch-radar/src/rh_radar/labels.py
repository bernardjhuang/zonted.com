from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from rh_radar.config import DATA, ensure_data_dirs, load_config
from rh_radar.decode import decode_swap_amounts, topic_address
from rh_radar.rpc import credits_remaining, get_logs

LAUNCHES = DATA / "launches.jsonl"
FEATURES = DATA / "features" / "decision_features.jsonl"
LABELS = DATA / "labels" / "outcomes.jsonl"
THRESHOLDS = DATA / "labels" / "thresholds.json"


def _estimate_block(first_block: int, first_ts: int, target_ts: int, block_time: float) -> int:
    return first_block + int(max(0, target_ts - first_ts) / block_time)


def horizon_stats(pool: str, quote: str, token: str, start_block: int, end_block: int, swap_topic: str) -> dict[str, Any]:
    if end_block < start_block:
        return {"swaps": 0, "unique_traders": 0, "quote_volume_wei": 0}
    logs = get_logs(pool, swap_topic, start_block, end_block)
    traders: set[str] = set()
    quote_volume = 0
    quote_is_token0 = int(quote, 16) < int(token, 16)
    for log in logs:
        traders.add(topic_address(log["topics"][1]))
        traders.add(topic_address(log["topics"][2]))
        amount0, amount1 = decode_swap_amounts(log["data"])
        quote_delta = amount0 if quote_is_token0 else amount1
        quote_volume += abs(quote_delta)
    return {"swaps": len(logs), "unique_traders": len(traders), "quote_volume_wei": quote_volume}


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return float(xs[0])
    k = (len(xs) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(xs[int(k)])
    return float(xs[f] * (c - k) + xs[c] * (k - f))


def main() -> None:
    parser = argparse.ArgumentParser(description="Label launch outcomes at frozen horizons (swap-flow proxies for M1)")
    parser.add_argument("--limit", type=int, default=400)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument(
        "--era-prefix",
        type=str,
        default="pons",
        help="Only include mechanism_era starting with this prefix (empty = all). Default pons avoids v4 poolIds.",
    )
    parser.add_argument(
        "--only-horizons",
        type=str,
        default="",
        help="Comma-separated outcome horizons in seconds (default: all configured)",
    )
    args = parser.parse_args()
    ensure_data_dirs()
    cfg = load_config()
    block_time = float(cfg["approx_block_time_sec"])
    swap_topic = cfg["events"]["uniswap_v3_swap"]["topic0"]
    horizons = list(cfg["outcome_horizons_sec"])
    if args.only_horizons.strip():
        horizons = [int(x) for x in args.only_horizons.split(",") if x.strip()]
    if 86400 not in horizons:
        horizons.append(86400)

    launches = [json.loads(line) for line in LAUNCHES.read_text().splitlines() if line.strip()]
    launches = [r for r in launches if r.get("first_liq_ts")]
    if args.era_prefix:
        launches = [r for r in launches if str(r.get("mechanism_era") or "").startswith(args.era_prefix)]
    launches.sort(key=lambda r: r["first_liq_block"])
    if args.limit:
        end = len(launches) - args.offset if args.offset else len(launches)
        start = max(0, end - args.limit)
        sample = launches[start:end]
    else:
        sample = launches

    # Need enough post-launch history for 24h label at minimum.
    now_ts = max(r["first_liq_ts"] for r in launches) if launches else 0
    sample = [r for r in sample if r["first_liq_ts"] + 86400 <= now_ts]
    print(f"[labels] era_prefix={args.era_prefix!r} sample_with_24h_history={len(sample)}")

    LABELS.parent.mkdir(parents=True, exist_ok=True)
    tmp = LABELS.with_suffix(".tmp")
    rows_out: list[dict[str, Any]] = []
    with tmp.open("w") as handle:
        for i, row in enumerate(sample):
            out: dict[str, Any] = {
                "launch_id": row["launch_id"],
                "token": row["token"],
                "pool": row["pool"],
                "mechanism_era": row["mechanism_era"],
                "factory_name": row["factory_name"],
                "first_liq_block": row["first_liq_block"],
                "first_liq_ts": row["first_liq_ts"],
                "threshold_version": "m0-proxy-v1",
            }
            for h in horizons:
                end_ts = int(row["first_liq_ts"]) + h
                end_block = _estimate_block(row["first_liq_block"], int(row["first_liq_ts"]), end_ts, block_time)
                stats = horizon_stats(row["pool"], row["quote"], row["token"], row["first_liq_block"], end_block, swap_topic)
                out[f"h{h}_swaps"] = stats["swaps"]
                out[f"h{h}_unique_traders"] = stats["unique_traders"]
                out[f"h{h}_quote_volume_wei"] = stats["quote_volume_wei"]
            handle.write(json.dumps(out, separators=(",", ":"), sort_keys=True) + "\n")
            rows_out.append(out)
            if (i + 1) % 25 == 0:
                print(f"[labels] {i+1}/{len(sample)} credits={credits_remaining()}")
    tmp.replace(LABELS)

    # Freeze thresholds from distribution of 24h quote volume / unique traders.
    vol = [float(r["h86400_quote_volume_wei"]) for r in rows_out]
    traders = [float(r["h86400_unique_traders"]) for r in rows_out]
    thresholds = {
        "threshold_version": "m0-proxy-v1",
        "n": len(rows_out),
        "h24_quote_volume_wei": {
            "p50": percentile(vol, 0.50),
            "p80": percentile(vol, 0.80),
            "p90": percentile(vol, 0.90),
            "p95": percentile(vol, 0.95),
        },
        "h24_unique_traders": {
            "p50": percentile(traders, 0.50),
            "p80": percentile(traders, 0.80),
            "p90": percentile(traders, 0.90),
            "p95": percentile(traders, 0.95),
        },
        "notes": (
            "Proxy labels pending executable depth simulation. "
            "high_value_proxy = h24 quote volume >= p90 AND h24 unique traders >= p80."
        ),
    }
    # Attach boolean labels
    vol_cut = thresholds["h24_quote_volume_wei"]["p90"]
    trader_cut = thresholds["h24_unique_traders"]["p80"]
    final_tmp = LABELS.with_suffix(".labeled.tmp")
    with LABELS.open() as src, final_tmp.open("w") as dst:
        for line in src:
            row = json.loads(line)
            row["high_value_proxy"] = (
                row["h86400_quote_volume_wei"] >= vol_cut and row["h86400_unique_traders"] >= trader_cut
            )
            row["volume_p90"] = row["h86400_quote_volume_wei"] >= vol_cut
            row["breadth_p80"] = row["h86400_unique_traders"] >= trader_cut
            dst.write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")
    final_tmp.replace(LABELS)
    THRESHOLDS.write_text(json.dumps(thresholds, indent=2, sort_keys=True))
    n_pos = sum(1 for r in rows_out if r["h86400_quote_volume_wei"] >= vol_cut and r["h86400_unique_traders"] >= trader_cut)
    print(f"[done] labels={len(rows_out)} high_value_proxy={n_pos} thresholds -> {THRESHOLDS}")
    print(json.dumps(thresholds, indent=2))


if __name__ == "__main__":
    main()
