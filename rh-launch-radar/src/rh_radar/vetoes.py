from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from rh_radar.config import DATA, ensure_data_dirs, load_config
from rh_radar.pool_math import (
    depth_quote_for_pct,
    quote_side_tvl_wei,
    read_v3_pool_state,
    simulate_sell_quote_out,
    token_amount_for_quote_notional,
)
from rh_radar.rpc import credits_remaining, rest_get

LAUNCHES = DATA / "launches.jsonl"
VETOES = DATA / "labels" / "vetoes.jsonl"
BURN = "0x0000000000000000000000000000000000000000"
DEAD = "0x000000000000000000000000000000000000dead"


def _norm_name(name: str | None) -> str:
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def gate_v1_quote(row: dict[str, Any], cfg: dict[str, Any]) -> str | None:
    allowed = {
        cfg["tokens"]["weth"].lower(),
        cfg["tokens"]["usdg"].lower(),
        cfg["tokens"]["native"].lower(),
    }
    if row["quote"].lower() not in allowed:
        return f"V1_bad_quote:{row['quote']}"
    return None


def gate_v3_lp_custody(row: dict[str, Any], cfg: dict[str, Any]) -> str | None:
    """Pons v1 locks via factory→locker NFT transfer; InstantLaunch encodes finalPositionRecipient."""
    era = row.get("mechanism_era") or ""
    if era.startswith("pons"):
        # Strategy-eligible Pons factory path is locked by construction; if an explicit
        # recipient is present on the row, it must be the Pons locker / burn.
        locker = cfg["pons_locker"].lower()
        recipient = (row.get("lp_recipient") or "").lower()
        if recipient and recipient not in {locker, BURN, DEAD}:
            return f"V3_lp_not_locked:{recipient}"
        return None
    if era.startswith("pools"):
        locker = (cfg.get("pools_lp_recipient") or "").lower()
        recipient = (row.get("lp_recipient") or "").lower()
        if not recipient:
            return "V3_lp_recipient_missing"
        if locker and recipient != locker:
            return f"V3_lp_not_locked:{recipient}"
        return None
    return "V3_unknown_era"


def gate_v5_clone_burst(row: dict[str, Any], burst_ids: set[str]) -> str | None:
    if row["launch_id"] in burst_ids:
        return "V5_clone_burst"
    return None


def _quote_usd(quote: str, amount_wei: float | int, cfg: dict[str, Any], eth_usd: float) -> float:
    if quote.lower() == cfg["tokens"]["weth"].lower():
        return float(amount_wei) / 1e18 * eth_usd
    if quote.lower() == cfg["tokens"]["usdg"].lower():
        return float(amount_wei) / 1e6
    return float(amount_wei) / 1e18 * eth_usd


def gate_v7_liquidity_floor(
    row: dict[str, Any],
    cfg: dict[str, Any],
    *,
    eth_usd: float,
    floor_usd: float,
    block: int | str,
    state: dict[str, Any] | None = None,
) -> tuple[str | None, dict[str, Any]]:
    """
    V7 uses quote-side pool TVL (WETH/USDG balance), not ±0.5% impact depth.
    ±0.5% depth is an F3 feature and is far smaller than displayed liquidity.
    """
    meta: dict[str, Any] = {
        "tvl_quote_wei": 0,
        "tvl_usd": 0.0,
        "depth_quote_wei": 0,
        "depth_usd": 0.0,
        "eth_usd": eth_usd,
        "block": block,
    }
    try:
        tvl_wei = quote_side_tvl_wei(row["pool"], row["quote"], block)
        meta["tvl_quote_wei"] = int(tvl_wei)
        meta["tvl_usd"] = _quote_usd(row["quote"], tvl_wei, cfg, eth_usd)
        state = state or read_v3_pool_state(row["pool"], block)
        depth_wei = depth_quote_for_pct(state, row["quote"], 0.005)
        meta["depth_quote_wei"] = int(depth_wei)
        meta["depth_usd"] = _quote_usd(row["quote"], depth_wei, cfg, eth_usd)
        if meta["tvl_usd"] < floor_usd:
            return f"V7_liq_floor:{meta['tvl_usd']:.2f}<{floor_usd}", meta
        return None, meta
    except Exception as exc:
        return f"V7_pool_state_error:{type(exc).__name__}", meta


