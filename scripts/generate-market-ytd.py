#!/usr/bin/env python3
"""Generate the compact SPY + VIX YTD feed used by the Trading desk rail."""
from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
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
DEFAULT_VWAP = ROOT / "trading" / "vwap-charts.json"
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


def load_spy_series(path: Path) -> dict[str, float]:
    payload = json.loads(path.read_text())
    markup = payload.get("charts", {}).get("SPY", "")
    match = re.search(r"data-d='([^']+)'", markup)
    if not match:
        raise RuntimeError("VWAP chart payload is missing SPY data")
    chart = json.loads(html.unescape(match.group(1)))
    dates, closes = chart.get("dates") or [], chart.get("close") or []
    series = {
        str(day): float(close)
        for day, close in zip(dates, closes)
        if close is not None and math.isfinite(float(close))
    }
    if len(series) < 50:
        raise RuntimeError("VWAP chart payload has too little SPY history")
    return series


def build_payload(as_of: date, vwap_path: Path = DEFAULT_VWAP) -> dict[str, Any]:
    start = date(as_of.year, 1, 1)
    spy = load_spy_series(vwap_path)
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
            "spy_ytd_percent": round((spy[day] / first_spy - 1) * 100, 2),
            "vix": round(vix[day], 2),
        }
        for day in common
    ]
    payload = {
        "schema_version": 1,
        "period": "YTD",
        "as_of": as_of.isoformat(),
        "source": "Zonted after-close VWAP feed for SPY; Yahoo Finance daily closes for Cboe Volatility Index (^VIX)",
        "points": points,
    }
    validate_payload(payload)
    return payload


def validate_payload(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != 1 or payload.get("period") != "YTD":
        raise RuntimeError("market YTD payload has an unsupported schema")
    points = payload.get("points")
    if not isinstance(points, list) or len(points) < 50:
        raise RuntimeError("market YTD payload needs at least 50 aligned sessions")
    dates = [str(row.get("date")) for row in points]
    if dates != sorted(set(dates)):
        raise RuntimeError("market YTD dates must be unique and ascending")
    if dates[-1] != payload.get("as_of"):
        raise RuntimeError("market YTD as_of must match its final point")
    for row in points:
        for key in ("spy", "spy_ytd_percent", "vix"):
            value = row.get(key)
            if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise RuntimeError(f"market YTD point has invalid {key}")
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
    parser.add_argument("--vwap", type=Path, default=DEFAULT_VWAP)
    parser.add_argument("--check", action="store_true", help="validate the existing output without fetching")
    args = parser.parse_args()
    if args.check:
        validate_payload(json.loads(args.output.read_text()))
        print(f"market YTD feed valid: {args.output}")
        return 0
    as_of = date.fromisoformat(args.as_of) if args.as_of else datetime.now(ET).date()
    payload = build_payload(as_of, args.vwap)
    atomic_write(args.output, json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(f"market YTD feed: {len(payload['points'])} sessions through {payload['as_of']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
