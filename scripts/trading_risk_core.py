#!/usr/bin/env python3
"""Pure point-in-time math for Zonted's public market-risk dashboard.

No network or file I/O belongs here.  The public generator, scanner renderer, and
research evaluators share these functions so scoring and outcome definitions
cannot drift silently.
"""
from __future__ import annotations

import bisect
import math
from typing import Any, Iterable, Sequence

PERCENTILE_WINDOW = 756
PERCENTILE_MINIMUM = 252
STALE_AFTER_SESSIONS = 2
COMPONENT_WEIGHTS = {
    "vvix": 25,
    "curve": 25,
    "move": 15,
    "skew": 10,
    "hy_oas": 25,
}
HORIZONS = (21, 42)


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def percentile_rank(history: Iterable[float], current: float) -> float:
    """Return an empirical percentile using midranks for ties."""
    clean = [float(value) for value in history if _finite(value)]
    if not clean or not _finite(current):
        raise ValueError("percentile rank needs finite history and current value")
    value = float(current)
    lower = sum(item < value for item in clean)
    equal = sum(item == value for item in clean)
    return round((lower + 0.5 * equal) / len(clean) * 100, 2)


def trailing_percentiles(
    values: Sequence[float | None],
    *,
    window: int = PERCENTILE_WINDOW,
    minimum: int = PERCENTILE_MINIMUM,
) -> list[float | None]:
    """Percentile of each value against prior observations only."""
    if window < minimum or minimum < 1:
        raise ValueError("percentile window must be at least the positive minimum")
    output: list[float | None] = []
    for index, value in enumerate(values):
        prior = [float(item) for item in values[max(0, index - window):index] if item is not None and _finite(item)]
        if value is None or not _finite(value) or len(prior) < minimum:
            output.append(None)
        else:
            output.append(percentile_rank(prior, float(value)))
    return output


def session_age(source_date: str, reference_date: str, sessions: list[str]) -> int:
    """Count completed reference sessions after source_date through reference_date."""
    ordered = sorted(set(sessions))
    if reference_date not in ordered:
        raise ValueError(f"reference date {reference_date} is not in the session calendar")
    source_position = bisect.bisect_right(ordered, source_date) - 1
    if source_position < 0:
        return len(ordered)
    return max(0, ordered.index(reference_date) - source_position)


def is_stale(
    source_date: str,
    reference_date: str,
    sessions: list[str],
    *,
    maximum_age: int = STALE_AFTER_SESSIONS,
) -> bool:
    return session_age(source_date, reference_date, sessions) > maximum_age


def lag_to_next_session(rows: list[dict[str, Any]], sessions: list[str]) -> list[dict[str, Any]]:
    """Make each observation usable on the next completed market session."""
    ordered = sorted(set(sessions))
    shifted: list[dict[str, Any]] = []
    for row in rows:
        observation_date = str(row["date"])
        index = bisect.bisect_right(ordered, observation_date)
        if index >= len(ordered):
            continue
        shifted.append({
            "date": ordered[index],
            "observation_date": observation_date,
            "value": float(row["value"]),
        })
    return shifted


def _interpolate(contracts: list[dict[str, float]], target_days: int) -> float:
    ordered = sorted(
        ({"days": int(row["days"]), "value": float(row["value"])} for row in contracts),
        key=lambda row: row["days"],
    )
    if len(ordered) < 2:
        raise ValueError("constant maturity needs at least two contracts")
    for row in ordered:
        if row["days"] == target_days:
            return row["value"]
    lower = [row for row in ordered if row["days"] < target_days]
    upper = [row for row in ordered if row["days"] > target_days]
    if not lower or not upper:
        raise ValueError(f"contracts do not bracket {target_days} days")
    left, right = lower[-1], upper[0]
    fraction = (target_days - left["days"]) / (right["days"] - left["days"])
    return left["value"] + fraction * (right["value"] - left["value"])