def gate_v6_sell_sim(
    row: dict[str, Any],
    cfg: dict[str, Any],
    *,
    eth_usd: float,
    block: int | str,
    notional_usd: float = 250.0,
    state: dict[str, Any] | None = None,
) -> tuple[str | None, dict[str, Any]]:
    meta: dict[str, Any] = {
        "notional_usd": notional_usd,
        "quote_out_wei": 0,
        "recovery": None,
        "block": block,
    }
    try:
        state = state or read_v3_pool_state(row["pool"], block)
        if row["quote"].lower() == cfg["tokens"]["weth"].lower():
            quote_in = int((notional_usd / eth_usd) * 1e18)
        elif row["quote"].lower() == cfg["tokens"]["usdg"].lower():
            quote_in = int(notional_usd * 1e6)
        else:
            return "V6_unsupported_quote", meta
        token_in = token_amount_for_quote_notional(state, row["quote"], row["token"], quote_in)
        quote_out = simulate_sell_quote_out(state, row["quote"], row["token"], token_in)
        meta["quote_out_wei"] = quote_out
        recovery = (quote_out / quote_in) if quote_in else 0.0
        # Clamp — model is tick-local and can slightly overshoot on tiny notionals.
        recovery = min(recovery, 1.0)
        meta["recovery"] = recovery
        if recovery < 0.5:
            return f"V6_sell_recovery:{recovery:.3f}<0.5", meta
        return None, meta
    except Exception as exc:
        return f"V6_sell_error:{type(exc).__name__}", meta


def gate_v8_concentration(token: str, pool: str, threshold: float = 0.40) -> tuple[str | None, dict[str, Any]]:
    meta: dict[str, Any] = {"top1_share_ex_lp": None, "holders_returned": 0}
    try:
        payload = rest_get(f"/api/v2/tokens/{token}/holders")
        items = payload.get("items") or []
        meta["holders_returned"] = len(items)
        total = 0
        balances: list[tuple[str, int]] = []
        for item in items:
            addr = ((item.get("address") or {}).get("hash") or "").lower()
            value = int(item.get("value") or 0)
            total += value
            balances.append((addr, value))
        if total <= 0:
            return "V8_no_supply", meta
        ex = [(a, v) for a, v in balances if a not in {pool.lower(), BURN, DEAD}]
        if not ex:
            return None, meta
        top = max(ex, key=lambda x: x[1])
        share = top[1] / total
        meta["top1_share_ex_lp"] = share
        meta["top1"] = top[0]
        if share > threshold:
            return f"V8_concentration:{share:.3f}>{threshold}", meta
        return None, meta
    except Exception as exc:
        return f"V8_holders_error:{type(exc).__name__}", meta


