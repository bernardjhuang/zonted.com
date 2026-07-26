#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pandas>=2.0", "requests", "yfinance>=0.2.50", "pyarrow"]
# ///
"""Build lazy YTD stock + sector chart data for the GPT catalyst brief.

Uses the existing local Alpaca/Yahoo trading data layer so the public site only
ships a compact, credential-free JSON artifact.
"""
from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_BRIEF = ROOT / "trading" / "gpt-brief.json"
DEFAULT_OUTPUT = ROOT / "trading" / "gpt-brief-charts.json"
TRADING_SRC = pathlib.Path.home() / "trading" / "src"
SECTOR_NAMES = {
    "XLK": "Technology",
    "XLY": "Consumer discretionary",
    "XLV": "Health care",
    "XLF": "Financials",
    "XLI": "Industrials",
    "XLE": "Energy",
    "XLP": "Consumer staples",
    "XLC": "Communication services",
    "XLU": "Utilities",
    "XLRE": "Real estate",
    "XLB": "Materials",
}


def finite_or_none(value: object, digits: int = 6) -> float | None:
    if value is None or pd.isna(value) or not math.isfinite(float(value)):
        return None
    return round(float(value), digits)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--brief", type=pathlib.Path, default=DEFAULT_BRIEF)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not TRADING_SRC.exists():
        raise SystemExit(f"Missing local trading data layer: {TRADING_SRC}")
    sys.path.insert(0, str(TRADING_SRC))
    from alpaca_data import data_end, load_keys, probe_feed  # noqa: PLC0415
    from vwap_scan import anchored_vwap, fetch_ohlcv, z50  # noqa: PLC0415

    brief = json.loads(args.brief.read_text())
    events = brief.get("events") or []
    if not events:
        raise SystemExit("GPT brief has no events")

    event_map: dict[str, dict[str, str]] = {}
    stock_symbols: list[str] = []
    sector_symbols: list[str] = []
    for event in events:
        event_id = str(event.get("id") or "").strip()
        stock = str(event.get("primary_ticker") or "").strip().upper()
        sector = str(event.get("sector_etf") or "").strip().upper()
        if not event_id or not stock or sector not in SECTOR_NAMES:
            raise SystemExit(f"Invalid event chart mapping: {event_id or stock or '<unknown>'}")
        event_map[event_id] = {"stock": stock, "sector": sector, "sector_name": SECTOR_NAMES[sector]}
        stock_symbols.append(stock)
        sector_symbols.append(sector)

    symbols = list(dict.fromkeys([*stock_symbols, *sector_symbols]))
    year = int(str(brief["window_start"])[:4])
    anchor = f"{year}-01-01"
    start = f"{year - 1}-05-01"
    headers = load_keys()
    feed = probe_feed(headers)
    end = data_end()
    print(f"[gpt-brief-charts] fetching {len(symbols)} symbols {start} -> {end} (feed={feed})")
    bars = fetch_ohlcv(headers, symbols, start, end, feed)
    got = set(bars["symbol"].unique())
    missing = [symbol for symbol in symbols if symbol not in got]
    if missing:
        raise SystemExit(f"No market data for: {' '.join(missing)}")

    pivots = {
        field: bars.pivot_table(index="date", columns="symbol", values=field).sort_index()
        for field in ("high", "low", "close", "volume")
    }
    series: dict[str, dict[str, object]] = {}
    for symbol in symbols:
        close = pivots["close"][symbol].dropna()
        high = pivots["high"][symbol].reindex(close.index)
        low = pivots["low"][symbol].reindex(close.index)
        volume = pivots["volume"][symbol].reindex(close.index)
        ytd_vwap = anchored_vwap(high, low, close, volume, anchor)
        if ytd_vwap is None:
            raise SystemExit(f"Unable to calculate YTD VWAP for {symbol}")
        ytd_close = close.reindex(ytd_vwap.index).dropna()
        ytd_vwap = ytd_vwap.reindex(ytd_close.index)
        trend_z = z50(close).reindex(ytd_close.index)
        if len(ytd_close) < 20:
            raise SystemExit(f"Insufficient YTD history for {symbol}: {len(ytd_close)} sessions")
        latest_z = next((finite_or_none(value, 2) for value in reversed(trend_z.tolist()) if finite_or_none(value, 2) is not None), None)
        latest_close = float(ytd_close.iloc[-1])
        latest_vwap = float(ytd_vwap.iloc[-1])
        first_close = float(ytd_close.iloc[0])
        series[symbol] = {
            "name": SECTOR_NAMES.get(symbol, symbol),
            "dates": [stamp.date().isoformat() for stamp in ytd_close.index],
            "close": [finite_or_none(value, 2) for value in ytd_close],
            "vwap": [finite_or_none(value, 2) for value in ytd_vwap],
            "z50": [finite_or_none(value) for value in trend_z],
            "latest": {
                "date": ytd_close.index[-1].date().isoformat(),
                "price": round(latest_close, 2),
                "ytd_return_pct": round((latest_close / first_close - 1) * 100, 1),
                "vs_vwap_pct": round((latest_close / latest_vwap - 1) * 100, 1),
                "z50": latest_z,
            },
        }

    payload = {
        "as_of": brief["as_of"],
        "last_bar": max(record["latest"]["date"] for record in series.values()),
        "anchor": anchor,
        "zscore": "50-session EMA mean/RMS, smoothed over 3 sessions",
        "source": f"{feed.upper()} adjusted daily bars via Alpaca; Yahoo fallback for unavailable symbols",
        "events": event_map,
        "series": series,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, separators=(",", ":"), sort_keys=True, allow_nan=False) + "\n")
    print(f"[gpt-brief-charts] wrote {args.output}: {len(event_map)} events, {len(series)} series, last bar {payload['last_bar']}")


if __name__ == "__main__":
    main()
