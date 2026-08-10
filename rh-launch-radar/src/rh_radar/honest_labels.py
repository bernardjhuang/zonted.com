"""Honest executable labels: $250 round-trip + measured rug flags.

Primary continuous label: rt_log_return_250 = log(quote_out / quote_in) for a
$250 notional entered at T+10m and exited at T+24h via single-tick v3 math.

Binary executable_winner_250 (provisional freeze from spec §3× band):
  not rug AND exit impact ≤15% (gross_multiple / mark_multiple proxy via
  exit_recovery_vs_entry ≥ 0.0 handled separately) AND gross_multiple ≥ 3.0
  AND a $250-equivalent sell at 24h recovers ≥ 85% of entry notional.

Rug (binary, measured at checkpoints):
  sell-path recovery < 0.5, mark ≤ −90% from T+10m, or quote TVL < $100.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from rh_radar.config import DATA, ensure_data_dirs, load_config
from rh_radar.pool_math import (
    mark_quote_per_token,
    quote_side_tvl_wei,
    read_v3_pool_state,
    round_trip_quote,
    simulate_buy_token_out,
    simulate_sell_quote_out,
)
from rh_radar.rpc import credits_remaining, rest_get

LAUNCHES = DATA / "launches.jsonl"
HONEST = DATA / "labels" / "honest_outcomes.jsonl"
THRESHOLDS = DATA / "labels" / "honest_thresholds.json"

# Checkpoints after first liquidity (seconds). Hourly full grid is too expensive;
# 1h / 6h / 24h covers early drain + late rugs; 24h state is reused as exit.
RUG_CHECKPOINTS_SEC = (3600, 21600, 86400)
ENTRY_OFFSET_SEC = 600
EXIT_OFFSET_SEC = 86400
NOTIONAL_USD = 250.0
WIN_MULTIPLE = 3.0
EXIT_MIN_RECOVERY = 0.85  # ≤15% round-trip impact vs entry notional
RUG_SELL_RECOVERY = 0.5
RUG_MARK_DRAWDOWN = 0.10  # price ≤ 10% of entry mark
RUG_TVL_USD = 100.0


def _estimate_block(first_block: int, first_ts: int, target_ts: int, block_time: float) -> int:
    return first_block + int(max(0, target_ts - first_ts) / block_time)


def _quote_in_wei(quote: str, cfg: dict[str, Any], eth_usd: float, notional_usd: float) -> int:
    if quote.lower() == cfg["tokens"]["weth"].lower():
        return int((notional_usd / eth_usd) * 1e18)
    if quote.lower() == cfg["tokens"]["usdg"].lower():
        return int(notional_usd * 1e6)
    return int((notional_usd / eth_usd) * 1e18)


def _quote_usd(quote: str, amount_wei: float | int, cfg: dict[str, Any], eth_usd: float) -> float:
    if quote.lower() == cfg["tokens"]["weth"].lower():
        return float(amount_wei) / 1e18 * eth_usd
    if quote.lower() == cfg["tokens"]["usdg"].lower():
        return float(amount_wei) / 1e6
    return float(amount_wei) / 1e18 * eth_usd


def label_one(
    row: dict[str, Any],
    cfg: dict[str, Any],
    *,
    eth_usd: float,
    block_time: float,
    checkpoints_sec: tuple[int, ...] = RUG_CHECKPOINTS_SEC,
    exit_offset_sec: int = EXIT_OFFSET_SEC,
) -> dict[str, Any]:
    quote = row["quote"]
    token = row["token"]
    pool = row["pool"]
    first_block = int(row["first_liq_block"])
    first_ts = int(row["first_liq_ts"])
    quote_in = _quote_in_wei(quote, cfg, eth_usd, NOTIONAL_USD)

    entry_ts = first_ts + ENTRY_OFFSET_SEC
    exit_ts = first_ts + exit_offset_sec
    entry_block = _estimate_block(first_block, first_ts, entry_ts, block_time)
    exit_block = _estimate_block(first_block, first_ts, exit_ts, block_time)

    out: dict[str, Any] = {
        "launch_id": row["launch_id"],
        "token": token,
        "pool": pool,
        "quote": quote,
        "mechanism_era": row.get("mechanism_era"),
        "factory_name": row.get("factory_name"),
        "first_liq_block": first_block,
        "first_liq_ts": first_ts,
        "entry_offset_sec": ENTRY_OFFSET_SEC,
        "exit_offset_sec": exit_offset_sec,
        "entry_block": entry_block,
        "exit_block": exit_block,
        "notional_usd": NOTIONAL_USD,
        "eth_usd": eth_usd,
        "threshold_version": "honest-v1" if exit_offset_sec >= EXIT_OFFSET_SEC else "honest-v1-fast1h",
        "quote_in_wei": quote_in,
        "entry_ok": False,
        "exit_ok": False,
        "token_bought_wei": 0,
        "quote_out_wei": 0,
        "gross_multiple": 0.0,
        "rt_log_return_250": None,
        "entry_mark": None,
        "exit_mark": None,
        "mark_multiple": None,
        "rug": False,
        "rug_reasons": [],
        "rug_checkpoints": [],
        "executable_exit": False,
        "executable_winner_250": False,
        "available_at": exit_ts,
        "observed_block": exit_block,
    }

    try:
        entry_state = read_v3_pool_state(pool, entry_block)
    except Exception as exc:
        out["rug"] = True
        out["rug_reasons"].append(f"entry_state_error:{type(exc).__name__}")
        out["rt_log_return_250"] = float("-inf")
        return out

    entry_mark = mark_quote_per_token(entry_state, quote, token)
    out["entry_mark"] = entry_mark
    try:
        entry_tvl = quote_side_tvl_wei(pool, quote, entry_block)
    except Exception:
        entry_tvl = 0
    out["entry_tvl_usd"] = _quote_usd(quote, entry_tvl, cfg, eth_usd)
    spend = min(quote_in, max(0, int(entry_tvl)))
    token_inv = simulate_buy_token_out(entry_state, quote, token, spend) if spend else 0
    if token_inv <= 0 or spend < quote_in:
        out["rug_reasons"].append(
            f"entry_underfilled:spend_usd={_quote_usd(quote, spend, cfg, eth_usd):.2f}<{NOTIONAL_USD}"
        )
        if token_inv <= 0 or out["entry_tvl_usd"] < RUG_TVL_USD:
            out["rug"] = True
            out["rug_reasons"].append("entry_buy_zero_or_dust_tvl")
            out["rt_log_return_250"] = float("-inf")
            return out
    out["entry_ok"] = True
    out["token_bought_wei"] = int(token_inv)
    out["quote_spent_wei"] = int(spend)

    exit_state = None
    exit_tvl = 0
    for h in checkpoints_sec:
        block = _estimate_block(first_block, first_ts, first_ts + h, block_time)
        cp: dict[str, Any] = {"horizon_sec": h, "block": block}
        try:
            state = read_v3_pool_state(pool, block)
            mark = mark_quote_per_token(state, quote, token)
            tvl = quote_side_tvl_wei(pool, quote, block)
            tvl_usd = _quote_usd(quote, tvl, cfg, eth_usd)
            sell_out = min(
                int(simulate_sell_quote_out(state, quote, token, token_inv)),
                max(0, int(tvl)),
            )
            recovery = (sell_out / quote_in) if quote_in else 0.0
            cp.update({"mark": mark, "tvl_usd": tvl_usd, "sell_recovery_vs_entry": recovery})
            reasons = []
            if recovery < RUG_SELL_RECOVERY:
                reasons.append(f"sell_recovery:{recovery:.3f}<{RUG_SELL_RECOVERY}")
            if entry_mark > 0 and mark <= entry_mark * RUG_MARK_DRAWDOWN:
                reasons.append(f"mark_drawdown:{mark:.6g}<={entry_mark * RUG_MARK_DRAWDOWN:.6g}")
            # Dust TVL alone is not a rug if sell still clears ≥50%; depth failure shows up in recovery.
            cp["rug_reasons"] = reasons
            if reasons:
                out["rug"] = True
                out["rug_reasons"].extend([f"h{h}:{r}" for r in reasons])
            if h == exit_offset_sec:
                exit_state = state
                exit_tvl = tvl
        except Exception as exc:
            cp["error"] = type(exc).__name__
            out["rug"] = True
            out["rug_reasons"].append(f"h{h}:state_error:{type(exc).__name__}")
        out["rug_checkpoints"].append(cp)

    if exit_state is None:
        try:
            exit_state = read_v3_pool_state(pool, exit_block)
            exit_tvl = quote_side_tvl_wei(pool, quote, exit_block)
        except Exception as exc:
            out["rug"] = True
            out["rug_reasons"].append(f"exit_state_error:{type(exc).__name__}")
            out["rt_log_return_250"] = float("-inf")
            attach_short_horizon_exits(out)
            return out

    exit_mark = mark_quote_per_token(exit_state, quote, token)
    out["exit_mark"] = exit_mark
    out["exit_tvl_usd"] = _quote_usd(quote, exit_tvl, cfg, eth_usd)
    if entry_mark and entry_mark > 0:
        out["mark_multiple"] = exit_mark / entry_mark

    final = round_trip_quote(
        entry_state,
        exit_state,
        quote,
        token,
        quote_in,
        entry_quote_tvl_wei=entry_tvl,
        exit_quote_tvl_wei=exit_tvl,
    )
    out["quote_out_wei"] = final["quote_out_wei"]
    out["gross_multiple"] = final["gross_multiple"]
    out["exit_ok"] = final["quote_out_wei"] > 0
    if final["quote_in_wei"] > 0 and final["quote_out_wei"] > 0:
        out["rt_log_return_250"] = math.log(final["quote_out_wei"] / final["quote_in_wei"])
    else:
        out["rt_log_return_250"] = float("-inf")

    out["executable_exit"] = bool(final["gross_multiple"] >= EXIT_MIN_RECOVERY)
    # Hold-to-exit winner only meaningful on the full 24h exit path.
    out["executable_winner_250"] = bool(
        exit_offset_sec >= EXIT_OFFSET_SEC
        and (not out["rug"])
        and out["entry_ok"]
        and spend >= quote_in
        and out["executable_exit"]
        and final["gross_multiple"] >= WIN_MULTIPLE
    )
    attach_short_horizon_exits(out)
    return out


def attach_short_horizon_exits(row: dict[str, Any]) -> dict[str, Any]:
    """Derive exit@1h / exit@6h fields from rug_checkpoints (no extra RPC).

    At checkpoint h, sell_recovery_vs_entry is the gross multiple of selling the
    T+10m token inventory — the short-horizon paper-exit label.
    """
    by_h = {
        int(cp["horizon_sec"]): cp
        for cp in (row.get("rug_checkpoints") or [])
        if isinstance(cp, dict) and cp.get("horizon_sec") is not None
    }
    for h, suffix in ((3600, "1h"), (21600, "6h")):
        cp = by_h.get(h)
        g = None
        if cp is not None and isinstance(cp.get("sell_recovery_vs_entry"), (int, float)):
            g = float(cp["sell_recovery_vs_entry"])
        row[f"gross_multiple_{suffix}"] = g
        row[f"rug_{suffix}"] = bool(cp and (cp.get("rug_reasons") or []))
        row[f"executable_exit_{suffix}"] = bool(g is not None and g >= EXIT_MIN_RECOVERY)
        row[f"executable_winner_250_{suffix}"] = bool(
            g is not None
            and g >= WIN_MULTIPLE
            and not row[f"rug_{suffix}"]
            and bool(row.get("entry_ok"))
        )
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description="Build honest $250 RT + rug labels")
    parser.add_argument("--limit", type=int, default=800)
    parser.add_argument("--offset", type=int, default=1726)
    parser.add_argument("--era-prefix", type=str, default="pons")
    parser.add_argument("--eth-usd", type=float, default=0.0)
    parser.add_argument("--resume", action="store_true", help="Skip launch_ids already in output")
    parser.add_argument("--shard-index", type=int, default=0, help="0-based shard index")
    parser.add_argument("--shard-count", type=int, default=1, help="total shards (>=1)")
    parser.add_argument(
        "--out",
        type=str,
        default="",
        help="Optional output jsonl path (default: data/labels/honest_outcomes.jsonl)",
    )
    parser.add_argument(
        "--derive-short-exits-only",
        action="store_true",
        help="Offline: rewrite honest_outcomes with 1h/6h fields from rug_checkpoints",
    )
    parser.add_argument(
        "--fast-1h",
        action="store_true",
        help="Only label entry + T+1h exit/rug (skip 6h/24h RPC). For EV expansion.",
    )
    args = parser.parse_args()
    ensure_data_dirs()
    if args.derive_short_exits_only:
        out_path = Path(args.out) if args.out else HONEST
        rows = [json.loads(l) for l in out_path.read_text().splitlines() if l.strip()]
        tmp = out_path.with_suffix(out_path.suffix + ".tmp")
        with tmp.open("w") as handle:
            for row in rows:
                attach_short_horizon_exits(row)
                handle.write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")
        tmp.replace(out_path)
        n1 = sum(1 for r in rows if r.get("executable_winner_250_1h"))
        print(f"[done] derived short exits on {len(rows)} rows; winners_1h={n1} -> {out_path}")
        return
    cfg = load_config()
    block_time = float(cfg["approx_block_time_sec"])
    eth_usd = args.eth_usd
    if eth_usd <= 0:
        stats = rest_get("/api/v2/stats")
        eth_usd = float(stats.get("coin_price") or cfg.get("eth_usd_default") or 0)
        if eth_usd <= 0:
            raise SystemExit("could not resolve eth_usd")

    rows = [json.loads(line) for line in LAUNCHES.read_text().splitlines() if line.strip()]
    rows = [r for r in rows if r.get("first_liq_ts")]
    if args.era_prefix:
        rows = [r for r in rows if str(r.get("mechanism_era") or "").startswith(args.era_prefix)]
    rows.sort(key=lambda r: r["first_liq_block"])
    end = len(rows) - args.offset if args.offset else len(rows)
    start = max(0, end - args.limit)
    sample = rows[start:end]
    checkpoints = (3600,) if args.fast_1h else RUG_CHECKPOINTS_SEC
    exit_offset = 3600 if args.fast_1h else EXIT_OFFSET_SEC
    now_ts = max(r["first_liq_ts"] for r in rows)
    sample = [r for r in sample if r["first_liq_ts"] + exit_offset <= now_ts]
    if args.shard_count < 1 or args.shard_index < 0 or args.shard_index >= args.shard_count:
        raise SystemExit("invalid shard-index/shard-count")
    if args.shard_count > 1:
        sample = [r for i, r in enumerate(sample) if i % args.shard_count == args.shard_index]
    out_path = Path(args.out) if args.out else HONEST
    print(
        f"[honest] era_prefix={args.era_prefix!r} sample={len(sample)} "
        f"shard={args.shard_index}/{args.shard_count} eth_usd={eth_usd} "
        f"notional_usd={NOTIONAL_USD} fast_1h={args.fast_1h} out={out_path}"
    )

    done: set[str] = set()
    existing: list[dict[str, Any]] = []
    if args.resume and out_path.exists():
        for line in out_path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            existing.append(row)
            done.add(row["launch_id"])
        print(f"[honest] resume existing={len(done)}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(out_path.suffix + ".tmp")
    # Rewrite full file each run (append-safe via resume merge).
    written = list(existing)
    with tmp.open("w") as handle:
        for row in written:
            handle.write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")
        for i, row in enumerate(sample):
            if row["launch_id"] in done:
                continue
            out = label_one(
                row,
                cfg,
                eth_usd=eth_usd,
                block_time=block_time,
                checkpoints_sec=checkpoints,
                exit_offset_sec=exit_offset,
            )
            # JSON-safe -inf
            if out["rt_log_return_250"] == float("-inf"):
                out["rt_log_return_250"] = None
                out["rt_log_return_250_failed"] = True
            handle.write(json.dumps(out, separators=(",", ":"), sort_keys=True) + "\n")
            written.append(out)
            n_new = len(written) - len(existing)
            if n_new % 5 == 0 or n_new == 1:
                print(
                    f"[honest] new={n_new}/{len(sample)-len(done)} "
                    f"winners={sum(1 for r in written if r.get('executable_winner_250'))} "
                    f"rugs={sum(1 for r in written if r.get('rug'))} "
                    f"credits={credits_remaining()}",
                    flush=True,
                )
    tmp.replace(out_path)

    if args.shard_count > 1:
        print(f"[done] shard wrote {len(written)} -> {out_path} (thresholds deferred to merge)")
        return

    # Freeze thresholds from chronological first 70% (dev) only.
    written.sort(key=lambda r: r["first_liq_block"])
    split = int(len(written) * 0.7)
    dev = written[:split]
    multiples = [
        float(r["gross_multiple"])
        for r in dev
        if r.get("entry_ok") and isinstance(r.get("gross_multiple"), (int, float))
    ]
    multiples.sort()
    def pct(xs: list[float], p: float) -> float | None:
        if not xs:
            return None
        if len(xs) == 1:
            return xs[0]
        k = (len(xs) - 1) * p
        f, c = int(math.floor(k)), int(math.ceil(k))
        if f == c:
            return xs[f]
        return xs[f] * (c - k) + xs[c] * (k - f)

    thresholds = {
        "threshold_version": "honest-v1",
        "n_total": len(written),
        "n_dev": len(dev),
        "notional_usd": NOTIONAL_USD,
        "entry_offset_sec": ENTRY_OFFSET_SEC,
        "exit_offset_sec": EXIT_OFFSET_SEC,
        "win_multiple_frozen": WIN_MULTIPLE,
        "exit_min_recovery": EXIT_MIN_RECOVERY,
        "rug_sell_recovery": RUG_SELL_RECOVERY,
        "rug_mark_drawdown": RUG_MARK_DRAWDOWN,
        "rug_tvl_usd": RUG_TVL_USD,
        "dev_gross_multiple": {
            "p50": pct(multiples, 0.50),
            "p80": pct(multiples, 0.80),
            "p90": pct(multiples, 0.90),
            "p95": pct(multiples, 0.95),
        },
        "counts": {
            "executable_winner_250": sum(1 for r in written if r.get("executable_winner_250")),
            "rug": sum(1 for r in written if r.get("rug")),
            "executable_exit": sum(1 for r in written if r.get("executable_exit")),
            "entry_ok": sum(1 for r in written if r.get("entry_ok")),
        },
        "notes": (
            "Binary winner uses frozen 3× band from spec (not a percentile). "
            "Continuous primary label is rt_log_return_250. "
            "Single-tick v3 math is conservative vs full-book V3 quoter."
        ),
    }
    THRESHOLDS.write_text(json.dumps(thresholds, indent=2, sort_keys=True))
    print(json.dumps(thresholds, indent=2, sort_keys=True))
    print(f"[done] honest_labels={len(written)} -> {HONEST}")


if __name__ == "__main__":
    main()