def build_clone_burst_ids(rows: list[dict[str, Any]], window_sec: int = 3600, min_count: int = 3) -> set[str]:
    """Flag creators with ≥min_count launches inside any trailing window_sec (two-pointer)."""
    by_creator: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("first_liq_ts") is None or not row.get("creator"):
            continue
        by_creator[row["creator"]].append(row)
    flagged: set[str] = set()
    for launches in by_creator.values():
        launches.sort(key=lambda r: r["first_liq_ts"])
        left = 0
        for right, row in enumerate(launches):
            while launches[left]["first_liq_ts"] < row["first_liq_ts"] - window_sec:
                left += 1
            if right - left + 1 >= min_count:
                for r in launches[left : right + 1]:
                    flagged.add(r["launch_id"])
    return flagged


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply Stage-1 veto gates to a launch sample")
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument("--offset", type=int, default=1726)
    parser.add_argument("--floor-usd", type=float, default=1000.0)
    parser.add_argument("--eth-usd", type=float, default=0.0, help="0 = fetch from Blockscout stats")
    parser.add_argument("--skip-heavy", action="store_true", help="Skip V6/V7/V8 eth_call/holders (fast structural only)")
    parser.add_argument(
        "--era-prefix",
        type=str,
        default="pons",
        help="Only include mechanism_era starting with this prefix (empty = all). Default pons avoids v4 poolIds.",
    )
    args = parser.parse_args()
    ensure_data_dirs()
    cfg = load_config()
    eth_usd = args.eth_usd
    if eth_usd <= 0:
        stats = rest_get("/api/v2/stats")
        eth_usd = float(stats.get("coin_price") or 0)
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
    print(
        f"[vetoes] era_prefix={args.era_prefix!r} stamped={len(rows)} "
        f"sample={len(sample)} eth_usd={eth_usd} floor_usd={args.floor_usd}"
    )
    burst_ids = build_clone_burst_ids(rows)
    print(f"[vetoes] clone_burst_flagged={len(burst_ids)}")

    VETOES.parent.mkdir(parents=True, exist_ok=True)
    tmp = VETOES.with_suffix(".tmp")
    survivors = killed = 0
    with tmp.open("w") as handle:
        for i, row in enumerate(sample):
            reasons: list[str] = []
            details: dict[str, Any] = {"eth_usd": eth_usd}
            for gate in (
                gate_v1_quote(row, cfg),
                gate_v3_lp_custody(row, cfg),
                gate_v5_clone_burst(row, burst_ids),
            ):
                if gate:
                    reasons.append(gate)
            # Heavy gates only if structural gates passed — saves most eth_call budget.
            if not args.skip_heavy and not reasons:
                block = int(row["first_liq_block"])
                try:
                    shared_state = read_v3_pool_state(row["pool"], block)
                except Exception:
                    shared_state = None
                r7, m7 = gate_v7_liquidity_floor(
                    row,
                    cfg,
                    eth_usd=eth_usd,
                    floor_usd=args.floor_usd,
                    block=block,
                    state=shared_state,
                )
                details.update({f"v7_{k}": v for k, v in m7.items()})
                if r7:
                    reasons.append(r7)
                r6, m6 = gate_v6_sell_sim(
                    row, cfg, eth_usd=eth_usd, block=block, state=shared_state
                )
                details.update({f"v6_{k}": v for k, v in m6.items()})
                if r6:
                    reasons.append(r6)
                r8, m8 = gate_v8_concentration(row["token"], row["pool"])
                details.update({f"v8_{k}": v for k, v in m8.items()})
                if r8:
                    reasons.append(r8)
            out = {
                "launch_id": row["launch_id"],
                "token": row["token"],
                "pool": row["pool"],
                "mechanism_era": row.get("mechanism_era"),
                "factory_name": row.get("factory_name"),
                "first_liq_ts": row.get("first_liq_ts"),
                "first_liq_block": row.get("first_liq_block"),
                "vetoed": bool(reasons),
                "reasons": reasons,
                "details": details,
                "available_at": row.get("first_liq_ts"),
                "observed_block": row.get("first_liq_block"),
            }
            handle.write(json.dumps(out, separators=(",", ":"), sort_keys=True) + "\n")
            survivors += int(not reasons)
            killed += int(bool(reasons))
            if (i + 1) % 25 == 0:
                print(f"[vetoes] {i+1}/{len(sample)} survivors={survivors} killed={killed} credits={credits_remaining()}")
    tmp.replace(VETOES)
    print(f"[done] sample={len(sample)} survivors={survivors} killed={killed} -> {VETOES}")


if __name__ == "__main__":
    main()
