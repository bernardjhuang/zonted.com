#!/usr/bin/env python3
"""Candle max_yes for KXHIGHCHI. Uses price.high / price.high_dollars, never yes_ask."""

from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = "research-backtest/1.0"
ROOT = Path(__file__).resolve().parent
SLEEP = 0.35
CUTOFF = datetime(2026, 6, 20, tzinfo=timezone.utc)
BOTH_START = datetime(2026, 6, 13, tzinfo=timezone.utc)


def log(msg: str) -> None:
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)


def get_json(path: str) -> tuple[int, dict | None, str]:
    url = BASE + path
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    backoff = 30.0
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode()
                time.sleep(SLEEP)
                return resp.status, json.loads(raw), ""
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            if e.code == 429:
                wait = min(90.0, backoff) + random.uniform(0, 3)
                log(f"429 {path[:80]} sleep {wait:.0f}s")
                time.sleep(wait)
                backoff *= 1.5
                continue
            time.sleep(SLEEP)
            return e.code, None, body[:400]
        except Exception as e:
            log(f"ERR {e!r} sleep {backoff:.0f}s")
            time.sleep(backoff)
            backoff *= 1.5
    time.sleep(SLEEP)
    return 0, None, "exhausted"


def parse_float(v):
    if v is None or v == "":
        return None
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if x > 1.5:
        x = x / 100.0
    return x


def parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


def candle_extrema(data: dict) -> tuple[float | None, float | None, int]:
    price_highs = []
    ask_highs = []
    cs = data.get("candlesticks") or []
    for c in cs:
        p = c.get("price") or {}
        a = c.get("yes_ask") or {}
        ph = parse_float(p.get("high") if p.get("high") is not None else p.get("high_dollars"))
        ah = parse_float(a.get("high") if a.get("high") is not None else a.get("high_dollars"))
        if ph is not None:
            price_highs.append(ph)
        if ah is not None:
            ask_highs.append(ah)
    return (
        max(price_highs) if price_highs else None,
        max(ask_highs) if ask_highs else None,
        len(cs),
    )


def endpoints_for(close: datetime | None) -> list[str]:
    if close is None:
        return ["historical", "series"]
    if close < BOTH_START:
        return ["historical"]
    if close >= CUTOFF:
        return ["series"]
    return ["historical", "series"]


def candle_path(kind: str, ticker: str, start: int, end: int) -> str:
    q = f"start_ts={start}&end_ts={end}&period_interval=1440"
    if kind == "historical":
        return f"/historical/markets/{ticker}/candlesticks?{q}"
    return f"/series/KXHIGHCHI/markets/{ticker}/candlesticks?{q}"


def fetch_one(ticker: str, close: datetime | None) -> dict:
    if close is None:
        close = datetime(2026, 6, 1, tzinfo=timezone.utc)
    start = int((close - timedelta(days=4)).timestamp())
    end = int((close + timedelta(days=1)).timestamp())
    best_px = None
    best_ask = None
    n_candles = 0
    used = []
    errors = []
    for kind in endpoints_for(close):
        status, data, err = get_json(candle_path(kind, ticker, start, end))
        if not data:
            errors.append({"kind": kind, "http_status": status, "error": err})
            continue
        px, ask, n = candle_extrema(data)
        n_candles += n
        used.append(kind)
        if px is not None and (best_px is None or px > best_px):
            best_px = px
        if ask is not None and (best_ask is None or ask > best_ask):
            best_ask = ask
    return {
        "ok": best_px is not None,
        "max_yes": best_px,
        "yes_ask_high": best_ask,
        "n_candles": n_candles,
        "endpoints": used,
        "errors": errors,
    }


def load_done() -> set[str]:
    path = ROOT / "candles_summary.jsonl"
    done = set()
    if not path.exists():
        return done
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("ok") and rec.get("ticker") and rec.get("max_yes") is not None:
            done.add(rec["ticker"])
    return done


def append(rec: dict) -> None:
    with (ROOT / "candles_summary.jsonl").open("a") as f:
        f.write(json.dumps(rec, separators=(",", ":")) + "\n")


def volume_of(m: dict) -> float:
    try:
        return float(m.get("volume_fp") or 0)
    except (TypeError, ValueError):
        return 0.0


def queue(markets: list[dict]) -> list[dict]:
    nos, yesses = [], []
    for m in markets:
        if not (m.get("event_ticker") or "").startswith("KXHIGHCHI-26"):
            continue
        result = (m.get("result") or "").lower()
        last = float(m.get("last_price_dollars") or 0)
        vol = volume_of(m)
        if result == "no" and vol > 0:
            nos.append(m)
        elif result == "yes" or (last >= 0.85 and vol > 0):
            yesses.append(m)
    yesses.sort(key=lambda m: float(m.get("last_price_dollars") or 0), reverse=True)
    return nos + yesses


def main() -> None:
    markets = json.loads((ROOT / "markets_merged.json").read_text())["markets"]
    done = load_done()
    todo = [m for m in queue(markets) if m.get("ticker") not in done]
    log(f"candles queue {len(todo)} remaining / {len(done)} done")
    for i, m in enumerate(todo, 1):
        ticker = m["ticker"]
        close = parse_dt(m.get("close_time"))
        out = fetch_one(ticker, close)
        rec = {
            "ok": out["ok"],
            "ticker": ticker,
            "event_ticker": m.get("event_ticker"),
            "result": m.get("result"),
            "max_yes": out["max_yes"],
            "yes_ask_high": out["yes_ask_high"],
            "n_candles": out["n_candles"],
            "source": "candle_price_high",
            "endpoints": out["endpoints"],
            "close_time": m.get("close_time"),
            "last_price_dollars": m.get("last_price_dollars"),
            "volume_fp": m.get("volume_fp"),
        }
        if out["errors"] and not out["ok"]:
            rec["errors"] = out["errors"]
        append(rec)
        if i == 1 or i % 50 == 0 or not out["ok"]:
            log(f"{i}/{len(todo)} {ticker} max_yes={out['max_yes']} ask={out['yes_ask_high']} ok={out['ok']}")
    log("candles done")


if __name__ == "__main__":
    main()
