#!/usr/bin/env python3
"""Generate Zonted's YTD forward-market-risk dataset from public sources.

Sources:
- Yahoo Finance chart API: ^VIX, ^VVIX, ^MOVE, ^SKEW
- Cboe: official contract settlement files for the VIX futures curve
- FRED: ICE BofA US High Yield Index option-adjusted spread

The output is presentation-ready JSON; charts are rendered lazily in the browser.
"""
from __future__ import annotations

import argparse
import calendar
import csv
import hashlib
import io
import json
import math
import os
import re
import tempfile
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "trading" / "risk-ytd.json"
PAGE = ROOT / "trading" / "index.html"
ET = ZoneInfo("America/New_York")
USER_AGENT = "zonted-risk-dashboard/1.0 hello@veracityapi.com"
YAHOO_SYMBOLS = {"vix": "^VIX", "vvix": "^VVIX", "move": "^MOVE", "skew": "^SKEW"}


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
    return {
        observed_fixed(date(year, 1, 1)),
        nth_weekday(year, 1, calendar.MONDAY, 3),
        nth_weekday(year, 2, calendar.MONDAY, 3),
        easter_sunday(year) - timedelta(days=2),
        memorial,
        observed_fixed(date(year, 6, 19)),
        observed_fixed(date(year, 7, 4)),
        nth_weekday(year, 9, calendar.MONDAY, 1),
        thanksgiving,
        observed_fixed(date(year, 12, 25)),
    }


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


