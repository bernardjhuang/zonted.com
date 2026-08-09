"""Phase 0 cheap-signal tests on an existing labeled cohort.

Answers the Fable review question: does creator prior alone match model_v0?
Does first-time-creator filtering dominate flow features under the (still circular)
proxy label? Reports P@K diagnostics only — not a promotion decision.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from typing import Any

from rh_radar.backtest import evaluate, score_row
from rh_radar.config import DATA, ensure_data_dirs

FEATURES = DATA / "features" / "decision_features.jsonl"
LABELS = DATA / "labels" / "outcomes.jsonl"
HONEST = DATA / "labels" / "honest_outcomes.jsonl"
VETOES = DATA / "labels" / "vetoes.jsonl"
REPORT = DATA / "scores" / "phase0_report.json"


def build_creator_history(rows: list[dict[str, Any]], labels: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in sorted(rows, key=lambda r: r["first_liq_block"]):
        by[row["creator"]].append(
            {
                "launch_id": row["launch_id"],
                "first_liq_block": row["first_liq_block"],
                "winner": bool(labels.get(row["launch_id"], {}).get("high_value_proxy")),
            }
        )
    return by


def prior_winner_rate(history: list[dict[str, Any]], block: int) -> float | None:
    past = [h for h in history if h["first_liq_block"] < block]
    if not past:
        return None
    return sum(1 for h in past if h["winner"]) / len(past)


def ranks_for(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    def ids_by(key, reverse=True):
        return [r["launch_id"] for r in sorted(rows, key=lambda x: x.get(key) or 0, reverse=reverse)]

    rnd = rows[:]
    random.Random(7).shuffle(rnd)
    # Prefer first-time creators, then lower prior count, then higher volume as tiebreak.
    first_time = sorted(
        rows,
        key=lambda r: (
            0 if r["creator_prior_launches"] == 0 else 1,
            r["creator_prior_launches"],
            -(r.get("flow_quote_volume_wei") or 0),
        ),
    )
    # Prefer higher prior winner rate; unknown (None) ranks last among non-first-timers.
    by_winrate = sorted(
        rows,
        key=lambda r: (
            -1.0 if r["creator_prior_launches"] == 0 else -(r.get("creator_prior_win_rate") or -0.01),
            -(r.get("flow_quote_volume_wei") or 0),
        ),
    )
    # Inverse prior: fewer prior launches ranks higher.
    by_low_prior = sorted(
        rows,
        key=lambda r: (r["creator_prior_launches"], -(r.get("flow_quote_volume_wei") or 0)),
    )
    return {
        "B1_volume": ids_by("flow_quote_volume_wei"),
        "B3_unique_traders": ids_by("flow_unique_traders"),
        "B4_random": [r["launch_id"] for r in rnd],
        "C1_first_time_then_volume": [r["launch_id"] for r in first_time],
        "C2_low_prior_count": [r["launch_id"] for r in by_low_prior],
        "C3_prior_win_rate": [r["launch_id"] for r in by_winrate],
        "model_v0": [r["launch_id"] for r in sorted(rows, key=lambda x: x["score"], reverse=True)],
    }


def summarize_buckets(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets = [(0, 0), (1, 2), (3, 10), (11, 50), (51, 10**9)]
    out = []
    for lo, hi in buckets:
        cell = [r for r in rows if lo <= r["creator_prior_launches"] <= hi]
        n = len(cell)
        pos = sum(1 for r in cell if r["label"])
        out.append(
            {
                "prior_lo": lo,
                "prior_hi": hi if hi < 10**9 else None,
                "n": n,
                "positives": pos,
                "positive_rate": (pos / n) if n else None,
            }
        )
    return out


def run_slice(name: str, rows: list[dict[str, Any]], dev_fraction: float) -> dict[str, Any]:
    rows = sorted(rows, key=lambda r: r["first_liq_block"])
    split = int(len(rows) * dev_fraction)
    dev, val = rows[:split], rows[split:]
    positives_dev = {r["launch_id"] for r in dev if r["label"]}
    positives_val = {r["launch_id"] for r in val if r["label"]}
    rugs_dev = {r["launch_id"] for r in dev if r.get("rug_proxy")}
    rugs_val = {r["launch_id"] for r in val if r.get("rug_proxy")}
    ranks_dev = ranks_for(dev)
    ranks_val = ranks_for(val)
    report = {
        "slice": name,
        "n_total": len(rows),
        "n_dev": len(dev),
        "n_val": len(val),
        "positives_dev": len(positives_dev),
        "positives_val": len(positives_val),
        "prior_buckets_all": summarize_buckets(rows),
        "prior_buckets_val": summarize_buckets(val),
        "dev": evaluate(ranks_dev, positives_dev, rugs_dev),
        "validation": evaluate(ranks_val, positives_val, rugs_val),
    }
    cheap = ["C1_first_time_then_volume", "C2_low_prior_count", "C3_prior_win_rate", "B1_volume", "B3_unique_traders"]
    val_m = report["validation"]
    best_cheap = max(cheap, key=lambda n: val_m[n]["precision@10"])
    model_p = val_m["model_v0"]["precision@10"]
    cheap_p = val_m[best_cheap]["precision@10"]
    report["phase0_gate"] = {
        "best_cheap_baseline": best_cheap,
        "best_cheap_precision@10": cheap_p,
        "model_precision@10": model_p,
        "model_minus_cheap": model_p - cheap_p,
        "creator_prior_matches_model": bool(
            val_m["C1_first_time_then_volume"]["precision@10"] >= model_p - 1e-9
            or val_m["C2_low_prior_count"]["precision@10"] >= model_p - 1e-9
        ),
        "note": (
            "If creator_prior_matches_model, prefer reputation-first architecture; "
            "ranker is a tiebreaker. Labels are still m0-proxy-v1 (circular) — redo after honest labels."
        ),
    }
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 0 creator-prior / cheap-signal tests")
    parser.add_argument("--decision-offset", type=int, default=600)
    parser.add_argument("--dev-fraction", type=float, default=0.7)
    parser.add_argument(
        "--label-field",
        type=str,
        default="high_value_proxy",
        help="high_value_proxy | executable_winner_250",
    )
    args = parser.parse_args()
    ensure_data_dirs()
    random.seed(7)

    use_honest = args.label_field == "executable_winner_250"
    label_path = HONEST if use_honest else LABELS
    if not label_path.exists():
        raise SystemExit(f"missing {label_path}")
    labels = {json.loads(line)["launch_id"]: json.loads(line) for line in label_path.read_text().splitlines() if line.strip()}
    vetoes = {}
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
        feats.append(row)

    # For creator win-rate, treat honest/proxy winner the same field name downstream.
    win_key = "executable_winner_250" if use_honest else "high_value_proxy"
    labels_for_hist = {
        lid: {**lab, "high_value_proxy": bool(lab.get(win_key))} for lid, lab in labels.items()
    }
    history = build_creator_history(feats, labels_for_hist)
    enriched: list[dict[str, Any]] = []
    for row in feats:
        hist = history.get(row["creator"], [])
        row = dict(row)
        row["creator_prior_win_rate"] = prior_winner_rate(hist, row["first_liq_block"])
        lab = labels[row["launch_id"]]
        veto = vetoes.get(row["launch_id"])
        if veto:
            details = veto.get("details") or {}
            row["depth_usd"] = details.get("v7_tvl_usd")
            row["sell_recovery"] = details.get("v6_recovery")
            row["vetoed"] = bool(veto.get("vetoed"))
        else:
            row["vetoed"] = False
        if use_honest:
            row["label"] = bool(lab.get("executable_winner_250"))
            row["rug_proxy"] = bool(lab.get("rug"))
            row["gross_multiple"] = lab.get("gross_multiple")
        else:
            row["label"] = bool(lab.get("high_value_proxy"))
            if veto:
                details = veto.get("details") or {}
                row["rug_proxy"] = bool(
                    (isinstance(row.get("sell_recovery"), (int, float)) and row["sell_recovery"] < 0.5)
                    or (isinstance(row.get("depth_usd"), (int, float)) and row["depth_usd"] < 100)
                )
            else:
                row["rug_proxy"] = False
        score, parts = score_row(row)
        row["score"] = score
        row["score_parts"] = parts
        enriched.append(row)

    # Re-score after attaching depth/sellability so model_v0 matches survivor path.
    for row in enriched:
        score, parts = score_row(row)
        row["score"] = score
        row["score_parts"] = parts

    all_rows = enriched
    survivors = [r for r in enriched if not r["vetoed"] and r["launch_id"] in vetoes]

    report = {
        "decision_offset_sec": args.decision_offset,
        "label_field": args.label_field,
        "label_caveat": (
            "honest-v1 executable labels"
            if use_honest
            else "m0-proxy-v1 is circular with flow features; Phase 0 is diagnostic only"
        ),
        "finding_preview": None,
        "all": run_slice("all_labeled", all_rows, args.dev_fraction),
        "survivors": run_slice("veto_survivors", survivors, args.dev_fraction) if len(survivors) >= 25 else None,
    }

    # Headline finding: are all positives first-time creators?
    pos_priors = [r["creator_prior_launches"] for r in all_rows if r["label"]]
    report["finding_preview"] = {
        "n_positives": len(pos_priors),
        "positives_with_prior_0": sum(1 for p in pos_priors if p == 0),
        "positives_with_prior_gt_0": sum(1 for p in pos_priors if p > 0),
        "all_positives_are_first_time": bool(pos_priors) and all(p == 0 for p in pos_priors),
    }

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"[done] report -> {REPORT}")


if __name__ == "__main__":
    main()
