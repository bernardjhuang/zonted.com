#!/usr/bin/env python3
"""Generate Zonted's auditable forward-market-risk conditions dataset.

Public sources:
- Yahoo Finance chart API: VIX, VVIX, MOVE, SKEW, VIX9D, VIX3M, SPY
- Cboe official monthly VX contract settlement files
- FRED BAMLH0A0HYM2, shifted to its next-session publication availability

The output keeps YTD chart payloads small while carrying a 2013-present score
history and frozen 21/42-session conditional outcome frequencies.
"""
from __future__ import annotations

import argparse
import bisect
import calendar
import csv
import hashlib
import io
import json
import math
import os
import re
import sys
import tempfile
import time as sleep_time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import trading_risk_core as core  # noqa: E402

ROOT = SCRIPT_DIR.parent
OUTPUT = ROOT / "trading" / "risk-ytd.json"
EVALUATION = ROOT / "trading" / "risk-evaluation.json"
PAGE = ROOT / "trading" / "index.html"
RISK_JS = ROOT / "js" / "trading-risk.js"
RISK_CSS = ROOT / "css" / "trading-risk.css"
ET = ZoneInfo("America/New_York")
USER_AGENT = "zonted-risk-dashboard/2.0 hello@veracityapi.com"
HISTORY_START = date(2013, 1, 1)
CACHE_DIR = Path.home() / ".cache" / "zonted-risk" / "vx"
YAHOO_SYMBOLS = {
    "vix": "^VIX",
    "vvix": "^VVIX",
    "move": "^MOVE",
    "skew": "^SKEW",
    "vix9d": "^VIX9D",
    "vix3m": "^VIX3M",
    "spy": "SPY",
}


def nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (occurrence - 1))