def constant_maturity_curve(contracts: list[dict[str, float]]) -> dict[str, float]:
    cm30 = round(_interpolate(contracts, 30), 4)
    cm60 = round(_interpolate(contracts, 60), 4)
    if cm30 <= 0 or cm60 <= 0:
        raise ValueError("constant-maturity values must be positive")
    return {
        "cm30": cm30,
        "cm60": cm60,
        # Slope from the rounded values so the published triple stays self-consistent.
        "slope_percent": round((cm60 / cm30 - 1) * 100, 4),
    }


def metric_changes(values: list[float | None], *, higher_is_risk: bool = True) -> dict[str, Any]:
    clean = [float(value) for value in values if _finite(value)]
    if not clean:
        return {"change_5d": None, "change_20d": None, "direction": "unavailable"}
    current = clean[-1]
    change_5d = round(current - clean[-6], 4) if len(clean) >= 6 else None
    change_20d = round(current - clean[-21], 4) if len(clean) >= 21 else None
    signed_changes = [value if higher_is_risk else -value for value in (change_5d, change_20d) if value is not None]
    if not signed_changes:
        direction = "stable"
    elif all(value > 0 for value in signed_changes):
        direction = "deteriorating"
    elif all(value < 0 for value in signed_changes):
        direction = "improving"
    else:
        direction = "mixed"
    return {"change_5d": change_5d, "change_20d": change_20d, "direction": direction}


def _risk_band_points(risk_percentile: float, maximum: int) -> float:
    if risk_percentile < 60:
        return 0.0
    if risk_percentile <= 85:
        return maximum / 2
    return float(maximum)


def _normalized_values(raw: dict[str, float], total: float) -> dict[str, float]:
    if not raw:
        return {}
    output = {name: round(value, 2) for name, value in raw.items()}
    difference = round(total - sum(output.values()), 2)
    if difference:
        target = max(raw, key=lambda name: raw[name])
        output[target] = round(output[target] + difference, 2)
    return output


