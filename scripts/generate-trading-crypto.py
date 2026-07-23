#!/usr/bin/env python3
"""Generate Zonted's daily Hyperliquid crypto spread/VWAP artifact.

Uses completed UTC daily perp candles only. Emits
scans/crypto-spread-YYYY-MM-DD.json for scripts/update-trading-crypto.py.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import urllib.request

API = "https://api.hyperliquid.xyz/info"
OUT_DIR = os.path.expanduser("~/trading/scans")
COINS = {
    "ZEC": "Zcash",
    "ETH": "Ethereum",
    "SOL": "Solana",
    "HYPE": "Hyperliquid",
    "XRP": "XRP",
    "BNB": "BNB",
    "DOGE": "Dogecoin",
}
DAY_MS = 86_400_000


def post(body):
    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "zonted-crypto-spread/1.0"},
    )
    with urllib.request.urlopen(req, timeout=45) as response:
        if response.status != 200:
            raise RuntimeError(f"Hyperliquid returned HTTP {response.status}")
        return json.load(response)


def candles(symbol, start_ms, end_ms):
    rows = post({"type": "candleSnapshot", "req": {
        "coin": symbol, "interval": "1d", "startTime": start_ms, "endTime": end_ms,
    }})
    out = {}
    for row in rows:
        if int(row["T"]) > end_ms:
            continue
        date = dt.datetime.fromtimestamp(int(row["t"]) / 1000, dt.timezone.utc).date().isoformat()
        values = {key: float(row[key]) for key in ("o", "h", "l", "c", "v")}
        if not all(math.isfinite(value) for value in values.values()) or values["v"] < 0:
            raise RuntimeError(f"{symbol} has invalid candle on {date}")
        out[date] = values
    if len(out) < 60:
        raise RuntimeError(f"{symbol} returned only {len(out)} completed daily candles")
    return out


def ema(values, span):
    alpha = 2.0 / (span + 1.0)
    out, current = [], None
    for value in values:
        if value is None:
            out.append(current)
            continue
        current = value if current is None else alpha * value + (1 - alpha) * current
        out.append(current)
    return out


def z50(values):
    mean = ema(values, 50)
    variance = ema([(value - center) ** 2 for value, center in zip(values, mean)], 50)
    raw = [None if value <= 0 else (price - center) / math.sqrt(value)
           for price, center, value in zip(values, mean, variance)]
    return ema(raw, 3)


def streak(values, positive):
    count = 0
    for value in reversed(values):
        if (value >= 0) != positive:
            break
        count += 1
    return count


def anchored_vwap(rows, dates):
    numerator = denominator = 0.0
    out = []
    for date in dates:
        row = rows[date]
        typical = (row["h"] + row["l"] + row["c"]) / 3.0
        numerator += typical * row["v"]
        denominator += row["v"]
        if denominator <= 0:
            raise RuntimeError(f"non-positive cumulative volume through {date}")
        out.append(numerator / denominator)
    return out


def main():
    now = dt.datetime.now(dt.timezone.utc)
    last_complete = now.date() - dt.timedelta(days=1)
    start = dt.date(now.year, 1, 1)
    start_ms = int(dt.datetime.combine(start, dt.time.min, tzinfo=dt.timezone.utc).timestamp() * 1000)
    end_ms = int(dt.datetime.combine(last_complete, dt.time.max, tzinfo=dt.timezone.utc).timestamp() * 1000)

    bars = {symbol: candles(symbol, start_ms, end_ms) for symbol in ["BTC", *COINS]}
    common = sorted(set.intersection(*(set(rows) for rows in bars.values())))
    if not common or common[-1] != last_complete.isoformat():
        raise RuntimeError(f"completed-session mismatch: expected {last_complete}, got {common[-1] if common else 'none'}")

    btc_close = [bars["BTC"][date]["c"] for date in common]
    btc_z = z50(btc_close)
    if btc_z[-1] is None:
        raise RuntimeError("BTC Z score is unavailable")

    coins, vwaps = [], []
    for symbol, name in COINS.items():
        rows = bars[symbol]
        close = [rows[date]["c"] for date in common]
        coin_z = z50(close)
        spread = [None if a is None or b is None else a - b for a, b in zip(coin_z, btc_z)]
        finite_spread = [value for value in spread if value is not None]
        if len(finite_spread) < 20:
            raise RuntimeError(f"{symbol} spread history is too short")
        first = next(i for i, value in enumerate(spread) if value is not None)
        spread_dates = common[first:]
        spread_values = spread[first:]
        ratio_start = close[first] / btc_close[first]
        ratio_last = close[-1] / btc_close[-1]
        spread_last = spread_values[-1]
        coins.append({
            "sym": symbol,
            "name": name,
            "price": round(close[-1], 8),
            "z": round(coin_z[-1], 6),
            "spread": round(spread_last, 6),
            "days_side": streak(spread_values, spread_last >= 0),
            "ratio_ytd_chg": round((ratio_last / ratio_start - 1) * 100, 6),
            "series": {
                "dates": spread_dates,
                "spread": [round(value, 6) for value in spread_values],
            },
        })

        vwap = anchored_vwap(rows, common)
        diff = [price - basis for price, basis in zip(close, vwap)]
        side = diff[-1] >= 0
        vwaps.append({
            "sym": symbol,
            "name": name,
            "price": round(close[-1], 8),
            "vwap": round(vwap[-1], 8),
            "pct": round((close[-1] / vwap[-1] - 1) * 100, 6),
            "side": side,
            "held": streak(diff, side),
            "series": {
                "dates": common,
                "close": [round(value, 8) for value in close],
                "vwap": [round(value, 8) for value in vwap],
            },
        })

    payload = {
        "last_bar": common[-1],
        "btc": {"price": round(btc_close[-1], 8), "z": round(btc_z[-1], 6)},
        "coins": coins,
        "vwap_native": vwaps,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"crypto-spread-{common[-1]}.json")
    text = json.dumps(payload, separators=(",", ":"), allow_nan=False)
    with open(path, "w") as handle:
        handle.write(text)
    print(f"[done] {path}: {len(coins)} coins, {len(common)} sessions")


if __name__ == "__main__":
    main()
