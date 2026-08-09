from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from rh_radar.config import DATA, ensure_data_dirs

FEATURES = DATA / "features" / "decision_features.jsonl"
LABELS = DATA / "labels" / "outcomes.jsonl"
THRESHOLDS = DATA / "labels" / "thresholds.json"
REPORT = DATA / "scores" / "backtest_report.json"


def precision_at_k(ranked_ids: list[str], positives: set[str], k: int) -> float:
    top = ranked_ids[:k]
    if not top:
        return 0.0
    return sum(1 for x in top if x in positives) / len(top)


def recall_at_k(ranked_ids: list[str], positives: set[str], k: int) -> float:
    if not positives:
        return 0.0
    top = set(ranked_ids[:k])
    return len(top & positives) / len(positives)


def score_row(row: dict[str, Any]) -> tuple[float, dict[str, float]]:
    """Interpretable v0 scorecard (uniform family weights, small integer feel)."""
    parts: dict[str, float] = {}
    # F2 creator quality (invert serial spammers)
    prior = row["creator_prior_launches"]
    parts["creator"] = 3.0 if prior == 0 else (1.0 if prior <= 2 else -2.0 if prior <= 10 else -5.0)
    # F3 liquidity quality proxy: initial msg value (launch ETH)
    eth = row["msg_value_wei"] / 1e18
    parts["liquidity"] = 4.0 if eth >= 0.05 else 2.0 if eth >= 0.02 else 0.5
    # F4 flow breadth at decision time
    traders = row["flow_unique_traders"]
    swaps = row["flow_swaps"]
    parts["breadth"] = min(8.0, traders * 0.8)
    parts["activity"] = min(6.0, math.log1p(swaps) * 1.5)
    # buy/sell imbalance
    buys = row["flow_buy_swaps"]
    sells = row["flow_sell_swaps"]
    total = buys + sells
    imbalance = ((buys - sells) / total) if total else 0.0
    parts["imbalance"] = max(-3.0, min(3.0, imbalance * 3.0))
    # volume
    vol_eth = row["flow_quote_volume_wei"] / 1e18
    parts["volume"] = min(6.0, math.log1p(vol_eth) * 2.0)
    # penalty: creator already dumping-era spam
    if prior >= 20:
        parts["spam_penalty"] = -8.0
    score = sum(parts.values())
    return score, parts


def baseline_ranks(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    def ids_by(key, reverse=True):
        return [r["launch_id"] for r in sorted(rows, key=lambda x: x[key], reverse=reverse)]

    rnd = rows[:]
    random.Random(7).shuffle(rnd)
    return {
        "B1_volume": ids_by("flow_quote_volume_wei"),
        "B2_liquidity_msg_value": ids_by("msg_value_wei"),
        "B3_unique_traders": ids_by("flow_unique_traders"),
        "B4_random": [r["launch_id"] for r in rnd],
        "model_v0": [r["launch_id"] for r in sorted(rows, key=lambda x: x["score"], reverse=True)],
    }


def evaluate(ranks: dict[str, list[str]], positives: set[str], ks=(3, 10)) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, ordered in ranks.items():
        out[name] = {
            **{f"precision@{k}": precision_at_k(ordered, positives, k) for k in ks},
            **{f"recall@{k}": recall_at_k(ordered, positives, k) for k in ks},
            "positives_in_top10": sorted(set(ordered[:10]) & positives),
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Chronological backtest of v0 scorecard vs baselines")
    parser.add_argument("--decision-offset", type=int, default=600, help="Seconds after first liquidity")
    parser.add_argument("--dev-fraction", type=float, default=0.7)
    args = parser.parse_args()
    ensure_data_dirs()
    random.seed(7)

    labels = {json.loads(line)["launch_id"]: json.loads(line) for line in LABELS.read_text().splitlines() if line.strip()}
    feats = []
    for line in FEATURES.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["decision_offset_sec"] != args.decision_offset:
            continue
        if row["launch_id"] not in labels:
            continue
        score, parts = score_row(row)
        row["score"] = score
        row["score_parts"] = parts
        row["high_value_proxy"] = bool(labels[row["launch_id"]].get("high_value_proxy"))
        feats.append(row)
    feats.sort(key=lambda r: r["first_liq_block"])
    if len(feats) < 40:
        raise SystemExit(f"Need more labeled feature rows; have {len(feats)}")

    split = int(len(feats) * args.dev_fraction)
    # Ensure split is not exactly on a pathological boundary; keep chronological.
    dev, val = feats[:split], feats[split:]
    positives_dev = {r["launch_id"] for r in dev if r["high_value_proxy"]}
    positives_val = {r["launch_id"] for r in val if r["high_value_proxy"]}

    # Optional tiny calibration on dev: none for v0 integer scorecard (frozen).
    ranks_dev = baseline_ranks(dev)
    ranks_val = baseline_ranks(val)
    report = {
        "decision_offset_sec": args.decision_offset,
        "n_total": len(feats),
        "n_dev": len(dev),
        "n_val": len(val),
        "positives_dev": len(positives_dev),
        "positives_val": len(positives_val),
        "threshold_version": json.loads(THRESHOLDS.read_text())["threshold_version"] if THRESHOLDS.exists() else None,
        "dev": evaluate(ranks_dev, positives_dev),
        "validation": evaluate(ranks_val, positives_val),
    }

    # Lift vs best naive baseline on validation Precision@10
    val_metrics = report["validation"]
    baseline_names = ["B1_volume", "B2_liquidity_msg_value", "B3_unique_traders", "B4_random"]
    best_base = max(baseline_names, key=lambda n: val_metrics[n]["precision@10"])
    model_p10 = val_metrics["model_v0"]["precision@10"]
    base_p10 = val_metrics[best_base]["precision@10"]
    lift = (model_p10 / base_p10) if base_p10 > 0 else None
    report["promotion"] = {
        "best_baseline": best_base,
        "model_precision@10": model_p10,
        "baseline_precision@10": base_p10,
        "lift_vs_best_baseline": lift,
        "bar": ">=1.5x Precision@10 over best baseline (and rug-rate constraint — rug proxy not yet wired)",
        "passed": bool(lift is not None and lift >= 1.5),
    }

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"[done] report -> {REPORT}")


if __name__ == "__main__":
    main()
