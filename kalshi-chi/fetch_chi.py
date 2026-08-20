#!/usr/bin/env python3
"""Resume-safe Kalshi KXHIGHCHI public-API fetcher. Sleep >=2s; 429 backoff."""

from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE = "https://api.elections.kalshi.com/trade-api/v2"
UA = "research-backtest/1.0"
ROOT = Path(__file__).resolve().parent
EVENT_DIR = ROOT / "event_pages"
SLIM_KEYS = [
    "ticker",
    "event_ticker",
    "result",
    "volume_fp",
    "last_price_dollars",
    "close_time",
    "settlement_ts",
    "yes_sub_title",
    "expiration_value",
    "rules_primary",
    "status",
    "title",
]
MONTHS = {
    1: "JAN",
    2: "FEB",
    3: "MAR",
    4: "APR",
    5: "MAY",
    6: "JUN",
    7: "JUL",
    8: "AUG",
    9: "SEP",
    10: "OCT",
    11: "NOV",
    12: "DEC",
}
CUTOFF_HIST = date(2026, 6, 20)  # historical for date < this
CUTOFF_LIVE = date(2026, 6, 13)  # live for date >= this
TRADE_HIST_CUTOFF = datetime(2026, 6, 20, tzinfo=timezone.utc)
TRADE_BOTH_START = datetime(2026, 6, 13, tzinfo=timezone.utc)
TRADE_BOTH_END = datetime(2026, 6, 27, 23, 59, 59, tzinfo=timezone.utc)


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def get_json(path: str, params: dict | None = None) -> tuple[int, dict | None, str]:
    """GET JSON. Returns (http_status, data_or_none, error_text). Sleeps after every attempt."""
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    backoff = 30.0
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                raw = resp.read().decode()
                time.sleep(2.05)
                return resp.status, json.loads(raw), ""
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            if e.code == 429:
                wait = min(90.0, backoff) + random.uniform(0, 5)
                log(f"429 {path} sleep {wait:.0f}s (attempt {attempt+1})")
                time.sleep(wait)
                backoff *= 2
                continue
            time.sleep(2.05)
            return e.code, None, body[:800]
        except Exception as e:
            wait = min(90.0, backoff)
            log(f"ERR {path} {e!r} sleep {wait:.0f}s")
            time.sleep(wait)
            backoff *= 1.5
    time.sleep(2.05)
    return 0, None, "exhausted retries"


def slim_market(m: dict) -> dict:
    return {k: m.get(k) for k in SLIM_KEYS}


def event_ticker_for(d: date) -> str:
    return f"KXHIGHCHI-26{MONTHS[d.month]}{d.day:02d}"


def settled_days() -> list[date]:
    out = []
    d = date(2026, 1, 1)
    end = date(2026, 8, 18)
    while d <= end:
        out.append(d)
        d += timedelta(days=1)
    return out


def parse_float(v) -> float | None:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_yes_price(trade: dict) -> float | None:
    v = trade.get("yes_price_dollars")
    if v is None:
        v = trade.get("yes_price")
    p = parse_float(v)
    if p is None:
        return None
    if p > 1.5:
        p = p / 100.0
    return p


def parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    s = s.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except ValueError:
        return None


def volume_of(m: dict) -> float:
    v = parse_float(m.get("volume_fp"))
    if v is None:
        v = parse_float(m.get("volume"))
    return v or 0.0


def fetch_series() -> dict:
    out = {}
    for ticker in ("KXHIGHCHI", "HIGHCHI"):
        status, data, err = get_json(f"/series/{ticker}")
        out[ticker] = {"http_status": status, "error": err, "data": data}
        log(f"series {ticker} status={status}")
    (ROOT / "series.json").write_text(json.dumps(out, indent=2) + "\n")
    return out


def fetch_markets_for_event(et: str, d: date) -> dict:
    pages = []
    endpoints = []
    if d < CUTOFF_HIST:
        endpoints.append("/historical/markets")
    if d >= CUTOFF_LIVE:
        endpoints.append("/markets")
    # always try historical if nothing else
    if not endpoints:
        endpoints.append("/historical/markets")

    seen = set()
    markets = []
    errors = []
    for ep in endpoints:
        cursor = None
        while True:
            params = {"event_ticker": et, "limit": 32}
            if cursor:
                params["cursor"] = cursor
            status, data, err = get_json(ep, params)
            pages.append({"endpoint": ep, "http_status": status, "error": err, "cursor_in": cursor})
            if not data:
                errors.append({"endpoint": ep, "http_status": status, "error": err})
                break
            for m in data.get("markets") or []:
                t = m.get("ticker")
                if t and t not in seen:
                    seen.add(t)
                    markets.append(slim_market(m))
            cursor = data.get("cursor") or None
            if not cursor:
                break
    return {
        "event_ticker": et,
        "date": d.isoformat(),
        "n_markets": len(markets),
        "markets": markets,
        "errors": errors,
        "endpoints": [p["endpoint"] for p in pages],
    }


