#!/usr/bin/env python3
"""Run Risk v2's frozen walk-forward persistence gauntlet.

The candidate is deliberately boring: one L2 logistic model per frozen target,
five pre-registered point-in-time features, quarterly refits, horizon embargoes,
and episode-weighted Brier scoring. A live probability is published only if all
four target/horizon endpoints beat both frozen baselines and every kill rule.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
from typing import Any
import warnings
from zoneinfo import ZoneInfo

import numpy as np
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "trading" / "risk-evaluation.json"
HISTORY_START = date(2013, 1, 1)
OOS_START = "2017-01-01"
HORIZONS = (21, 42)
TARGETS = ("vix_above_25", "spy_drawdown_5")
BOOTSTRAP_SEED = 20260725
BOOTSTRAP_RESAMPLES = 10_000
ET = ZoneInfo("America/New_York")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trading_risk_core as core  # noqa: E402

GENERATOR_SPEC = importlib.util.spec_from_file_location(
    "generate_trading_risk", Path(__file__).with_name("generate-trading-risk.py")
)
assert GENERATOR_SPEC is not None and GENERATOR_SPEC.loader is not None
risk_generator = importlib.util.module_from_spec(GENERATOR_SPEC)
GENERATOR_SPEC.loader.exec_module(risk_generator)

FEATURES = (
    {"name": "vix_pct", "description": "Trailing 756-observation VIX percentile, excluding today", "hard_cap": [0.01, 0.99]},
    {"name": "curve_slope", "description": "Constant-maturity VX 30-to-60-day percentage slope as a decimal", "hard_cap": [-0.25, 0.25]},
    {"name": "vvix_delta_5d", "description": "Five-session VVIX close change", "hard_cap": [-75.0, 75.0]},
    {"name": "vix9d_vix", "description": "VIX9D divided by VIX", "hard_cap": [0.50, 1.50]},
    {"name": "vrp", "description": "VIX less trailing 21-session annualized SPY realized volatility", "hard_cap": [-50.0, 50.0]},
)
FEATURE_NAMES = tuple(row["name"] for row in FEATURES)
FEATURE_HASH = hashlib.sha256(json.dumps(FEATURES, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def quarter_bounds(day: date) -> tuple[str, str]:
    quarter = (day.month - 1) // 3
    start_month = quarter * 3 + 1
    start = date(day.year, start_month, 1)
    if start_month == 10:
        end = date(day.year + 1, 1, 1)
    else:
        end = date(day.year, start_month + 3, 1)
    return start.isoformat(), end.isoformat()


def annualized_realized_vol(closes: list[float], index: int, window: int = 21) -> float | None:
    if index < window:
        return None
    values = closes[index - window:index + 1]
    if any(value <= 0 for value in values):
        return None
    returns = np.diff(np.log(np.asarray(values, dtype=float)))
    if len(returns) < 2:
        return None
    return float(np.std(returns, ddof=1) * math.sqrt(252) * 100)


def first_hit(
    vix: list[float], spy: list[float], sessions: list[str], *, index: int, horizon: int, target: str
) -> str | None:
    if index + horizon >= len(sessions):
        return None
    for future in range(index + 1, index + horizon + 1):
        if target == "vix_above_25" and vix[future] > 25:
            return sessions[future]
        if target == "spy_drawdown_5" and spy[future] <= spy[index] * 0.95:
            return sessions[future]
    return None


def build_feature_rows(end: date | None = None) -> tuple[list[dict[str, Any]], str]:
    today = datetime.now(ET).date()
    requested_end = min(end or today, today)
    names = ("vix", "vvix", "vix9d", "spy")
    with ThreadPoolExecutor(max_workers=len(names)) as executor:
        jobs = {
            name: executor.submit(
                risk_generator.yahoo_series,
                risk_generator.YAHOO_SYMBOLS[name],
                HISTORY_START,
                requested_end,
            )
            for name in names
        }
        series = {name: job.result() for name, job in jobs.items()}
    futures, _ = risk_generator.futures_history(HISTORY_START, requested_end)

    sessions = [row["date"] for row in series["vix"]]
    vix = [float(row["value"]) for row in series["vix"]]
    vix_map = dict(zip(sessions, vix))
    spy_map = {row["date"]: float(row["value"]) for row in series["spy"]}
    vvix_map = {row["date"]: float(row["value"]) for row in series["vvix"]}
    vix9d_map = {row["date"]: float(row["value"]) for row in series["vix9d"]}
    slope_map = {row["date"]: float(row["slope_percent"]) / 100 for row in futures}
    vix_percentiles = core.trailing_percentiles(vix)

    aligned_sessions = [day for day in sessions if day in spy_map]
    aligned_vix = [vix_map[day] for day in aligned_sessions]
    aligned_spy = [spy_map[day] for day in aligned_sessions]
    aligned_index = {day: index for index, day in enumerate(aligned_sessions)}
    session_index = {day: index for index, day in enumerate(sessions)}
    spy_closes_by_session = [spy_map.get(day, math.nan) for day in sessions]

    rows: list[dict[str, Any]] = []
    for index, day in enumerate(sessions):
        percentile = vix_percentiles[index]
        if day not in aligned_index or index < 21 or percentile is None:
            continue
        required_days = [day, sessions[index - 5]]
        if any(item not in vvix_map for item in required_days) or day not in vix9d_map or day not in slope_map:
            continue
        realized = annualized_realized_vol(spy_closes_by_session, index)
        if realized is None or not math.isfinite(realized):
            continue
        features = {
            "vix_pct": float(percentile) / 100,
            "curve_slope": slope_map[day],
            "vvix_delta_5d": vvix_map[day] - vvix_map[sessions[index - 5]],
            "vix9d_vix": vix9d_map[day] / vix_map[day],
            "vrp": vix_map[day] - realized,
        }
        if not all(math.isfinite(value) for value in features.values()):
            continue
        outcome_index = aligned_index[day]
        row: dict[str, Any] = {
            "date": day,
            "origin_index": session_index[day],
            "vix": vix_map[day],
            **features,
        }
        for horizon in HORIZONS:
            for target in TARGETS:
                hit = first_hit(
                    aligned_vix,
                    aligned_spy,
                    aligned_sessions,
                    index=outcome_index,
                    horizon=horizon,
                    target=target,
                )
                mature = outcome_index + horizon < len(aligned_sessions)
                key = f"{target}_{horizon}d"
                row[key] = None if not mature else int(hit is not None)
                row[f"{key}_first_hit"] = hit
                row[f"{key}_first_hit_index"] = session_index.get(hit) if hit else None
        rows.append(row)
    if not rows:
        raise RuntimeError("no complete point-in-time feature rows")
    return rows, sessions[-1]


def assign_blocks(rows: list[dict[str, Any]], target_key: str, horizon: int) -> dict[str, str]:
    """Assign positive first-hit episodes and non-overlapping calm horizon blocks."""
    ordered = sorted((row for row in rows if row.get(target_key) is not None), key=lambda row: row["origin_index"])
    hit_dates = sorted({
        row[f"{target_key}_first_hit"]
        for row in ordered
        if row.get(target_key) == 1 and row.get(f"{target_key}_first_hit")
    })
    hit_indexes = {
        row[f"{target_key}_first_hit"]: row.get(f"{target_key}_first_hit_index")
        for row in ordered
        if row.get(target_key) == 1 and row.get(f"{target_key}_first_hit")
    }
    # Synthetic tests and old receipts may omit the true trading-session index. Their fallback
    # still preserves ordering, while production rows always carry the exact VIX session index.
    all_dates = sorted({row["date"] for row in ordered} | {day for day in hit_dates if day})
    date_rank = {day: index for index, day in enumerate(all_dates)}
    hit_episode: dict[str, str] = {}
    episode = 0
    previous_rank: int | None = None
    for hit in hit_dates:
        if hit is None:
            continue
        rank = hit_indexes.get(hit)
        if rank is None:
            rank = date_rank[hit]
        if previous_rank is None or rank - previous_rank > horizon:
            episode += 1
        hit_episode[hit] = f"P{episode:03d}"
        previous_rank = rank

    blocks: dict[str, str] = {}
    calm_block = 0
    calm_count = 0
    previous_origin: int | None = None
    for row in ordered:
        if row[target_key] == 1:
            hit = row[f"{target_key}_first_hit"]
            blocks[row["date"]] = hit_episode[hit]
            continue
        if previous_origin is None or row["origin_index"] - previous_origin > 1 or calm_count >= horizon:
            calm_block += 1
            calm_count = 0
        calm_count += 1
        previous_origin = row["origin_index"]
        blocks[row["date"]] = f"N{calm_block:03d}"
    return blocks


def block_weights(rows: list[dict[str, Any]], target_key: str, horizon: int) -> np.ndarray:
    blocks = assign_blocks(rows, target_key, horizon)
    counts = Counter(blocks[row["date"]] for row in rows)
    return np.asarray([1 / counts[blocks[row["date"]]] for row in rows], dtype=float)


def feature_matrix(rows: list[dict[str, Any]]) -> np.ndarray:
    matrix = np.asarray([[float(row[name]) for name in FEATURE_NAMES] for row in rows], dtype=float)
    for column, spec in enumerate(FEATURES):
        low, high = spec["hard_cap"]
        matrix[:, column] = np.clip(matrix[:, column], low, high)
    return matrix


def fit_preprocessor(matrix: np.ndarray) -> dict[str, np.ndarray]:
    low = np.quantile(matrix, 0.01, axis=0)
    high = np.quantile(matrix, 0.99, axis=0)
    clipped = np.clip(matrix, low, high)
    mean = clipped.mean(axis=0)
    scale = clipped.std(axis=0)
    scale[scale == 0] = 1
    return {"low": low, "high": high, "mean": mean, "scale": scale}


def transform(matrix: np.ndarray, prep: dict[str, np.ndarray]) -> np.ndarray:
    return (np.clip(matrix, prep["low"], prep["high"]) - prep["mean"]) / prep["scale"]


def training_baselines(rows: list[dict[str, Any]], target_key: str, horizon: int) -> tuple[float, dict[str, float]]:
    y = np.asarray([row[target_key] for row in rows], dtype=float)
    weights = block_weights(rows, target_key, horizon)
    weighted_total = float(weights.sum())
    weighted_positives = float(np.dot(weights, y))
    unconditional = (weighted_positives + 0.5) / (weighted_total + 1)
    bins = {"low": (0.0, 0.5), "elevated": (0.5, 0.8), "high": (0.8, 1.0000001)}
    lookup: dict[str, float] = {}
    for name, (low, high) in bins.items():
        mask = np.asarray([low <= row["vix_pct"] < high for row in rows])
        n_bin = float(weights[mask].sum())
        if n_bin == 0:
            lookup[name] = unconditional
            continue
        raw = float(np.dot(weights[mask], y[mask]) / n_bin)
        lookup[name] = (n_bin * raw + 4 * unconditional) / (n_bin + 4)
    return unconditional, lookup


def vix_bin(value: float) -> str:
    return "low" if value < 0.5 else "elevated" if value < 0.8 else "high"


def walk_forward(rows: list[dict[str, Any]], target: str, horizon: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    target_key = f"{target}_{horizon}d"
    eligible = [row for row in rows if row[target_key] is not None]
    test_rows = [row for row in eligible if row["date"] >= OOS_START]
    quarters = sorted({quarter_bounds(date.fromisoformat(row["date"])) for row in test_rows})
    predictions: list[dict[str, Any]] = []
    folds: list[dict[str, Any]] = []
    for start, end in quarters:
        quarter_rows = [row for row in test_rows if start <= row["date"] < end]
        if not quarter_rows:
            continue
        first_origin = min(row["origin_index"] for row in quarter_rows)
        train = [
            row for row in eligible
            if row["date"] < start and row["origin_index"] + horizon < first_origin
        ]
        if len(train) < 252 or len({row[target_key] for row in train}) < 2:
            continue
        x_train = feature_matrix(train)
        x_test = feature_matrix(quarter_rows)
        y_train = np.asarray([row[target_key] for row in train], dtype=int)
        weights = block_weights(train, target_key, horizon)
        prep = fit_preprocessor(x_train)
        model = LogisticRegression(
            penalty="l2", C=0.25, solver="lbfgs", max_iter=1000, class_weight=None, random_state=BOOTSTRAP_SEED
        )
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                category=RuntimeWarning,
                module=r"sklearn\.linear_model\._linear_loss",
            )
            model.fit(transform(x_train, prep), y_train, sample_weight=weights)
        if not np.isfinite(model.coef_).all() or not np.isfinite(model.intercept_).all():
            raise RuntimeError(f"non-finite fitted coefficients for {target} {horizon} at {start}")
        p_model = model.predict_proba(transform(x_test, prep))[:, 1]
        if not np.isfinite(p_model).all():
            raise RuntimeError(f"non-finite OOS probabilities for {target} {horizon} at {start}")
        unconditional, lookup = training_baselines(train, target_key, horizon)
        for row, probability in zip(quarter_rows, p_model):
            predictions.append({
                "date": row["date"],
                "target": target,
                "horizon": horizon,
                "actual": row[target_key],
                "first_hit": row[f"{target_key}_first_hit"],
                "first_hit_index": row[f"{target_key}_first_hit_index"],
                "p_model": round(float(probability), 8),
                "p_unconditional": round(float(unconditional), 8),
                "p_vix_percentile": round(float(lookup[vix_bin(row["vix_pct"])]), 8),
                "vix_pct": round(float(row["vix_pct"]), 8),
                "origin_index": row["origin_index"],
            })
        folds.append({
            "target": target,
            "horizon": horizon,
            "test_start": start,
            "test_end_exclusive": end,
            "train_rows": len(train),
            "train_effective_blocks": round(float(weights.sum()), 4),
            "test_rows": len(quarter_rows),
            "p_unconditional": round(float(unconditional), 8),
            "vix_lookup": {name: round(float(value), 8) for name, value in lookup.items()},
        })
    return predictions, folds


def score_predictions(predictions: list[dict[str, Any]], target: str, horizon: int) -> dict[str, Any]:
    target_key = f"{target}_{horizon}d"
    rows = [{
        "date": row["date"],
        "origin_index": row["origin_index"],
        target_key: row["actual"],
        f"{target_key}_first_hit": row["first_hit"],
        f"{target_key}_first_hit_index": row.get("first_hit_index"),
        **row,
    } for row in predictions]
    blocks = assign_blocks(rows, target_key, horizon)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[blocks[row["date"]]].append(row)
    metric_names = ("model", "unconditional", "vix_percentile")
    field = {"model": "p_model", "unconditional": "p_unconditional", "vix_percentile": "p_vix_percentile"}
    daily_brier = {
        name: float(np.mean([(row[field[name]] - row["actual"]) ** 2 for row in rows]))
        for name in metric_names
    }
    block_errors: dict[str, dict[str, float]] = {}
    for block, members in grouped.items():
        block_errors[block] = {
            name: float(np.mean([(row[field[name]] - row["actual"]) ** 2 for row in members]))
            for name in metric_names
        }
    episode_brier = {
        name: float(np.mean([errors[name] for errors in block_errors.values()]))
        for name in metric_names
    }
    best_name = min(("unconditional", "vix_percentile"), key=lambda name: episode_brier[name])
    best = episode_brier[best_name]
    model = episode_brier["model"]
    improvement = best - model
    required = max(0.0025, best * 0.02)
    deltas = np.asarray([errors["model"] - errors[best_name] for errors in block_errors.values()])
    rng = np.random.default_rng(BOOTSTRAP_SEED + horizon + (0 if target == "vix_above_25" else 100))
    samples = rng.choice(deltas, size=(BOOTSTRAP_RESAMPLES, len(deltas)), replace=True).mean(axis=1)
    probability_better = float(np.mean(samples < 0))
    positive_blocks = [block for block in block_errors if block.startswith("P")]
    negative_blocks = [block for block in block_errors if block.startswith("N")]
    leave_deltas = []
    for held_out in positive_blocks:
        remaining = [value for block, value in zip(block_errors, deltas) if block != held_out]
        if remaining:
            leave_deltas.append(float(np.mean(remaining)))
    leave_one_pass = bool(leave_deltas) and max(leave_deltas) <= 0
    positive_delta = float(np.mean([block_errors[block]["model"] - block_errors[block][best_name] for block in positive_blocks])) if positive_blocks else None
    negative_delta = float(np.mean([block_errors[block]["model"] - block_errors[block][best_name] for block in negative_blocks])) if negative_blocks else None
    balance_pass = positive_delta is not None and negative_delta is not None and max(positive_delta, negative_delta) <= 0.0025
    criteria = {
        "beats_best_baseline": model < best,
        "minimum_improvement": improvement >= required,
        "bootstrap_probability_at_least_0_80": probability_better >= 0.80,
        "leave_one_positive_episode_out": leave_one_pass,
        "positive_and_calm_balance": balance_pass,
        "effective_sample": len(positive_blocks) >= 4 and len(block_errors) >= 20,
    }
    return {
        "target": target,
        "horizon": horizon,
        "observations": len(rows),
        "positive_event_episodes": len(positive_blocks),
        "calm_blocks": len(negative_blocks),
        "total_blocks": len(block_errors),
        "daily_brier": {name: round(value, 8) for name, value in daily_brier.items()},
        "episode_weighted_brier": {name: round(value, 8) for name, value in episode_brier.items()},
        "best_baseline": best_name,
        "absolute_improvement": round(improvement, 8),
        "required_improvement": round(required, 8),
        "relative_improvement": round(improvement / best, 8) if best else None,
        "bootstrap_probability_better": round(probability_better, 6),
        "leave_one_positive_max_delta": round(max(leave_deltas), 8) if leave_deltas else None,
        "positive_block_delta": round(positive_delta, 8) if positive_delta is not None else None,
        "calm_block_delta": round(negative_delta, 8) if negative_delta is not None else None,
        "criteria": criteria,
        "passed": all(criteria.values()),
        "blocks": [
            {"id": block, "kind": "positive_episode" if block.startswith("P") else "calm", "rows": len(grouped[block])}
            for block in sorted(grouped)
        ],
    }


def build(end: date | None = None) -> dict[str, Any]:
    rows, as_of = build_feature_rows(end)
    all_predictions: list[dict[str, Any]] = []
    all_folds: list[dict[str, Any]] = []
    scores: list[dict[str, Any]] = []
    for target in TARGETS:
        for horizon in HORIZONS:
            predictions, folds = walk_forward(rows, target, horizon)
            if not predictions:
                raise RuntimeError(f"no OOS predictions for {target} {horizon}")
            score = score_predictions(predictions, target, horizon)
            scores.append(score)
            all_predictions.extend(predictions)
            all_folds.extend(folds)
    shipped = all(score["passed"] for score in scores)
    failed = [
        f"{score['target']} {score['horizon']}d: " + ", ".join(name for name, passed in score["criteria"].items() if not passed)
        for score in scores if not score["passed"]
    ]
    status = {
        "status": "shipped" if shipped else "withheld",
        "message": "All four endpoints beat both persistence baselines under the frozen gauntlet." if shipped else "Fitted probabilities are withheld because at least one frozen endpoint failed the persistence gauntlet.",
        "reasons": failed,
        "live_probabilities": None,
    }
    return {
        "schema_version": 1,
        "as_of": as_of,
        "generated_at": datetime.combine(date.fromisoformat(as_of), time(16, 30), tzinfo=ET).isoformat(),
        "model_status": status,
        "manifest": {
            "name": "risk_v2_stage3_persistence_gauntlet",
            "oos_start": OOS_START,
            "refit_cadence": "quarterly_expanding",
            "horizons": list(HORIZONS),
            "targets": {
                "vix_above_25": "Any VIX close strictly above 25 in t+1 through t+H",
                "spy_drawdown_5": "Any SPY close at or below 95% of today's close in t+1 through t+H",
            },
            "feature_hash": FEATURE_HASH,
            "features": list(FEATURES),
            "model": {"class": "sklearn.linear_model.LogisticRegression", "penalty": "l2", "C": 0.25, "solver": "lbfgs", "class_weight": None},
            "preprocessing": "fixed hard caps; train-fold 1st/99th winsorization; train-fold standardization; no interactions or feature selection",
            "baselines": ["Jeffreys-smoothed episode-weighted unconditional", "three-bin VIX-percentile persistence with four-block shrinkage"],
            "decision_metric": "episode_weighted_brier",
            "bootstrap_seed": BOOTSTRAP_SEED,
            "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
            "kill_rule": "Every endpoint must beat the best baseline by max(0.0025 absolute, 2% relative), bootstrap P>=0.80, survive leave-one-positive-episode-out, balance positive/calm blocks, and have >=4 positive plus >=20 total OOS blocks.",
        },
        "feature_rows": len(rows),
        "scores": scores,
        "folds": all_folds,
        "oos_predictions": sorted(all_predictions, key=lambda row: (row["target"], row["horizon"], row["date"])),
    }


def serialize(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--end", help="YYYY-MM-DD cutoff, capped at today")
    parser.add_argument("--check", action="store_true", help="Evaluate without writing")
    args = parser.parse_args()
    end = date.fromisoformat(args.end) if args.end else None
    payload = build(end)
    rendered = serialize(payload)
    changed = not OUTPUT.exists() or OUTPUT.read_text() != rendered
    if not args.check:
        temporary = OUTPUT.with_suffix(".json.tmp")
        temporary.write_text(rendered)
        os.replace(temporary, OUTPUT)
    summary = {
        "as_of": payload["as_of"],
        "changed": changed,
        "feature_hash": FEATURE_HASH[:12],
        "feature_rows": payload["feature_rows"],
        "model_status": payload["model_status"]["status"],
        "scores": [{
            "target": row["target"],
            "horizon": row["horizon"],
            "model_brier": row["episode_weighted_brier"]["model"],
            "best_baseline": row["best_baseline"],
            "best_baseline_brier": row["episode_weighted_brier"][row["best_baseline"]],
            "passed": row["passed"],
        } for row in payload["scores"]],
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
