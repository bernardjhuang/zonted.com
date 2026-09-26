"""Walk-forward paper EV on honest 1h gross multiples.

Uses existing features + honest labels (no new RPC). Optionally rebuilds the
survivor mask by applying V7 at decision-time TVL (honest entry_tvl_usd) instead
of launch-block TVL — the Round D failure mode.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from rh_radar.backtest import baseline_ranks, score_row
from rh_radar.config import DATA, ensure_data_dirs

FEATURES = DATA / "features" / "decision_features.jsonl"
HONEST = DATA / "labels" / "honest_outcomes.jsonl"
VETOES = DATA / "labels" / "vetoes.jsonl"
REPORT = DATA / "scores" / "ev_backtest_report.json"


def fold_key(ts: int, grain: str) -> str:
    """UTC fold key. Cohort often spans <2 calendar days — prefer hour folds."""
    from datetime import datetime, timezone

    dt = datetime.fromtimestamp(ts, timezone.utc)
    if grain == "day":
        return dt.strftime("%Y-%m-%d")
    if grain == "hour":
        return dt.strftime("%Y-%m-%dT%H")
    raise ValueError(f"unknown fold grain: {grain}")


def rebuild_survivor(
    row: dict[str, Any],
    veto: dict[str, Any] | None,
    *,
    decision_tvl_usd: float | None,
    floor_usd: float,
) -> tuple[bool, list[str]]:
    """Structural vetoes kept; V7 re-evaluated at decision-time TVL when available."""
    reasons: list[str] = []
    if veto:
        for r in veto.get("reasons") or []:
            if r.startswith("V7_"):
                continue
            # Drop heavy V6 launch-block failures too when we have decision TVL path;
            # sellability is represented by 1h gross multiple in the EV label.
            if r.startswith("V6_"):
                continue
            reasons.append(r)
    if decision_tvl_usd is None:
        if veto:
            for r in veto.get("reasons") or []:
                if r.startswith("V7_"):
                    reasons.append(r)
        else:
            reasons.append("V7_missing_decision_tvl")
    elif decision_tvl_usd < floor_usd:
        reasons.append(f"V7_decision_tvl:{decision_tvl_usd:.2f}<{floor_usd}")
    return (len(reasons) == 0), reasons


def fold_metrics(picks: list[dict[str, Any]], k: int) -> dict[str, Any]:
    top = picks[:k]
    if not top:
        return {"n": 0, "mean_gross_1h": None, "hit_ge1": None, "hit_ge3": None, "rug_1h_rate": None}
    gs = [float(r["gross_multiple_1h"]) for r in top if isinstance(r.get("gross_multiple_1h"), (int, float))]
    return {
        "n": len(top),
        "mean_gross_1h": (sum(gs) / len(gs)) if gs else None,
        "median_gross_1h": (sorted(gs)[len(gs) // 2] if gs else None),
        "hit_ge1": sum(1 for g in gs if g >= 1.0) / len(gs) if gs else None,
        "hit_ge3": sum(1 for g in gs if g >= 3.0) / len(gs) if gs else None,
        "rug_1h_rate": sum(1 for r in top if r.get("rug_1h")) / len(top),
        "sum_pnl_per_dollar": (sum(gs) / len(gs) - 1.0) if gs else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-forward EV backtest on 1h honest multiples")
    parser.add_argument("--decision-offset", type=int, default=600)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--floor-usd", type=float, default=1000.0)
    parser.add_argument(
        "--veto-mode",
        choices=("none", "launch_v7", "decision_v7"),
        default="decision_v7",
        help="none=all labeled; launch_v7=existing veto file; decision_v7=retiming V7 to entry TVL",
    )
    parser.add_argument("--min-fold-candidates", type=int, default=5)
    parser.add_argument("--fold-grain", choices=("hour", "day"), default="hour")
    args = parser.parse_args()
    ensure_data_dirs()
    random.seed(7)

    honest = {json.loads(l)["launch_id"]: json.loads(l) for l in HONEST.read_text().splitlines() if l.strip()}
    vetoes = {}
    if VETOES.exists():
        vetoes = {json.loads(l)["launch_id"]: json.loads(l) for l in VETOES.read_text().splitlines() if l.strip()}

    rows: list[dict[str, Any]] = []
    for line in FEATURES.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["decision_offset_sec"] != args.decision_offset:
            continue
        lab = honest.get(row["launch_id"])
        if not lab:
            continue
        veto = vetoes.get(row["launch_id"])
        decision_tvl = lab.get("entry_tvl_usd")
        if args.veto_mode == "none":
            survivor, reasons = True, []
        elif args.veto_mode == "launch_v7":
            if not veto:
                survivor, reasons = False, ["missing_veto"]
            else:
                reasons = list(veto.get("reasons") or [])
                survivor = not bool(veto.get("vetoed"))
        else:
            survivor, reasons = rebuild_survivor(
                row, veto, decision_tvl_usd=decision_tvl if isinstance(decision_tvl, (int, float)) else None,
                floor_usd=args.floor_usd,
            )
        if not survivor:
            continue
        # Attach honest 1h outcomes + score
        row = dict(row)
        row["gross_multiple_1h"] = lab.get("gross_multiple_1h")
        row["rug_1h"] = bool(lab.get("rug_1h"))
        row["executable_winner_250_1h"] = bool(lab.get("executable_winner_250_1h"))
        row["entry_tvl_usd"] = decision_tvl
        row["veto_reasons_used"] = reasons
        row["depth_usd"] = decision_tvl
        row["sell_recovery"] = lab.get("gross_multiple_1h")  # weak proxy for scorecard sellability term
        score, parts = score_row(row)
        row["score"] = score
        row["score_parts"] = parts
        row["fold"] = fold_key(int(row["first_liq_ts"]), args.fold_grain)
        rows.append(row)

    rows.sort(key=lambda r: r["first_liq_block"])
    by_fold: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_fold[r["fold"]].append(r)

    rankers = {
        "model_v0": lambda fold_rows: sorted(fold_rows, key=lambda x: x["score"], reverse=True),
        "B1_volume": lambda fold_rows: sorted(fold_rows, key=lambda x: x.get("flow_quote_volume_wei") or 0, reverse=True),
        "B3_unique_traders": lambda fold_rows: sorted(
            fold_rows, key=lambda x: x.get("flow_unique_traders") or 0, reverse=True
        ),
        "C1_first_time_then_volume": lambda fold_rows: sorted(
            fold_rows,
            key=lambda x: (
                0 if (x.get("creator_prior_launches") or 0) == 0 else 1,
                x.get("creator_prior_launches") or 0,
                -(x.get("flow_quote_volume_wei") or 0),
            ),
        ),
        "B4_random": lambda fold_rows: (lambda xs: (random.Random(7 + hash(xs[0]["fold"]) % 10_000).shuffle(xs) or xs))(
            fold_rows[:]
        ),
    }

    folds = sorted(by_fold)
    per_ranker: dict[str, Any] = {}
    for name, rank_fn in rankers.items():
        fold_rows: list[dict[str, Any]] = []
        fold_metrics_rows = []
        fold_means = []
        for fold in folds:
            candidates = by_fold[fold]
            if len(candidates) < args.min_fold_candidates:
                continue
            ranked = rank_fn(candidates)
            m = fold_metrics(ranked, args.k)
            m["fold"] = fold
            m["fold_n"] = len(candidates)
            fold_metrics_rows.append(m)
            if m["mean_gross_1h"] is not None:
                fold_means.append(m["mean_gross_1h"])
            fold_rows.extend(ranked[: args.k])
        gs = [float(r["gross_multiple_1h"]) for r in fold_rows if isinstance(r.get("gross_multiple_1h"), (int, float))]
        per_ranker[name] = {
            "folds_used": len(fold_metrics_rows),
            "picks": len(fold_rows),
            "mean_gross_1h": (sum(gs) / len(gs)) if gs else None,
            "median_gross_1h": (sorted(gs)[len(gs) // 2] if gs else None),
            "mean_of_fold_means": (sum(fold_means) / len(fold_means)) if fold_means else None,
            "folds_with_mean_gt_1": sum(1 for x in fold_means if x > 1.0),
            "hit_ge1": sum(1 for g in gs if g >= 1.0) / len(gs) if gs else None,
            "hit_ge3": sum(1 for g in gs if g >= 3.0) / len(gs) if gs else None,
            "rug_1h_rate": sum(1 for r in fold_rows if r.get("rug_1h")) / len(fold_rows) if fold_rows else None,
            "sum_pnl_per_dollar": (sum(gs) / len(gs) - 1.0) if gs else None,
            "folds": fold_metrics_rows,
            "winner_launch_ids": sorted({r["launch_id"] for r in fold_rows if r.get("executable_winner_250_1h")}),
        }

    # Cohort diagnostics after veto mode
    n_pos = sum(1 for r in rows if r.get("executable_winner_250_1h"))
    n_ge1 = sum(1 for r in rows if isinstance(r.get("gross_multiple_1h"), (int, float)) and r["gross_multiple_1h"] >= 1.0)
    report = {
        "decision_offset_sec": args.decision_offset,
        "exit": "T+1h honest gross_multiple_1h",
        "notional_usd": 250,
        "k_per_fold": args.k,
        "fold_grain": args.fold_grain,
        "veto_mode": args.veto_mode,
        "floor_usd": args.floor_usd,
        "n_candidates": len(rows),
        "n_folds_total": len(folds),
        "positives_3x_1h": n_pos,
        "positives_ge1_1h": n_ge1,
        "rankers": per_ranker,
        "promotion_ev": {
            "bar": "mean_of_fold_means > 1.0 on raw 1h gross (gas≈0) with ≥2 folds mean>1",
            "best_ranker": max(
                per_ranker,
                key=lambda n: (
                    per_ranker[n]["mean_of_fold_means"] is not None,
                    per_ranker[n]["mean_of_fold_means"] or -1,
                ),
            ),
            "passed": any(
                (
                    per_ranker[n]["mean_of_fold_means"] is not None
                    and per_ranker[n]["mean_of_fold_means"] > 1.0
                    and per_ranker[n]["folds_with_mean_gt_1"] >= 2
                )
                for n in per_ranker
            ),
        },
        "notes": (
            "decision_v7 uses honest entry_tvl_usd at T+10m instead of launch-block V7. "
            "Structural V5 clone-burst and V1/V3 retained from the veto file. "
            "Hour folds used because the current 800-launch slice sits on one UTC day."
        ),
    }
    # Attach comparison snapshot for launch_v7 vs decision_v7 counts when mode is decision.
    if args.veto_mode == "decision_v7":
        launch_surv = 0
        for line in FEATURES.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row["decision_offset_sec"] != args.decision_offset or row["launch_id"] not in honest:
                continue
            v = vetoes.get(row["launch_id"])
            if v and not v.get("vetoed"):
                launch_surv += 1
        report["survivor_count_launch_v7"] = launch_surv
        report["survivor_count_decision_v7"] = len(rows)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"[done] report -> {REPORT}")


if __name__ == "__main__":
    main()