def request_bytes(url: str, *, timeout: int = 60) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json,text/csv,*/*"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


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


def cboe_contract(expiration: str, start: date, end: date) -> list[dict[str, Any]]:
    url = f"https://cdn.cboe.com/data/us/futures/market_statistics/historical_data/VX/VX_{expiration}.csv"
    text = request_bytes(url).decode("utf-8-sig")
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
        if math.isfinite(settle):
            rows.append({"date": day.isoformat(), "value": round(settle, 4)})
    return rows


def futures_history(start: date, end: date) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    by_expiration: dict[str, list[dict[str, Any]]] = {}
    for expiration in vx_expirations_for_window(start, end):
        expiry = date.fromisoformat(expiration)
        if expiry <= start or expiry > end + timedelta(days=240):
            continue
        by_expiration[expiration] = cboe_contract(expiration, start, end)

    observations: dict[str, list[tuple[date, float]]] = {}
    for expiration, rows in by_expiration.items():
        expiry = date.fromisoformat(expiration)
        for row in rows:
            observations.setdefault(row["date"], []).append((expiry, float(row["value"])))

    history: list[dict[str, Any]] = []
    for day_text in sorted(observations):
        day = date.fromisoformat(day_text)
        contracts = sorted((expiry, value) for expiry, value in observations[day_text] if expiry > day)
        if len(contracts) < 2:
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
        })
    if not history:
        raise RuntimeError("Cboe returned no usable M1/M2 history")
    return history, by_expiration


def latest_curve(
    as_of: date,
    vix: float,
    contracts: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
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
    if len(rows) < 3:
        raise RuntimeError("Cboe current curve has fewer than M1 and M2")
    return rows


def fred_series(series_id: str, start: date, api_key: str | None) -> list[dict[str, Any]]:
    if not api_key:
        return []
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
    return rows


def threshold_score(vvix: float, curve_spread: float, move: float, skew: float) -> dict[str, Any]:
    vvix_points = 0 if vvix < 90 else 20 if vvix <= 110 else 40
    curve_points = 0 if curve_spread > 0.5 else 15 if curve_spread >= 0 else 30
    move_points = 0 if move < 80 else 10 if move <= 100 else 20
    skew_points = 0 if skew < 130 else 5 if skew <= 145 else 10
    total = vvix_points + curve_points + move_points + skew_points
    label = "Contained" if total < 25 else "Watchful" if total < 50 else "Elevated"
    return {
        "total": total,
        "label": label,
        "components": {
            "vvix": {"points": vvix_points, "maximum": 40},
            "curve": {"points": curve_points, "maximum": 30},
            "move": {"points": move_points, "maximum": 20},
            "skew": {"points": skew_points, "maximum": 10},
        },
        "rules": [
            "VVIX: <90 = 0, 90–110 = 20, >110 = 40",
            "Curve (M2−M1): >0.50 = 0, 0–0.50 = 15, <0 = 30",
            "MOVE: <80 = 0, 80–100 = 10, >100 = 20",
            "SKEW: <130 = 0, 130–145 = 5, >145 = 10",
            "Regime: <25 Contained, 25–49 Watchful, 50+ Elevated",
        ],
    }


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


def commentary(current: dict[str, Any], score: dict[str, Any]) -> list[str]:
    curve = float(current["curve_spread"])
    curve_text = (
        "healthy contango" if curve > 0.5 else
        "a flattening but still positive curve" if curve >= 0 else
        "backwardation"
    )
    broad_confirmation = []
    if float(current["move"]) >= 80:
        broad_confirmation.append("bond volatility")
    if curve <= 0:
        broad_confirmation.append("the VIX curve")
    if current.get("hy_oas") is not None and float(current["hy_oas"]) >= 4:
        broad_confirmation.append("high-yield credit")
    confirmation_text = (
        f"Stress is also confirmed by {', '.join(broad_confirmation)}."
        if broad_confirmation else
        "The curve, bond volatility, and credit are not confirming broad stress."
    )
    return [
        f"Overall regime: {score['label']} ({score['total']}/100) for the next 1–2 months; this is a conditions score, not a forecast of a crash.",
        f"VIX is {current['vix']:.2f} ({current_band('vix', float(current['vix']))}); VVIX is {current['vvix']:.2f} ({current_band('vvix', float(current['vvix']))}), so options-of-options volatility deserves attention.",
        f"VIX futures show {curve_text}: M2−M1 is {curve:+.2f} points. Positive means contango; negative means backwardation.",
        f"MOVE is {current['move']:.2f} ({current_band('move', float(current['move']))}) and SKEW is {current['skew']:.2f} ({current_band('skew', float(current['skew']))}). {confirmation_text}",
    ]


def build(end: date | None = None) -> dict[str, Any]:
    today = datetime.now(ET).date()
    requested_end = min(end or today, today)
    start = date(requested_end.year, 1, 1)

    indices = {name: yahoo_series(symbol, start, requested_end) for name, symbol in YAHOO_SYMBOLS.items()}
    futures, contracts = futures_history(start, requested_end)
    latest_future = futures[-1]
    dashboard_as_of = max(
        date.fromisoformat(indices["vix"][-1]["date"]),
        date.fromisoformat(indices["vvix"][-1]["date"]),
        date.fromisoformat(indices["skew"][-1]["date"]),
        date.fromisoformat(latest_future["date"]),
    )
    curve = latest_curve(dashboard_as_of, float(indices["vix"][-1]["value"]), contracts)

    env = load_env(Path.home() / ".hermes" / ".env")
    hy_oas = fred_series("BAMLH0A0HYM2", start, env.get("FRED_API_KEY") or env.get("FRED_KEY"))
    current: dict[str, Any] = {name: float(rows[-1]["value"]) for name, rows in indices.items()}
    current.update({
        "dates": {name: rows[-1]["date"] for name, rows in indices.items()},
        "m1": float(latest_future["m1"]),
        "m2": float(latest_future["m2"]),
        "curve_spread": float(latest_future["spread"]),
        "curve_spread_percent": float(latest_future["spread_percent"]),
        "curve_as_of": latest_future["date"],
        "hy_oas": float(hy_oas[-1]["value"]) if hy_oas else None,
        "hy_oas_as_of": hy_oas[-1]["date"] if hy_oas else None,
    })
    score = threshold_score(current["vvix"], current["curve_spread"], current["move"], current["skew"])
    current["bands"] = {name: current_band(name, current[name]) for name in YAHOO_SYMBOLS}
    current["curve_band"] = "Contango" if current["curve_spread"] > 0.5 else "Flattening" if current["curve_spread"] >= 0 else "Backwardation"

    return {
        "schema_version": 1,
        "period": "YTD",
        "year": dashboard_as_of.year,
        "as_of": dashboard_as_of.isoformat(),
        "generated_at": f"{dashboard_as_of.isoformat()}T16:15:00-04:00",
        "sources": {
            "indices": "Yahoo Finance daily closes (^VIX, ^VVIX, ^MOVE, ^SKEW)",
            "futures": "Cboe official VX monthly contract settlement files",
            "credit": "FRED BAMLH0A0HYM2 (ICE BofA US High Yield Index OAS)",
        },
        "current": current,
        "score": score,
        "commentary": commentary(current, score),
        "series": {**indices, "curve_spread": futures, "hy_oas": hy_oas},
        "curve": curve,
        "windows": {
            "vix_spikes": contiguous_windows(indices["vix"], lambda value: value >= 25),
            "vvix_high": contiguous_windows(indices["vvix"], lambda value: value > 110),
        },
        "thresholds": {
            "vix": [15, 20, 25],
            "vvix": [90, 110],
            "move": [80, 100],
            "skew": [130, 145],
            "curve_spread": [0, 0.5],
        },
        "method": "M2−M1 is used so positive values correctly mean contango and negative values mean backwardation. The score is a transparent conditions heuristic, not a calibrated probability or trading signal.",
    }


def serialize(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, separators=(",", ": ")) + "\n"


def update_asset_version(rendered: str) -> str:
    digest = hashlib.sha256(rendered.encode()).hexdigest()[:12]
    if not PAGE.exists() or 'id="risk-panel"' not in PAGE.read_text():
        return digest
    source = PAGE.read_text()
    updated, count = re.subn(
        r"/trading/risk-ytd\.json\?v=[a-f0-9]+",
        f"/trading/risk-ytd.json?v={digest}",
        source,
    )
    if count != 2:
        raise RuntimeError(f"expected two risk data asset URLs, found {count}")
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
        "vix": payload["current"]["vix"],
        "vvix": payload["current"]["vvix"],
        "curve_spread": payload["current"]["curve_spread"],
        "digest": digest,
        "points": {name: len(rows) for name, rows in payload["series"].items()},
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
