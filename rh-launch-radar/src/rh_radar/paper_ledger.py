"""Paper trade ledger: decision-V7 survivors, top-K/hour, exit@1h.

Offline only — reuses honest 1h gross multiples and (optionally) retimed V7.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from rh_radar.backtest import score_row
from rh_radar.config import DATA, ensure_data_dirs
from rh_radar.ev_backtest import fold_key, rebuild_survivor

FEATURES = DATA / "features" / "decision_features.jsonl"
HONEST = DATA / "labels" / "honest_outcomes.jsonl"
VETOES = DATA / "labels" / "vetoes.jsonl"
LEDGER = DATA / "scores" / "paper_ledger.jsonl"
SUMMARY = DATA / "scores" / "paper_ledger_summary.json"


def build_candidates(
    *,
    decision_offset: int,
    veto_mode: str,
    floor_usd: float,
) -> list[dict[str, Any]]:
    honest = {json.loads(l)["launch_id"]: json.loads(l) for l in HONEST.read_text().splitlines() if l.strip()}
    vetoes: dict[str, Any] = {}
    if VETOES.exists():
        vetoes = {json.loads(l)["launch_id"]: json.loads(l) for l in VETOES.read_text().splitlines() if l.strip()}

    rows: list[dict[str, Any]] = []
    for line in FEATURES.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["decision_offset_sec"] != decision_offset:
            continue
        lab = honest.get(row["launch_id"])
        if not lab:
            continue
        veto = vetoes.get(row["launch_id"])
        decision_tvl = lab.get("entry_tvl_usd")
        if veto_mode == "none":
            survivor, reasons = True, []
        elif veto_mode == "launch_v7":
            if not veto:
                survivor, reasons = False, ["missing_veto"]
            else:
                reasons = list(veto.get("reasons") or [])
                survivor = not bool(veto.get("vetoed"))
        else:
            survivor, reasons = rebuild_survivor(
                row,
                veto,
                decision_tvl_usd=decision_tvl if isinstance(decision_tvl, (int, float)) else None,
                floor_usd=floor_usd,
            )
        if not survivor:
            continue
        row = dict(row)
        row["gross_multiple_1h"] = lab.get("gross_multiple_1h")
        row["rug_1h"] = bool(lab.get("rug_1h"))
        row["executable_winner_250_1h"] = bool(lab.get("executable_winner_250_1h"))
        row["entry_tvl_usd"] = decision_tvl
        row["veto_reasons_used"] = reasons
        row["depth_usd"] = decision_tvl
        row["sell_recovery"] = lab.get("gross_multiple_1h")
        score, parts = score_row(row)
        row["score"] = score
        row["score_parts"] = parts
        rows.append(row)
    rows.sort(key=lambda r: r["first_liq_block"])
    return rows


def select_trades(
    rows: list[dict[str, Any]],
    *,
    k: int,
    fold_grain: str,
    dedupe_creator: bool,
    creator_cooldown_sec: int = 0,
    first_time_creator_only: bool = False,
) -> list[dict[str, Any]]:
    by_fold: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_fold[fold_key(int(r["first_liq_ts"]), fold_grain)].append(r)

    trades: list[dict[str, Any]] = []
    last_pick_ts: dict[str, int] = {}
    for fold in sorted(by_fold):
        ranked = sorted(by_fold[fold], key=lambda x: x["score"], reverse=True)
        seen_creators: set[str] = set()
        rank = 0
        for row in ranked:
            if rank >= k:
                break
            creator = (row.get("creator") or "").lower()
            if first_time_creator_only and (row.get("creator_prior_launches") or 0) > 0:
                continue
            if dedupe_creator and creator and creator in seen_creators:
                continue
            if creator_cooldown_sec > 0 and creator:
                prev = last_pick_ts.get(creator)
                if prev is not None and int(row["first_liq_ts"]) - prev < creator_cooldown_sec:
                    continue
            if creator:
                seen_creators.add(creator)
            rank += 1
            g = row.get("gross_multiple_1h")
            trade = {
                "fold": fold,
                "rank_in_fold": rank,
                "launch_id": row["launch_id"],
                "token": row.get("token"),
                "pool": row.get("pool"),
                "creator": row.get("creator"),
                "first_liq_ts": row["first_liq_ts"],
                "first_liq_block": row["first_liq_block"],
                "score": row["score"],
                "entry_tvl_usd": row.get("entry_tvl_usd"),
                "flow_quote_volume_wei": row.get("flow_quote_volume_wei"),
                "creator_prior_launches": row.get("creator_prior_launches"),
                "gross_multiple_1h": g,
                "pnl_per_dollar": (float(g) - 1.0) if isinstance(g, (int, float)) else None,
                "rug_1h": row.get("rug_1h"),
                "executable_winner_250_1h": row.get("executable_winner_250_1h"),
                "exit": "T+1h",
                "notional_usd": 250,
            }
            trades.append(trade)
            if creator:
                last_pick_ts[creator] = int(row["first_liq_ts"])
    return trades


def summarize(trades: list[dict[str, Any]], *, n_candidates: int) -> dict[str, Any]:
    gs = [float(t["gross_multiple_1h"]) for t in trades if isinstance(t.get("gross_multiple_1h"), (int, float))]
    by_fold: dict[str, list[float]] = defaultdict(list)
    for t in trades:
        if isinstance(t.get("gross_multiple_1h"), (int, float)):
            by_fold[t["fold"]].append(float(t["gross_multiple_1h"]))
    fold_means = [sum(xs) / len(xs) for xs in by_fold.values() if xs]
    return {
        "n_candidates": n_candidates,
        "n_trades": len(trades),
        "n_folds_with_trades": len(by_fold),
        "mean_gross_1h": (sum(gs) / len(gs)) if gs else None,
        "median_gross_1h": (sorted(gs)[len(gs) // 2] if gs else None),
        "mean_of_fold_means": (sum(fold_means) / len(fold_means)) if fold_means else None,
        "folds_with_mean_gt_1": sum(1 for x in fold_means if x > 1.0),
        "hit_ge1": sum(1 for g in gs if g >= 1.0) / len(gs) if gs else None,
        "hit_ge3": sum(1 for g in gs if g >= 3.0) / len(gs) if gs else None,
        "rug_1h_rate": sum(1 for t in trades if t.get("rug_1h")) / len(trades) if trades else None,
        "sum_pnl_per_dollar": (sum(gs) / len(gs) - 1.0) if gs else None,
        "equity_curve_end": (sum(gs) / len(gs)) if gs else None,
        "winner_launch_ids": sorted(t["launch_id"] for t in trades if t.get("executable_winner_250_1h")),
        "fold_means": {k: (sum(v) / len(v)) for k, v in sorted(by_fold.items())},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Paper ledger: decision-V7 + top-K/hour + exit@1h")
    parser.add_argument("--decision-offset", type=int, default=600)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--floor-usd", type=float, default=1000.0)
    parser.add_argument("--veto-mode", choices=("none", "launch_v7", "decision_v7"), default="decision_v7")
    parser.add_argument("--fold-grain", choices=("hour", "day"), default="hour")
    parser.add_argument(
        "--dedupe-creator",
        action="store_true",
        help="At most one trade per creator per fold (cheap lineage-ish dedupe)",
    )
    parser.add_argument(
        "--creator-cooldown-sec",
        type=int,
        default=0,
        help="Skip creator if already traded within this many seconds (cross-fold lineage)",
    )
    parser.add_argument(
        "--first-time-creator-only",
        action="store_true",
        help="Only trade creators with creator_prior_launches == 0",
    )
    args = parser.parse_args()
    ensure_data_dirs()

    candidates = build_candidates(
        decision_offset=args.decision_offset,
        veto_mode=args.veto_mode,
        floor_usd=args.floor_usd,
    )
    trades = select_trades(
        candidates,
        k=args.k,
        fold_grain=args.fold_grain,
        dedupe_creator=args.dedupe_creator,
        creator_cooldown_sec=args.creator_cooldown_sec,
        first_time_creator_only=args.first_time_creator_only,
    )
    summary = {
        "decision_offset_sec": args.decision_offset,
        "veto_mode": args.veto_mode,
        "floor_usd": args.floor_usd,
        "k_per_fold": args.k,
        "fold_grain": args.fold_grain,
        "dedupe_creator": args.dedupe_creator,
        "creator_cooldown_sec": args.creator_cooldown_sec,
        "first_time_creator_only": args.first_time_creator_only,
        "ranker": "model_v0",
        "exit": "T+1h honest gross_multiple_1h",
        **summarize(trades, n_candidates=len(candidates)),
    }

    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("w") as handle:
        for t in trades:
            handle.write(json.dumps(t, separators=(",", ":"), sort_keys=True) + "\n")
    SUMMARY.write_text(json.dumps(summary, indent=2, sort_keys=True))
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"[done] ledger -> {LEDGER} ({len(trades)} trades)")
    print(f"[done] summary -> {SUMMARY}")


if __name__ == "__main__":
    main()
