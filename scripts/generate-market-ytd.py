#!/usr/bin/env python3
"""Generate the compact trailing-one-year SPY + VIX feed used by the Trading desk rail."""
from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, time as dt_time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "trading" / "market-ytd.json"
ET = ZoneInfo("America/New_York")


def fetch_series(symbol: str, start: date, end: date, attempts: int = 3) -> list[dict[str, Any]]:
    start_epoch = int(datetime.combine(start, dt_time.min, timezone.utc).timestamp())
    end_epoch = int(datetime.combine(end + timedelta(days=1), dt_time.min, timezone.utc).timestamp())
    query = urllib.parse.urlencode({
        "period1": start_epoch,
        "period2": end_epoch,
        "interval": "1d",
        "events": "history",
    })
    encoded = urllib.parse.quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?{query}"
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "zonted-market-ytd/1.0"})
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = json.load(response)
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
            if not rows:
                raise RuntimeError(f"Yahoo returned no usable history for {symbol}")
            return rows
        except Exception as exc:  # Yahoo occasionally rate-limits a single request.
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Could not fetch {symbol}: {last_error}")


def build_payload(as_of: date) -> dict[str, Any]:
    start = as_of - timedelta(days=365)
    spy = {row["date"]: float(row["value"]) for row in fetch_series("SPY", start, as_of)}
    vix = {row["date"]: float(row["value"]) for row in fetch_series("^VIX", start, as_of)}
    common = sorted(set(spy) & set(vix))
    if len(common) < 50:
        raise RuntimeError(f"SPY/VIX overlap is too short: {len(common)} sessions")
    if common[-1] != as_of.isoformat():
        raise RuntimeError(f"Latest common SPY/VIX session is {common[-1]}, expected {as_of}")
    first_spy = spy[common[0]]
    points = [
        {
            "date": day,
            "spy": round(spy[day], 2),
            "spy_1y_percent": round((spy[day] / first_spy - 1) * 100, 2),
            "vix": round(vix[day], 2),
        }
        for day in common
    ]
    payload = {
        "schema_version": 2,
        "period": "1Y",
        "as_of": as_of.isoformat(),
        "source": "Yahoo Finance daily closes for SPY and Cboe Volatility Index (^VIX)",
        "points": points,
    }
    validate_payload(payload)
    return payload


def validate_payload(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != 2 or payload.get("period") != "1Y":
        raise RuntimeError("market one-year payload has an unsupported schema")
    points = payload.get("points")
    if not isinstance(points, list) or len(points) < 50:
        raise RuntimeError("market one-year payload needs at least 50 aligned sessions")
    dates = [str(row.get("date")) for row in points]
    if dates != sorted(set(dates)):
        raise RuntimeError("market one-year dates must be unique and ascending")
    if dates[-1] != payload.get("as_of"):
        raise RuntimeError("market one-year as_of must match its final point")
    for row in points:
        for key in ("spy", "spy_1y_percent", "vix"):
            value = row.get(key)
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise RuntimeError(f"market one-year point has invalid {key}")
        if row["spy"] <= 0 or row["vix"] <= 0:
            raise RuntimeError("SPY and VIX values must be positive")


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--as-of", help="latest completed trading session (YYYY-MM-DD)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)

    parser.add_argument("--check", action="store_true", help="validate the existing output without fetching")
    args = parser.parse_args()
    if args.check:
        validate_payload(json.loads(args.output.read_text()))
        print(f"market one-year feed valid: {args.output}")
        return 0
    as_of = date.fromisoformat(args.as_of) if args.as_of else datetime.now(ET).date()
    payload = build_payload(as_of)
    atomic_write(args.output, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"market one-year feed: {len(payload['points'])} sessions through {payload['as_of']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
