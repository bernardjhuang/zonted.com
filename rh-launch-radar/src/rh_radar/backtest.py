from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any

from rh_radar.config import DATA, ensure_data_dirs

FEATURES = DATA / "features" / "decision_features.jsonl"
LABELS = DATA / "labels" / "outcomes.jsonl"
VETOES = DATA / "labels" / "vetoes.jsonl"
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
    prior = row["creator_prior_launches"]
    parts["creator"] = 3.0 if prior == 0 else (1.0 if prior <= 2 else -2.0 if prior <= 10 else -5.0)
    eth = row["msg_value_wei"] / 1e18
    parts["liquidity"] = 4.0 if eth >= 0.05 else 2.0 if eth >= 0.02 else 0.5
    traders = row["flow_unique_traders"]
    swaps = row["flow_swaps"]
    parts["breadth"] = min(8.0, traders * 0.8)
    parts["activity"] = min(6.0, math.log1p(swaps) * 1.5)
    buys = row["flow_buy_swaps"]
    sells = row["flow_sell_swaps"]
    total = buys + sells
    imbalance = ((buys - sells) / total) if total else 0.0
    parts["imbalance"] = max(-3.0, min(3.0, imbalance * 3.0))
    vol_eth = row["flow_quote_volume_wei"] / 1e18
    parts["volume"] = min(6.0, math.log1p(vol_eth) * 2.0)
    # Optional depth / sell recovery from veto enrichment (available at decision for survivors).
    depth_usd = row.get("depth_usd")
    if isinstance(depth_usd, (int, float)):
        parts["depth"] = 4.0 if depth_usd >= 5000 else 2.0 if depth_usd >= 1000 else 0.0
    recovery = row.get("sell_recovery")
    if isinstance(recovery, (int, float)):
        parts["sellability"] = 3.0 if recovery >= 0.85 else 1.0 if recovery >= 0.5 else -3.0
    if prior >= 20:
        parts["spam_penalty"] = -8.0
    score = sum(parts.values())
    return score, parts