def fetch_all_event_pages() -> list[dict]:
    EVENT_DIR.mkdir(parents=True, exist_ok=True)
    days = settled_days()
    merged = []
    for i, d in enumerate(days, 1):
        et = event_ticker_for(d)
        dest = EVENT_DIR / f"{et}.json"
        if dest.exists():
            page = json.loads(dest.read_text())
            if page.get("n_markets", 0) > 0:
                log(f"skip event {i}/{len(days)} {et} n={page['n_markets']}")
                merged.extend(page["markets"])
                continue
        log(f"fetch event {i}/{len(days)} {et}")
        page = fetch_markets_for_event(et, d)
        dest.write_text(json.dumps(page, indent=2) + "\n")
        merged.extend(page["markets"])
    (ROOT / "markets_merged.json").write_text(
        json.dumps(
            {
                "n_markets": len(merged),
                "n_events": len(days),
                "date_start": "2026-01-01",
                "date_end": "2026-08-18",
                "markets": merged,
            },
            indent=2,
        )
        + "\n"
    )
    log(f"merged {len(merged)} markets")
    return merged


def fetch_events_list() -> dict:
    """Paginate settled events as a coverage cross-check."""
    dest = ROOT / "events_list.json"
    events = []
    cursor = None
    page_n = 0
    while True:
        page_n += 1
        params = {
            "series_ticker": "KXHIGHCHI",
            "status": "settled",
            "limit": 200,
            "with_nested_markets": "true",
        }
        if cursor:
            params["cursor"] = cursor
        log(f"events list page {page_n} cursor={cursor}")
        status, data, err = get_json("/events", params)
        if not data:
            log(f"events list failed {status} {err}")
            break
        batch = data.get("events") or []
        for e in batch:
            slim_e = {
                "event_ticker": e.get("event_ticker"),
                "series_ticker": e.get("series_ticker"),
                "title": e.get("title"),
                "sub_title": e.get("sub_title"),
                "strike_date": e.get("strike_date"),
                "settlement_sources": e.get("settlement_sources"),
                "n_markets": len(e.get("markets") or []),
                "market_tickers": [m.get("ticker") for m in (e.get("markets") or [])],
            }
            events.append(slim_e)
        cursor = data.get("cursor") or None
        if not cursor or not batch:
            break
        # safety: stop if we go past 2025
        if all((e.get("event_ticker") or "").find("25") == 2 or "25" in (e.get("event_ticker") or "") for e in batch):
            # don't stop on this heuristic alone
            pass
        if page_n > 20:
            break
    payload = {"n_events": len(events), "events": events}
    dest.write_text(json.dumps(payload, indent=2) + "\n")
    log(f"events list n={len(events)}")
    return payload


def load_done_tickers() -> set[str]:
    path = ROOT / "trades_summary.jsonl"
    done = set()
    if not path.exists():
        return done
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if rec.get("ok") and rec.get("ticker"):
            done.add(rec["ticker"])
    return done


def append_trade_summary(rec: dict) -> None:
    path = ROOT / "trades_summary.jsonl"
    with path.open("a") as f:
        f.write(json.dumps(rec, separators=(",", ":")) + "\n")


def fetch_trade_pages(ticker: str, close_time: datetime | None) -> tuple[list[dict], list[str]]:
    endpoints = []
    if close_time is None:
        endpoints = ["/historical/trades", "/markets/trades"]
    elif close_time < TRADE_HIST_CUTOFF:
        endpoints = ["/historical/trades"]
        if TRADE_BOTH_START <= close_time <= TRADE_BOTH_END:
            endpoints.append("/markets/trades")
    else:
        endpoints = ["/markets/trades"]
        if TRADE_BOTH_START <= close_time <= TRADE_BOTH_END:
            endpoints.insert(0, "/historical/trades")

    seen_ids = set()
    trades = []
    used = []
    for ep in endpoints:
        cursor = None
        got_any = False
        while True:
            params = {"ticker": ticker, "limit": 1000}
            if cursor:
                params["cursor"] = cursor
            status, data, err = get_json(ep, params)
            if not data:
                if status and status != 200:
                    log(f"trades {ticker} {ep} status={status}")
                break
            batch = data.get("trades") or []
            if batch:
                got_any = True
            for t in batch:
                tid = t.get("trade_id") or f"{t.get('created_time')}|{t.get('yes_price_dollars')}|{t.get('count_fp')}"
                if tid in seen_ids:
                    continue
                seen_ids.add(tid)
                trades.append(t)
            cursor = data.get("cursor") or None
            if not cursor or not batch:
                break
        if got_any:
            used.append(ep)
    return trades, used