def conditions_score(metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Score percentile conditions, excluding stale/unavailable components.

    Active weights are normalized to 100.  Component contributions therefore
    sum exactly to the displayed total even when an input is stale.
    """
    raw_points: dict[str, float] = {}
    active_weights: dict[str, float] = {}
    states: dict[str, dict[str, Any]] = {}
    for name, maximum in COMPONENT_WEIGHTS.items():
        metric = metrics.get(name) or {}
        percentile = metric.get("risk_percentile")
        percentile_value = float(percentile) if isinstance(percentile, (int, float)) and not isinstance(percentile, bool) and math.isfinite(float(percentile)) else None
        active = percentile_value is not None and not bool(metric.get("stale"))
        raw = _risk_band_points(percentile_value, maximum) if percentile_value is not None and active else 0.0
        states[name] = {
            "active": active,
            "stale": bool(metric.get("stale")),
            "risk_percentile": round(percentile_value, 2) if percentile_value is not None else None,
            "raw_points": raw,
            "raw_maximum": maximum,
        }
        if active:
            raw_points[name] = raw
            active_weights[name] = float(maximum)

    active_maximum = int(sum(active_weights.values()))
    if not active_maximum:
        total = 0
        contributions: dict[str, float] = {}
        maxima: dict[str, float] = {}
    else:
        unrounded = {name: value / active_maximum * 100 for name, value in raw_points.items()}
        total = round(sum(unrounded.values()), 2)
        contributions = _normalized_values(unrounded, total)
        maxima = _normalized_values(
            {name: value / active_maximum * 100 for name, value in active_weights.items()},
            100.0,
        )

    components: dict[str, dict[str, Any]] = {}
    for name in COMPONENT_WEIGHTS:
        state = states[name]
        components[name] = {
            **state,
            "points": contributions.get(name, 0.0),
            "maximum": maxima.get(name, 0.0),
        }
    label = "Contained" if total < 25 else "Watchful" if total < 50 else "Elevated"
    return {
        "total": total,
        "label": label,
        "active_maximum": active_maximum,
        "components": components,
        "rules": [
            "Each metric is ranked against its prior 756 available observations; today's value is excluded.",
            "Risk percentile <60 = 0, 60–85 = half weight, >85 = full weight.",
            "Weights: VVIX 25, constant-maturity curve 25, MOVE 15, SKEW 10, HY OAS 25.",
            "Inputs older than two completed VIX sessions receive zero weight; active weights normalize to 100.",
            "Regime: <25 Contained, 25–49 Watchful, 50+ Elevated.",
        ],
    }


def forward_targets(
    vix_values: list[float],
    spy_values: list[float],
    *,
    index: int,
    horizon: int,
) -> dict[str, Any]:
    if index < 0 or horizon < 1 or index >= len(vix_values) or index >= len(spy_values):
        raise ValueError("invalid target index or horizon")
    end = index + horizon + 1
    if end > len(vix_values) or end > len(spy_values):
        return {
            "complete": False,
            "vix_above_25": None,
            "spy_drawdown_5": None,
            "spy_max_drawdown_percent": None,
        }
    future_vix = [float(value) for value in vix_values[index + 1:end]]
    future_spy = [float(value) for value in spy_values[index + 1:end]]
    start_spy = float(spy_values[index])
    drawdown = (min(future_spy) / start_spy - 1) * 100
    return {
        "complete": True,
        "vix_above_25": any(value > 25 for value in future_vix),
        "spy_drawdown_5": drawdown <= -5,
        "spy_max_drawdown_percent": round(drawdown, 4),
    }


def band_for_score(score: int | float) -> str:
    value = float(score)
    return "Contained" if value < 25 else "Watchful" if value < 50 else "Elevated"


def conditional_frequencies(rows: list[dict[str, Any]], horizons: tuple[int, ...] = HORIZONS) -> dict[str, Any]:
    """Summarize frozen outcomes by score band and against base rates."""
    result: dict[str, Any] = {"horizons": list(horizons), "targets": {}}
    for target in ("vix_above_25", "spy_drawdown_5"):
        target_result: dict[str, Any] = {}
        for horizon in horizons:
            key = f"{target}_{horizon}d"
            eligible = [row for row in rows if row.get(key) is not None and row.get("score") is not None]
            positives = sum(bool(row[key]) for row in eligible)
            summary = {
                "observations": len(eligible),
                "events": positives,
                "frequency": round(positives / len(eligible) * 100, 2) if eligible else None,
                "bands": {},
            }
            for band in ("Contained", "Watchful", "Elevated"):
                selected = [row for row in eligible if row.get("regime") == band]
                events = sum(bool(row[key]) for row in selected)
                summary["bands"][band] = {
                    "observations": len(selected),
                    "events": events,
                    "frequency": round(events / len(selected) * 100, 2) if selected else None,
                }
            target_result[str(horizon)] = summary
        result["targets"][target] = target_result
    return result


def gate_policy(frequencies: dict[str, Any]) -> dict[str, Any]:
    """Enable an Elevated hard gate only on repeated, monotonic separation."""
    evidence: list[dict[str, Any]] = []
    qualifying = 0
    for target, horizons in frequencies.get("targets", {}).items():
        target_qualifies = True
        target_rows = []
        for horizon in HORIZONS:
            summary = horizons.get(str(horizon)) or {}
            bands = summary.get("bands") or {}
            values = [bands.get(name, {}).get("frequency") for name in ("Contained", "Watchful", "Elevated")]
            base = summary.get("frequency")
            monotonic = all(value is not None for value in values) and values[0] <= values[1] <= values[2]
            above_base = values[2] is not None and base is not None and values[2] > base
            target_rows.append({"horizon": horizon, "monotonic": monotonic, "elevated_above_base": above_base})
            target_qualifies = target_qualifies and monotonic and above_base
        if target_qualifies:
            qualifying += 1
        evidence.append({"target": target, "qualifies": target_qualifies, "horizons": target_rows})
    enabled = qualifying > 0
    return {
        "hard_gate_enabled": enabled,
        "watchful_action": "annotate_half_size",
        "elevated_action": "gate" if enabled else "shadow_gate",
        "reason": "At least one frozen target separates monotonically and exceeds base rate at both horizons." if enabled else "Stage-1 bands did not clear the pre-registered separation rule; Elevated remains a shadow gate.",
        "evidence": evidence,
    }