def easter_sunday(year: int) -> date:
    """Anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def observed_fixed(day: date) -> date:
    if day.weekday() == calendar.SATURDAY:
        return day - timedelta(days=1)
    if day.weekday() == calendar.SUNDAY:
        return day + timedelta(days=1)
    return day


def market_holidays(year: int) -> set[date]:
    thanksgiving = nth_weekday(year, 11, calendar.THURSDAY, 4)
    memorial = date(year, 5, 31)
    while memorial.weekday() != calendar.MONDAY:
        memorial -= timedelta(days=1)
    holidays = {
        observed_fixed(date(year, 1, 1)),
        nth_weekday(year, 1, calendar.MONDAY, 3),
        nth_weekday(year, 2, calendar.MONDAY, 3),
        easter_sunday(year) - timedelta(days=2),
        memorial,
        observed_fixed(date(year, 7, 4)),
        nth_weekday(year, 9, calendar.MONDAY, 1),
        thanksgiving,
        observed_fixed(date(year, 12, 25)),
    }
    if year >= 2022:
        holidays.add(observed_fixed(date(year, 6, 19)))
    return holidays


def vx_monthly_expiration(year: int, month: int) -> date:
    """VIX monthly settlement: 30 days before the next SPX monthly expiry."""
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    spx_expiry = nth_weekday(next_year, next_month, calendar.FRIDAY, 3)
    holidays = market_holidays(next_year)
    while spx_expiry.weekday() >= calendar.SATURDAY or spx_expiry in holidays:
        spx_expiry -= timedelta(days=1)
    expiry = spx_expiry - timedelta(days=30)
    holidays = market_holidays(expiry.year)
    while expiry.weekday() >= calendar.SATURDAY or expiry in holidays:
        expiry -= timedelta(days=1)
    return expiry


def vx_expirations_for_window(start: date, end: date) -> list[str]:
    expirations: list[str] = []
    cursor = date(start.year, start.month, 1)
    horizon = end + timedelta(days=240)
    while cursor <= horizon:
        expiry = vx_monthly_expiration(cursor.year, cursor.month)
        if expiry > start and expiry <= horizon:
            expirations.append(expiry.isoformat())
        cursor = date(cursor.year + 1, 1, 1) if cursor.month == 12 else date(cursor.year, cursor.month + 1, 1)
    return expirations


def request_bytes(url: str, *, timeout: int = 60, attempts: int = 3) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/csv,*/*"},
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as error:
            last_error = error
            if attempt + 1 < attempts:
                sleep_time.sleep(0.5 * (2 ** attempt))
    raise RuntimeError(f"request failed after {attempts} attempts: {url}") from last_error


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def yahoo_series(symbol: str, start: date, end: date) -> list[dict[str, Any]]:
    start_epoch = int(datetime.combine(start, time.min, timezone.utc).timestamp())
    end_epoch = int(datetime.combine(end + timedelta(days=1), time.min, timezone.utc).timestamp())
    query = urllib.parse.urlencode({
        "period1": start_epoch,
        "period2": end_epoch,
        "interval": "1d",
        "events": "history",
    })
    encoded = urllib.parse.quote(symbol, safe="")
    payload = json.loads(request_bytes(f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?{query}"))
    result = payload.get("chart", {}).get("result") or []
    if not result:
        raise RuntimeError(f"Yahoo returned no history for {symbol}")
    timestamps = result[0].get("timestamp") or []
    closes = (result[0].get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    rows: list[dict[str, Any]] = []
    for stamp, close in zip(timestamps, closes):
        if close is None or not math.isfinite(float(close)):
            continue
        day = datetime.fromtimestamp(int(stamp), ET).date()
        if start <= day <= end:
            rows.append({"date": day.isoformat(), "value": round(float(close), 4)})
    deduped = {row["date"]: row for row in rows}
    result_rows = [deduped[key] for key in sorted(deduped)]
    if not result_rows:
        raise RuntimeError(f"Yahoo returned no usable closes for {symbol}")
    return result_rows


def _contract_bytes(expiration: str) -> bytes:
    expiry = date.fromisoformat(expiration)
    cache_path = CACHE_DIR / f"VX_{expiration}.csv"
    if expiry < datetime.now(ET).date() and cache_path.exists():
        return cache_path.read_bytes()
    url = f"https://cdn.cboe.com/data/us/futures/market_statistics/historical_data/VX/VX_{expiration}.csv"
    data = request_bytes(url)
    if expiry < datetime.now(ET).date():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=cache_path.name + ".", dir=CACHE_DIR)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
            os.replace(temporary, cache_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return data


def cboe_contract(expiration: str, start: date, end: date) -> list[dict[str, Any]]:
    text = _contract_bytes(expiration).decode("utf-8-sig")
    rows: list[dict[str, Any]] = []
    for row in csv.DictReader(io.StringIO(text)):
        raw_day = (row.get("Trade Date") or "").strip()
        raw_settle = (row.get("Settle") or "").strip().replace(",", "")
        if not raw_day or not raw_settle:
            continue
        day = date.fromisoformat(raw_day)
        if not start <= day <= end:
            continue
        try:
            settle = float(raw_settle)
        except ValueError:
            continue
        if math.isfinite(settle) and settle > 0:
            rows.append({"date": day.isoformat(), "value": round(settle, 4)})
    return rows


def futures_history(start: date, end: date) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    expirations = vx_expirations_for_window(start, end)
    by_expiration: dict[str, list[dict[str, Any]]] = {}
    failures: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        jobs = {executor.submit(cboe_contract, expiration, start, end): expiration for expiration in expirations}
        for future in as_completed(jobs):
            expiration = jobs[future]
            try:
                by_expiration[expiration] = future.result()
            except Exception as error:  # future listed contracts can be unavailable before Cboe publishes them
                failures[expiration] = str(error)
    past_failures = [expiration for expiration in failures if date.fromisoformat(expiration) <= end]
    if past_failures:
        raise RuntimeError(f"Cboe contract history missing for expired contracts: {past_failures[:5]}")

    observations: dict[str, list[tuple[date, float]]] = {}
    for expiration, rows in by_expiration.items():
        expiry = date.fromisoformat(expiration)
        for row in rows:
            observations.setdefault(row["date"], []).append((expiry, float(row["value"])))

    history: list[dict[str, Any]] = []
    for day_text in sorted(observations):
        day = date.fromisoformat(day_text)
        contracts = sorted((expiry, value) for expiry, value in observations[day_text] if expiry > day)
        if len(contracts) < 3:
            continue
        maturity_inputs = [{"days": (expiry - day).days, "value": value} for expiry, value in contracts]
        try:
            constant = core.constant_maturity_curve(maturity_inputs)
        except ValueError:
            continue
        m1_expiry, m1 = contracts[0]
        m2_expiry, m2 = contracts[1]
        history.append({
            "date": day_text,
            "m1": round(m1, 4),
            "m2": round(m2, 4),
            "spread": round(m2 - m1, 4),
            "spread_percent": round((m2 / m1 - 1) * 100, 3),
            "m1_expiration": m1_expiry.isoformat(),
            "m2_expiration": m2_expiry.isoformat(),
            **constant,
        })
    if not history:
        raise RuntimeError("Cboe returned no usable constant-maturity history")
    return history, by_expiration


def latest_curve(as_of: date, vix: float, contracts: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = [{"label": "Spot", "expiration": None, "value": round(vix, 4)}]
    available: list[tuple[date, float]] = []
    for expiration, history in contracts.items():
        expiry = date.fromisoformat(expiration)
        if expiry <= as_of:
            continue
        value_by_day = {row["date"]: float(row["value"]) for row in history}
        eligible = [day for day in value_by_day if day <= as_of.isoformat()]
        if eligible:
            available.append((expiry, value_by_day[max(eligible)]))
    for index, (expiry, value) in enumerate(sorted(available)[:6], 1):
        rows.append({"label": f"M{index}", "expiration": expiry.isoformat(), "value": round(value, 4)})
    if len(rows) != 7:
        raise RuntimeError(f"Cboe current curve has {len(rows) - 1} monthly contracts; expected 6")
    return rows


def fred_series(series_id: str, start: date, api_key: str | None) -> list[dict[str, Any]]:
    if not api_key:
        raise RuntimeError("FRED_API_KEY or FRED_KEY is required for point-in-time credit history")
    query = urllib.parse.urlencode({
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start.isoformat(),
        "sort_order": "asc",
    })
    payload = json.loads(request_bytes(f"https://api.stlouisfed.org/fred/series/observations?{query}"))
    rows = []
    for observation in payload.get("observations") or []:
        if observation.get("value") == ".":
            continue
        rows.append({"date": observation["date"], "value": round(float(observation["value"]), 4)})
    if not rows:
        raise RuntimeError(f"FRED returned no observations for {series_id}")
    return rows


def _change_metadata(values: list[float], index: int, *, higher_is_risk: bool) -> dict[str, Any]:
    current = values[index]
    change_5d = round(current - values[index - 5], 4) if index >= 5 else None
    change_20d = round(current - values[index - 20], 4) if index >= 20 else None
    adjusted = [value if higher_is_risk else -value for value in (change_5d, change_20d) if value is not None]
    if not adjusted:
        direction = "stable"
    elif all(value > 0 for value in adjusted):
        direction = "deteriorating"
    elif all(value < 0 for value in adjusted):
        direction = "improving"
    else:
        direction = "mixed"
    return {"change_5d": change_5d, "change_20d": change_20d, "direction": direction}


def metric_states(
    rows: list[dict[str, Any]],
    sessions: list[str],
    *,
    value_key: str = "value",
    higher_is_risk: bool = True,
) -> dict[str, dict[str, Any]]:
    ordered = sorted(rows, key=lambda row: row["date"])
    values = [float(row[value_key]) for row in ordered]
    percentiles = core.trailing_percentiles(values)
    by_session: dict[str, dict[str, Any]] = {}
    pointer = -1
    for session_index, session in enumerate(sessions):
        while pointer + 1 < len(ordered) and ordered[pointer + 1]["date"] <= session:
            pointer += 1
        if pointer < 0:
            continue
        row = ordered[pointer]
        source_session = bisect.bisect_right(sessions, row["date"]) - 1
        age = session_index - source_session if source_session >= 0 else len(sessions)
        percentile = percentiles[pointer]
        risk_percentile = None if percentile is None else percentile if higher_is_risk else round(100 - percentile, 2)
        by_session[session] = {
            "value": values[pointer],
            "source_date": row["date"],
            "observation_date": row.get("observation_date", row["date"]),
            "percentile": percentile,
            "risk_percentile": risk_percentile,
            "age_sessions": age,
            "stale": age > core.STALE_AFTER_SESSIONS,
            **_change_metadata(values, pointer, higher_is_risk=higher_is_risk),
        }
    return by_session


def ratio_series(
    numerator: list[dict[str, Any]],
    denominator: list[dict[str, Any]],
    *,
    multiply: float = 1.0,
) -> list[dict[str, Any]]:
    left = {row["date"]: float(row["value"]) for row in numerator}
    right = {row["date"]: float(row["value"]) for row in denominator}
    return [
        {"date": day, "value": round(left[day] / right[day] * multiply, 4)}
        for day in sorted(set(left) & set(right)) if right[day] != 0
    ]


def current_band(metric: str, value: float) -> str:
    if metric == "vix":
        return "Low" if value < 15 else "Moderate" if value < 20 else "Elevated" if value < 25 else "High"
    if metric == "vvix":
        return "Calm" if value < 90 else "Elevated" if value <= 110 else "High"
    if metric == "move":
        return "Calm" if value < 80 else "Elevated" if value <= 100 else "High"
    if metric == "skew":
        return "Low" if value < 130 else "Moderate" if value <= 145 else "Elevated"
    raise KeyError(metric)


def contiguous_windows(series: list[dict[str, Any]], predicate) -> list[dict[str, str]]:
    selected = [date.fromisoformat(row["date"]) for row in series if predicate(float(row["value"]))]
    if not selected:
        return []
    windows: list[list[date]] = [[selected[0]]]
    for day in selected[1:]:
        if (day - windows[-1][-1]).days <= 4:
            windows[-1].append(day)
        else:
            windows.append([day])
    return [{"start": group[0].isoformat(), "end": group[-1].isoformat()} for group in windows]


def commentary(current: dict[str, Any], score: dict[str, Any]) -> list[str]:
    metrics = current["metrics"]
    curve = metrics["curve"]
    stale = [name.upper().replace("HY_OAS", "HY OAS") for name, row in metrics.items() if row.get("stale")]
    stale_text = f" Stale inputs receive zero weight: {', '.join(stale)}." if stale else ""
    return [
        f"Overall regime: {score['label']} ({score['total']}/100). This is a percentile-based conditions score, not a forecast.",
        f"VVIX is {current['vvix']:.2f} at its trailing percentile {metrics['vvix']['percentile']:.0f}; its 5-session direction is {metrics['vvix']['direction']}.",
        f"The constant-maturity 30-to-60-day VIX curve slope is {curve['value']:+.2f}%; its direction is {curve['direction']} and positive still means contango.",
        f"Credit is {current['hy_oas']:.2f}% and {metrics['hy_oas']['direction']}; MOVE is {current['move']:.2f}. SKEW remains a low-weight confirm, not a standalone forecast.{stale_text}",
    ]


def evaluation_status(as_of: str) -> dict[str, Any]:
    if not EVALUATION.exists():
        return {
            "status": "not_evaluated",
            "message": "No fitted forecast is published until it beats unconditional and VIX-persistence baselines out of sample.",
        }
    raw = EVALUATION.read_bytes()
    payload = json.loads(raw)
    if payload.get("schema_version") != 1 or payload.get("as_of") != as_of:
        return {
            "status": "not_evaluated",
            "message": "The last persistence-gauntlet receipt does not match the current completed session.",
        }
    status = dict(payload["model_status"])
    status["evaluation_digest"] = hashlib.sha256(raw).hexdigest()[:12]
    status["evaluation_url"] = "/trading/risk-evaluation.json"
    status["endpoints_passed"] = sum(bool(row["passed"]) for row in payload["scores"])
    status["endpoints_total"] = len(payload["scores"])
    status["scores"] = [{
        "target": row["target"],
        "horizon": row["horizon"],
        "model_brier": row["episode_weighted_brier"]["model"],
        "best_baseline": row["best_baseline"],
        "best_baseline_brier": row["episode_weighted_brier"][row["best_baseline"]],
        "passed": row["passed"],
    } for row in payload["scores"]]
    return status


def build(end: date | None = None) -> dict[str, Any]:
    today = datetime.now(ET).date()
    requested_end = min(end or today, today)
    display_start = date(requested_end.year, 1, 1)

    with ThreadPoolExecutor(max_workers=len(YAHOO_SYMBOLS)) as executor:
        yahoo_jobs = {name: executor.submit(yahoo_series, symbol, HISTORY_START, requested_end) for name, symbol in YAHOO_SYMBOLS.items()}
        indices = {name: job.result() for name, job in yahoo_jobs.items()}
    futures, contracts = futures_history(HISTORY_START, requested_end)

    env = load_env(Path.home() / ".hermes" / ".env")
    credit_observations = fred_series("BAMLH0A0HYM2", HISTORY_START, env.get("FRED_API_KEY") or env.get("FRED_KEY"))
    sessions = [row["date"] for row in indices["vix"]]
    credit_available = core.lag_to_next_session(credit_observations, sessions)
    vix9d_ratio = ratio_series(indices["vix9d"], indices["vix"])
    vix3m_ratio = ratio_series(indices["vix"], indices["vix3m"])

    states = {
        "vvix": metric_states(indices["vvix"], sessions),
        "curve": metric_states(futures, sessions, value_key="slope_percent", higher_is_risk=False),
        "move": metric_states(indices["move"], sessions),
        "skew": metric_states(indices["skew"], sessions),
        "hy_oas": metric_states(credit_available, sessions),
    }
    context_states = {
        "vix": metric_states(indices["vix"], sessions),
        "vix9d_vix": metric_states(vix9d_ratio, sessions),
        "vix_vix3m": metric_states(vix3m_ratio, sessions),
    }
    dashboard_as_of = date.fromisoformat(indices["vix"][-1]["date"])
    as_of = dashboard_as_of.isoformat()
    latest_metrics = {name: rows[as_of] for name, rows in states.items() if as_of in rows}
    if set(latest_metrics) != set(core.COMPONENT_WEIGHTS):
        raise RuntimeError(f"current risk inputs are incomplete: {sorted(latest_metrics)}")
    score = core.conditions_score(latest_metrics)
    if score["active_maximum"] < 60:
        raise RuntimeError("current conditions score has insufficient active weight")

    score_history: list[dict[str, Any]] = []
    for session in sessions:
        available = {name: rows[session] for name, rows in states.items() if session in rows}
        daily_score = core.conditions_score(available)
        if daily_score["active_maximum"] < 60:
            continue
        score_history.append({
            "date": session,
            "score": daily_score["total"],
            "regime": daily_score["label"],
            "active_maximum": daily_score["active_maximum"],
        })

    score_by_date = {row["date"]: row for row in score_history}
    spy_map = {row["date"]: float(row["value"]) for row in indices["spy"]}
    vix_map = {row["date"]: float(row["value"]) for row in indices["vix"]}
    outcome_sessions = [day for day in sessions if day in spy_map]
    aligned_vix = [vix_map[day] for day in outcome_sessions]
    aligned_spy = [spy_map[day] for day in outcome_sessions]
    outcome_rows: list[dict[str, Any]] = []
    for index, session in enumerate(outcome_sessions):
        score_row = score_by_date.get(session)
        if not score_row:
            continue
        row = dict(score_row)
        for horizon in core.HORIZONS:
            target = core.forward_targets(aligned_vix, aligned_spy, index=index, horizon=horizon)
            row[f"vix_above_25_{horizon}d"] = target["vix_above_25"]
            row[f"spy_drawdown_5_{horizon}d"] = target["spy_drawdown_5"]
        outcome_rows.append(row)
    frequencies = core.conditional_frequencies(outcome_rows)
    policy = core.gate_policy(frequencies)

    latest_future = max((row for row in futures if row["date"] <= as_of), key=lambda row: row["date"])
    curve = latest_curve(dashboard_as_of, float(indices["vix"][-1]["value"]), contracts)
    current: dict[str, Any] = {
        "vix": float(indices["vix"][-1]["value"]),
        "vvix": latest_metrics["vvix"]["value"],
        "move": latest_metrics["move"]["value"],
        "skew": latest_metrics["skew"]["value"],
        "dates": {
            "vix": indices["vix"][-1]["date"],
            "vvix": latest_metrics["vvix"]["source_date"],
            "move": latest_metrics["move"]["source_date"],
            "skew": latest_metrics["skew"]["source_date"],
        },
        "m1": float(latest_future["m1"]),
        "m2": float(latest_future["m2"]),
        "curve_spread": float(latest_future["spread"]),
        "curve_spread_percent": float(latest_future["spread_percent"]),
        "curve_cm30": float(latest_future["cm30"]),
        "curve_cm60": float(latest_future["cm60"]),
        "curve_slope_percent": float(latest_future["slope_percent"]),
        "curve_as_of": latest_future["date"],
        "hy_oas": latest_metrics["hy_oas"]["value"],
        "hy_oas_as_of": latest_metrics["hy_oas"]["observation_date"],
        "hy_oas_available_as_of": latest_metrics["hy_oas"]["source_date"],
        "metrics": latest_metrics,
        "context_metrics": {name: rows[as_of] for name, rows in context_states.items()},
    }
    current["bands"] = {name: current_band(name, current[name]) for name in ("vix", "vvix", "move", "skew")}
    current["curve_band"] = "Contango" if current["curve_slope_percent"] > 0 else "Backwardation"

    ytd = lambda rows: [row for row in rows if row["date"] >= display_start.isoformat()]
    comparison_start = dashboard_as_of - timedelta(days=730)
    comparison = lambda rows: [row for row in rows if row["date"] >= comparison_start.isoformat()]
    payload = {
        "schema_version": 2,
        "period": "YTD",
        "year": dashboard_as_of.year,
        "as_of": as_of,
        "generated_at": f"{as_of}T16:15:00-04:00",
        "history_start": HISTORY_START.isoformat(),
        "scorable_start": score_history[0]["date"],
        "comparison_start": comparison_start.isoformat(),
        "sources": {
            "indices": "Yahoo Finance daily closes (^VIX, ^VVIX, ^MOVE, ^SKEW, ^VIX9D, ^VIX3M, SPY)",
            "futures": "Cboe official VX monthly contract settlement files (detailed archive begins 2013)",
            "credit": "FRED BAMLH0A0HYM2 shifted to next completed session for T+1 availability",
        },
        "current": current,
        "score": score,
        "commentary": commentary(current, score),
        "series": {
            "vix": ytd(indices["vix"]),
            "vvix": ytd(indices["vvix"]),
            "move": ytd(indices["move"]),
            "skew": ytd(indices["skew"]),
            "curve_spread": ytd(futures),
            "hy_oas": ytd(credit_observations),
            "vix9d_vix": ytd(vix9d_ratio),
            "vix_vix3m": ytd(vix3m_ratio),
        },
        "history": {
            "score": score_history,
            "spy": comparison(indices["spy"]),
            "vix_spikes": contiguous_windows(indices["vix"], lambda value: value >= 25),
        },
        "conditional_frequencies": frequencies,
        "gate_policy": policy,
        "scanner_policy": {
            "schema_version": 1,
            "stage": "risk_v2_stage2",
            "as_of": as_of,
            "watchful_action": "annotate_half_size",
            "elevated_action": "gate" if policy["hard_gate_enabled"] else "shadow_log",
            "elevated_hard_gate_enabled": policy["hard_gate_enabled"],
            "stage1_bands_separate_from_unconditional_base_rate": policy["hard_gate_enabled"],
            "evidence": policy["evidence"],
        },
        "curve": curve,
        "windows": {
            "vix_spikes": contiguous_windows(ytd(indices["vix"]), lambda value: value >= 25),
            "vvix_high": contiguous_windows(ytd(indices["vvix"]), lambda value: value > 110),
        },
        "thresholds": {
            "display_only": True,
            "vix": [15, 20, 25],
            "vvix": [90, 110],
            "move": [80, 100],
            "skew": [130, 145],
        },
        "method": "The Conditions Score uses trailing three-year empirical percentiles, a constant-maturity 30-to-60-day VIX futures slope where a positive slope means contango, lagged credit, and zero weight for stale inputs. It is a falsifiable conditions heuristic, not a calibrated probability or trading signal.",
        "model_status": evaluation_status(as_of),
    }
    return payload


def serialize(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, separators=(",", ": ")) + "\n"


def update_asset_version(rendered: str) -> str:
    digest = hashlib.sha256(rendered.encode()).hexdigest()[:12]
    if not PAGE.exists() or 'id="risk-panel"' not in PAGE.read_text():
        return digest
    source = PAGE.read_text()
    js_digest = hashlib.sha256(RISK_JS.read_bytes()).hexdigest()[:12]
    css_digest = hashlib.sha256(RISK_CSS.read_bytes()).hexdigest()[:12]
    replacements = (
        (r"/trading/risk-ytd\.json\?v=[a-f0-9]+", f"/trading/risk-ytd.json?v={digest}", 2, "risk data"),
        (r"/js/trading-risk\.js\?v=[a-f0-9]+", f"/js/trading-risk.js?v={js_digest}", 1, "risk JS"),
        (r"/css/trading-risk\.css\?v=[a-f0-9]+", f"/css/trading-risk.css?v={css_digest}", 1, "risk CSS"),
    )
    updated = source
    for pattern, replacement, expected, label in replacements:
        updated, count = re.subn(pattern, replacement, updated)
        if count != expected:
            raise RuntimeError(f"expected {expected} {label} asset URLs, found {count}")
    if updated != source:
        temporary = PAGE.with_suffix(".html.tmp")
        temporary.write_text(updated)
        os.replace(temporary, PAGE)
    return digest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--end", type=date.fromisoformat, help="inclusive data cutoff (YYYY-MM-DD)")
    parser.add_argument("--check", action="store_true", help="fetch and validate without writing")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    payload = build(args.end)
    rendered = serialize(payload)
    digest = hashlib.sha256(rendered.encode()).hexdigest()[:12]
    current = args.output.read_text() if args.output.exists() else ""
    changed = rendered != current
    if not args.check:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=args.output.name + ".", dir=args.output.parent)
        try:
            with os.fdopen(descriptor, "w") as handle:
                handle.write(rendered)
            os.replace(temporary, args.output)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        if args.output.resolve() == OUTPUT.resolve():
            digest = update_asset_version(rendered)
    print(json.dumps({
        "as_of": payload["as_of"],
        "changed": changed,
        "score": payload["score"]["total"],
        "regime": payload["score"]["label"],
        "curve_slope_percent": payload["current"]["curve_slope_percent"],
        "scorable_start": payload["scorable_start"],
        "score_history_points": len(payload["history"]["score"]),
        "hard_gate_enabled": payload["gate_policy"]["hard_gate_enabled"],
        "digest": digest,
        "points": {name: len(rows) for name, rows in payload["series"].items()},
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