def summarize(trades: list[dict]) -> dict:
    max_yes = None
    first_hit: dict[str, str] = {}
    levels = [70, 75, 80, 85, 90, 95]
    for t in trades:
        yp = parse_yes_price(t)
        ts = t.get("created_time")
        if yp is None:
            continue
        if max_yes is None or yp > max_yes:
            max_yes = yp
        for lvl in levels:
            key = str(lvl)
            if yp + 1e-12 >= lvl / 100.0:
                if key not in first_hit or (ts and ts < first_hit[key]):
                    if ts:
                        first_hit[key] = ts
    return {"n_trades": len(trades), "max_yes": max_yes, "first_hit": first_hit}


def trade_priority(markets: list[dict]) -> list[dict]:
    """a) 2026 settled NO volume>0 first; b) settled YES or last>=0.70 volume>0."""
    nos = []
    yesses = []
    rest = []
    for m in markets:
        et = m.get("event_ticker") or ""
        if not et.startswith("KXHIGHCHI-26"):
            continue
        result = (m.get("result") or "").lower()
        vol = volume_of(m)
        last = parse_float(m.get("last_price_dollars")) or 0.0
        if result == "no" and vol > 0:
            nos.append(m)
        elif result == "yes" or (last >= 0.70 and vol > 0):
            yesses.append(m)
        else:
            rest.append(m)

    def last_key(m):
        return parse_float(m.get("last_price_dollars")) or 0.0

    # YES: prefer last>=0.85 first so we can stop later if needed
    yesses.sort(key=last_key, reverse=True)
    return nos + yesses


def fetch_trades(markets: list[dict], yes_min_last: float | None = None) -> None:
    done = load_done_tickers()
    queue = trade_priority(markets)
    if yes_min_last is not None:
        filtered = []
        for m in queue:
            result = (m.get("result") or "").lower()
            last = parse_float(m.get("last_price_dollars")) or 0.0
            if result == "no":
                filtered.append(m)
            elif last >= yes_min_last or volume_of(m) > 0:
                filtered.append(m)
        queue = filtered
    todo = [m for m in queue if m.get("ticker") not in done]
    log(f"trades queue {len(todo)} remaining / {len(queue)} priority / {len(done)} done")
    for i, m in enumerate(todo, 1):
        ticker = m["ticker"]
        close = parse_dt(m.get("close_time"))
        log(f"trades {i}/{len(todo)} {ticker} result={m.get('result')} vol={volume_of(m)} last={m.get('last_price_dollars')}")
        trades, used = fetch_trade_pages(ticker, close)
        summ = summarize(trades)
        rec = {
            "ok": True,
            "ticker": ticker,
            "event_ticker": m.get("event_ticker"),
            "result": m.get("result"),
            "n_trades": summ["n_trades"],
            "max_yes": summ["max_yes"],
            "first_hit": summ["first_hit"],
            "endpoints": used,
            "close_time": m.get("close_time"),
            "last_price_dollars": m.get("last_price_dollars"),
            "volume_fp": m.get("volume_fp"),
        }
        append_trade_summary(rec)
        if i % 25 == 0:
            log(f"progress trades {i}/{len(todo)}")


def main() -> None:
    EVENT_DIR.mkdir(parents=True, exist_ok=True)
    series_path = ROOT / "series.json"
    if not series_path.exists():
        fetch_series()
    else:
        log("series.json exists")
    events_path = ROOT / "events_list.json"
    if not events_path.exists():
        fetch_events_list()
    else:
        log("events_list.json exists")
    merged_path = ROOT / "markets_merged.json"
    if merged_path.exists() and all((EVENT_DIR / f"{event_ticker_for(d)}.json").exists() for d in settled_days()):
        markets = json.loads(merged_path.read_text())["markets"]
        log(f"markets_merged exists n={len(markets)}")
    else:
        markets = fetch_all_event_pages()
    fetch_trades(markets)


if __name__ == "__main__":
    main()