def baseline_ranks(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    def ids_by(key, reverse=True):
        return [r["launch_id"] for r in sorted(rows, key=lambda x: x.get(key) or 0, reverse=reverse)]

    rnd = rows[:]
    random.Random(7).shuffle(rnd)
    # Cheap reputation baselines (Phase 0): first-time creators, then volume tiebreak.
    first_time = sorted(
        rows,
        key=lambda r: (
            0 if (r.get("creator_prior_launches") or 0) == 0 else 1,
            r.get("creator_prior_launches") or 0,
            -(r.get("flow_quote_volume_wei") or 0),
        ),
    )
    return {
        "B1_volume": ids_by("flow_quote_volume_wei"),
        "B2_liquidity_msg_value": ids_by("msg_value_wei"),
        "B3_unique_traders": ids_by("flow_unique_traders"),
        "B4_random": [r["launch_id"] for r in rnd],
        "C1_first_time_then_volume": [r["launch_id"] for r in first_time],
        "model_v0": [r["launch_id"] for r in sorted(rows, key=lambda x: x["score"], reverse=True)],
    }


def evaluate(ranks: dict[str, list[str]], positives: set[str], rugs: set[str], ks=(3, 10)) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, ordered in ranks.items():
        out[name] = {
            **{f"precision@{k}": precision_at_k(ordered, positives, k) for k in ks},
            **{f"recall@{k}": recall_at_k(ordered, positives, k) for k in ks},
            **{f"rug_rate@{k}": (sum(1 for x in ordered[:k] if x in rugs) / k if ordered else 0.0) for k in ks},
            "positives_in_top10": sorted(set(ordered[:10]) & positives),
        }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Chronological backtest of v0 scorecard vs baselines")
    parser.add_argument("--decision-offset", type=int, default=600, help="Seconds after first liquidity")
    parser.add_argument("--dev-fraction", type=float, default=0.7)
    parser.add_argument("--require-veto-survivor", action="store_true", default=True)
    parser.add_argument("--label-field", type=str, default="high_value_proxy")
    args = parser.parse_args()
    ensure_data_dirs()
    random.seed(7)

    labels = {json.loads(line)["launch_id"]: json.loads(line) for line in LABELS.read_text().splitlines() if line.strip()}
    vetoes: dict[str, dict[str, Any]] = {}
    if VETOES.exists():
        vetoes = {json.loads(line)["launch_id"]: json.loads(line) for line in VETOES.read_text().splitlines() if line.strip()}

    feats = []
    for line in FEATURES.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["decision_offset_sec"] != args.decision_offset:
            continue
        if row["launch_id"] not in labels:
            continue
        veto = vetoes.get(row["launch_id"])
        if args.require_veto_survivor:
            if not veto or veto.get("vetoed"):
                continue
        if veto:
            details = veto.get("details") or {}
            row["depth_usd"] = details.get("v7_depth_usd")
            row["tvl_usd"] = details.get("v7_tvl_usd")
            row["sell_recovery"] = details.get("v6_recovery")
            # Rug proxy: failed sell recovery or dust quote-side TVL.
            row["rug_proxy"] = bool(
                (isinstance(row["sell_recovery"], (int, float)) and row["sell_recovery"] < 0.5)
                or (isinstance(row["tvl_usd"], (int, float)) and row["tvl_usd"] < 100)
            )
        else:
            row["rug_proxy"] = False
        score, parts = score_row(row)
        row["score"] = score
        row["score_parts"] = parts
        row["label"] = bool(labels[row["launch_id"]].get("high_value_proxy" if args.label_field == "executable_winner_proxy" else args.label_field))
        # Executable joint label: flow proxy winner + sellable + quote TVL floor.
        if veto and not veto.get("vetoed"):
            details = veto.get("details") or {}
            row["executable_winner_proxy"] = bool(
                row["label"]
                and isinstance(details.get("v6_recovery"), (int, float))
                and details["v6_recovery"] >= 0.5
                and isinstance(details.get("v7_tvl_usd"), (int, float))
                and details["v7_tvl_usd"] >= 1000
            )
        else:
            row["executable_winner_proxy"] = False
        feats.append(row)

    label_key = "executable_winner_proxy" if args.label_field == "executable_winner_proxy" else "label"
    if args.label_field == "executable_winner_proxy":
        for row in feats:
            row["label"] = row["executable_winner_proxy"]

    feats.sort(key=lambda r: r["first_liq_block"])
    if len(feats) < 25:
        raise SystemExit(f"Need more labeled feature rows after filters; have {len(feats)}")

    split = int(len(feats) * args.dev_fraction)
    dev, val = feats[:split], feats[split:]
    positives_dev = {r["launch_id"] for r in dev if r["label"]}
    positives_val = {r["launch_id"] for r in val if r["label"]}
    rugs_dev = {r["launch_id"] for r in dev if r.get("rug_proxy")}
    rugs_val = {r["launch_id"] for r in val if r.get("rug_proxy")}

    ranks_dev = baseline_ranks(dev)
    ranks_val = baseline_ranks(val)
    report = {
        "decision_offset_sec": args.decision_offset,
        "require_veto_survivor": args.require_veto_survivor,
        "label_field": args.label_field,
        "n_total": len(feats),
        "n_dev": len(dev),
        "n_val": len(val),
        "positives_dev": len(positives_dev),
        "positives_val": len(positives_val),
        "threshold_version": json.loads(THRESHOLDS.read_text())["threshold_version"] if THRESHOLDS.exists() else None,
        "dev": evaluate(ranks_dev, positives_dev, rugs_dev),
        "validation": evaluate(ranks_val, positives_val, rugs_val),
    }

    val_metrics = report["validation"]
    # Cheap baselines include reputation (C1). Random is reported but not a promotion hurdle.
    baseline_names = [
        "B1_volume",
        "B2_liquidity_msg_value",
        "B3_unique_traders",
        "C1_first_time_then_volume",
    ]
    best_base = max(baseline_names, key=lambda n: val_metrics[n]["precision@10"])
    model_p10 = val_metrics["model_v0"]["precision@10"]
    base_p10 = val_metrics[best_base]["precision@10"]
    lift = (model_p10 / base_p10) if base_p10 > 0 else None
    model_rug = val_metrics["model_v0"]["rug_rate@10"]
    base_rug = val_metrics[best_base]["rug_rate@10"]
    report["promotion"] = {
        "best_baseline": best_base,
        "model_precision@10": model_p10,
        "baseline_precision@10": base_p10,
        "lift_vs_best_baseline": lift,
        "model_rug_rate@10": model_rug,
        "baseline_rug_rate@10": base_rug,
        "bar": ">=1.5x Precision@10 over best cheap baseline AND rug-rate@10 <= baseline",
        "passed": bool(lift is not None and lift >= 1.5 and model_rug <= base_rug),
        "diagnostic_only_until_honest_labels": True,
    }

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"[done] report -> {REPORT}")


if __name__ == "__main__":
    main()
