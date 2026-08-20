#!/usr/bin/env python3
"""Score KXHIGHCHI 2026 YTD Buy-No ladder from fetched artifacts. Do not invent numbers."""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEVELS = [70, 75, 80, 85, 90, 95]
NYC = {"n": 281, "die_pct": 18.1, "ev_after_fee": 7.5}


def parse_float(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fee_cents(x: int) -> float:
    """Kalshi taker 0.07 * p * (1-p) in cents, p = No price = (100-X)/100."""
    p = (100 - x) / 100.0
    return 0.07 * p * (1.0 - p) * 100.0


def load_markets() -> list[dict]:
    payload = json.loads((ROOT / "markets_merged.json").read_text())
    return payload["markets"]


def load_jsonl(name: str) -> dict[str, dict]:
    path = ROOT / name
    out: dict[str, dict] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec.get("ticker"):
            out[rec["ticker"]] = rec
    return out


def load_max_yes() -> dict[str, dict]:
    """Prefer candle price.high; fall back to trade max_yes if a candle failed."""
    candles = load_jsonl("candles_summary.jsonl")
    trades = load_jsonl("trades_summary.jsonl")
    out: dict[str, dict] = {}
    tickers = set(candles) | set(trades)
    for t in tickers:
        c = candles.get(t) or {}
        tr = trades.get(t) or {}
        if c.get("ok") and c.get("max_yes") is not None:
            out[t] = {
                "ticker": t,
                "max_yes": c["max_yes"],
                "src": "candle_price_high",
                "yes_ask_high": c.get("yes_ask_high"),
                "result": c.get("result") or tr.get("result"),
            }
        elif tr.get("ok") and tr.get("max_yes") is not None:
            out[t] = {
                "ticker": t,
                "max_yes": tr["max_yes"],
                "src": "trade_max_yes",
                "result": tr.get("result"),
            }
    return out


def classify_rules(text: str) -> dict[str, bool]:
    t = (text or "").lower()
    midway = bool(
        re.search(r"midway|\bclimdw\b|\bkmdw\b|issuedby=mdw|chicago \(climdw\)", t)
    )
    # do not match bare "ord" — it hits "recorded"
    ohare = bool(
        re.search(r"o['’]hare|\bohare\b|\bkord\b|\bcliord\b|issuedby=ord", t)
    )
    return {"midway": midway, "ohare": ohare}


def printed_x(m: dict, rec: dict | None, x: int) -> tuple[bool, str]:
    """printed X if candle/trade max_yes >= X/100; else last_price only on YES>=0.96."""
    if rec and rec.get("max_yes") is not None:
        my = float(rec["max_yes"])
        src = rec.get("src") or "max_yes"
        return my + 1e-12 >= x / 100.0, src
    last = parse_float(m.get("last_price_dollars"))
    result = (m.get("result") or "").lower()
    if last is None:
        return False, "none"
    # last_price fallback: YES that finished >=0.96 (lives). Not used as a die source.
    if result == "yes" and last + 1e-12 >= 0.96:
        if x >= 90:
            return last + 1e-12 >= max(x / 100.0, 0.90), "last_yes96"
        return last + 1e-12 >= x / 100.0, "last_yes96"
    return False, "none"


def score() -> dict:
    markets = load_markets()
    mx = load_max_yes()
    events = sorted({m.get("event_ticker") for m in markets if m.get("event_ticker")})
    y2026 = [m for m in markets if (m.get("event_ticker") or "").startswith("KXHIGHCHI-26")]

    n_midway = n_ohare = n_rules = 0
    n_word_midway = n_climdw = n_nws = n_twc = 0
    for m in y2026:
        rules = m.get("rules_primary") or ""
        if rules:
            n_rules += 1
            flags = classify_rules(rules)
            if flags["midway"]:
                n_midway += 1
            if flags["ohare"]:
                n_ohare += 1
            if "Midway" in rules:
                n_word_midway += 1
            if "CLIMDW" in rules:
                n_climdw += 1
            if "National Weather Service" in rules:
                n_nws += 1
            if "Weather Company" in rules:
                n_twc += 1

    series = json.loads((ROOT / "series.json").read_text())
    highchi_src = (
        ((series.get("HIGHCHI") or {}).get("data") or {}).get("series") or {}
    ).get("settlement_sources")
    kx_src = (
        ((series.get("KXHIGHCHI") or {}).get("data") or {}).get("series") or {}
    ).get("settlement_sources")
    kx_info = (
        (((series.get("KXHIGHCHI") or {}).get("data") or {}).get("series") or {})
        .get("product_metadata")
        or {}
    ).get("important_info") or {}

    results = Counter((m.get("result") or "").lower() for m in y2026)
    n_yes = results.get("yes", 0)
    n_no = results.get("no", 0)

    candles_raw = load_jsonl("candles_summary.jsonl")
    trades_raw = load_jsonl("trades_summary.jsonl")
    n_agree = n_flips = n_false_ask = 0
    for m in y2026:
        tkr = m.get("ticker") or ""
        c = candles_raw.get(tkr) or {}
        tr = trades_raw.get(tkr) or {}
        cv = parse_float(c.get("max_yes"))
        tv = parse_float(tr.get("max_yes"))
        if cv is not None and tv is not None:
            if abs(cv - tv) < 1e-6:
                n_agree += 1
            if (cv + 1e-12 >= 0.90) != (tv + 1e-12 >= 0.90):
                n_flips += 1
        ah = parse_float(c.get("yes_ask_high"))
        if (
            cv is not None
            and ah is not None
            and ah + 1e-12 >= 0.90
            and cv + 1e-12 < 0.90
            and (m.get("result") or "").lower() == "no"
        ):
            n_false_ask += 1

    have_candle = [m for m in y2026 if (mx.get(m.get("ticker") or "") or {}).get("src") == "candle_price_high"]
    have_trade_fb = [m for m in y2026 if (mx.get(m.get("ticker") or "") or {}).get("src") == "trade_max_yes"]
    have_max = [m for m in y2026 if (mx.get(m.get("ticker") or "") or {}).get("max_yes") is not None]
    missing_no_vol = []
    for m in y2026:
        if (m.get("result") or "").lower() != "no":
            continue
        vol = parse_float(m.get("volume_fp")) or 0.0
        if vol <= 0:
            continue
        t = mx.get(m.get("ticker") or "")
        if not t or t.get("max_yes") is None:
            missing_no_vol.append(m.get("ticker"))

    yes_need = []
    for m in y2026:
        if (m.get("result") or "").lower() != "yes":
            continue
        t = mx.get(m.get("ticker") or "")
        last = parse_float(m.get("last_price_dollars")) or 0.0
        vol = parse_float(m.get("volume_fp")) or 0.0
        if not t or t.get("max_yes") is None:
            if last >= 0.85 or vol > 0:
                yes_need.append({"ticker": m.get("ticker"), "last": last, "volume_fp": m.get("volume_fp")})

    ladder = {}
    for x in LEVELS:
        prints = []
        sources = Counter()
        for m in y2026:
            hit, src = printed_x(m, mx.get(m.get("ticker") or ""), x)
            if not hit:
                continue
            die = (m.get("result") or "").lower() == "no"
            prints.append({"ticker": m.get("ticker"), "die": die, "src": src, "result": m.get("result")})
            sources[src] += 1
        n = len(prints)
        n_die = sum(1 for p in prints if p["die"])
        die_pct = (n_die / n * 100.0) if n else None
        ev = (die_pct - (100 - x)) if die_pct is not None else None
        fee = fee_cents(x)
        ev_af = (ev - fee) if ev is not None else None
        ladder[str(x)] = {
            "n": n,
            "n_die": n_die,
            "die_pct": round(die_pct, 4) if die_pct is not None else None,
            "ev_cents": round(ev, 4) if ev is not None else None,
            "fee_cents": round(fee, 4),
            "ev_after_fee_cents": round(ev_af, 4) if ev_af is not None else None,
            "sources": dict(sources),
            "n_max_yes": sources.get("candle_price_high", 0) + sources.get("trade_max_yes", 0) + sources.get("max_yes", 0),
            "n_candle": sources.get("candle_price_high", 0),
            "n_trade_fallback": sources.get("trade_max_yes", 0),
            "n_last_yes96": sources.get("last_yes96", 0),
        }

    line90 = ladder["90"]
    n90 = line90["n"]
    if n90 < 80:
        verdict = "n too small"
    elif line90["ev_after_fee_cents"] is None:
        verdict = "not enough n"
    elif line90["ev_after_fee_cents"] > 0:
        verdict = "+EV"
    else:
        verdict = "no edge"

    dates = []
    for et in events:
        m = re.match(r"KXHIGHCHI-26([A-Z]{3})(\d{2})$", et or "")
        if not m:
            continue
        mon = {
            "JAN": 1,
            "FEB": 2,
            "MAR": 3,
            "APR": 4,
            "MAY": 5,
            "JUN": 6,
            "JUL": 7,
            "AUG": 8,
            "SEP": 9,
            "OCT": 10,
            "NOV": 11,
            "DEC": 12,
        }[m.group(1)]
        dates.append(date(2026, mon, int(m.group(2))))

    out = {
        "asof": "2026-08-19",
        "series": "KXHIGHCHI",
        "judge": {
            "station": "KMDW Midway / CLIMDW",
            "confirmed": n_ohare == 0 and n_midway > 0,
            "n_rules": n_rules,
            "n_rules_midway_climdw": n_midway,
            "n_rules_word_midway": n_word_midway,
            "n_rules_climdw": n_climdw,
            "n_rules_nws": n_nws,
            "n_rules_twc": n_twc,
            "n_rules_ohare": n_ohare,
            "kxhighchi_settlement_sources": kx_src,
            "highchi_settlement_sources": highchi_src,
            "kxhighchi_important_info": kx_info.get("markdown"),
            "note": "HIGHCHI series source is NWS CLI issuedby=MDW. KXHIGHCHI event rules_primary name CLIMDW / Chicago Midway. NWS→TWC 2026-08-14 same station.",
        },
        "coverage": {
            "n_settled_markets": len(y2026),
            "n_2026_events": len(events),
            "date_start": min(dates).isoformat() if dates else None,
            "date_end": max(dates).isoformat() if dates else None,
            "n_yes": n_yes,
            "n_no": n_no,
            "n_with_max_yes": len(have_max),
            "n_with_candle_price_high": len(have_candle),
            "n_with_trade_fallback": len(have_trade_fb),
            "n_missing_no_volume_max_yes": len(missing_no_vol),
            "missing_no_volume_tickers": missing_no_vol,
            "n_yes_still_missing": len(yes_need),
            "yes_missing": yes_need,
            "max_yes_field": "candle price.high / price.high_dollars (trade high). Never yes_ask.high.",
            "n_candle_trade_agree": n_agree,
            "n_90_flips": n_flips,
            "n_false_ask_90": n_false_ask,
            "note": "Missing NO-with-volume max_yes bias die% DOWN (spike-then-fade 90s not seen). Last-price fallback is YES>=0.96 lives only. Do not score last-price-only 0% die as the strategy.",
        },
        "ladder": ladder,
        "nyc_2026_ytd_given": NYC,
        "vs_nyc_90": {
            "chi_n": line90["n"],
            "chi_die_pct": line90["die_pct"],
            "chi_ev_after_fee_cents": line90["ev_after_fee_cents"],
            "nyc_n": NYC["n"],
            "nyc_die_pct": NYC["die_pct"],
            "nyc_ev_after_fee_cents": NYC["ev_after_fee"],
        },
        "verdict": verdict,
        "pass_90no_plus_ev_after_fee": verdict == "+EV",
        "fee_note": "taker 0.07*p*(1-p); at 10c No fee=0.63c; breakeven die after fee=10.63%",
        "max_yes_source": "candle price.high (daily 1440); trade tape only if candle fails",
    }
    return out


def render_md(s: dict) -> str:
    j = s["judge"]
    c = s["coverage"]
    lines = [
        "# KXHIGHCHI 2026 YTD — Buy-No at first 90¢ Yes print",
        "",
        f"As-of **{s['asof']}**. Settled event-days `KXHIGHCHI-26JAN01` through `KXHIGHCHI-26AUG18`.",
        "",
        "## Judge / station",
        "",
        f"- Station: **{j['station']}** (not O'Hare).",
        f"- Confirmed from event `rules_primary`: {j['n_rules_midway_climdw']} / {j['n_rules']} mention Midway/CLIMDW ({j['n_rules_word_midway']} say Midway, {j['n_rules_climdw']} say CLIMDW); {j['n_rules_ohare']} mention O'Hare.",
        f"- Source agency in rules: NWS {j['n_rules_nws']}, TWC {j['n_rules_twc']} (TWC = Aug 14–18 after the 2026-08-14 switch).",
        f"- HIGHCHI series `settlement_sources`: NWS CLI `issuedby=MDW` (CLIMDW).",
        f"- KXHIGHCHI series settlement source is The Weather Company after **2026-08-14** (NWS→TWC, same station).",
        "",
        "## Universe",
        "",
        f"- Settled 2026 markets: **{c['n_settled_markets']}**",
        f"- 2026 events: **{c['n_2026_events']}** ({c['date_start']} .. {c['date_end']})",
        f"- Results: YES={c['n_yes']} NO={c['n_no']}",
        "",
        "## Coverage",
        "",
        f"- Tickers with `max_yes`: **{c['n_with_max_yes']}** / {c['n_settled_markets']} (candle `price.high` {c['n_with_candle_price_high']}; trade fallback {c['n_with_trade_fallback']})",
        f"- Missing NO-with-volume max_yes: **{c['n_missing_no_volume_max_yes']}** (these bias die% **down**)",
        f"- YES still missing (last≥0.85 or volume): **{c['n_yes_still_missing']}**",
        f"- `max_yes` is candle **price.high** (trade high), never yes_ask.high. Last-price fallback only for YES last≥0.96. Die% is **not** last-price-only.",
        f"- Candle `price.high` vs full trade tape: {c.get('n_candle_trade_agree', 'n/a')} tickers agree (90-print flips = {c.get('n_90_flips', 0)}). `yes_ask.high`≥0.90 with `price.high`<0.90 on {c.get('n_false_ask_90', 'n/a')} NOs — those are book, not trades.",
        "",
        "## 2026 YTD ladder (Buy No at 100−X¢ on first X Yes print)",
        "",
        "| X¢ Yes | n | die | die% | EV¢ | fee¢ | EV after fee¢ | candle n | trade-fb n | YES≥96 n |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for x in LEVELS:
        row = s["ladder"][str(x)]
        die_pct = "—" if row["die_pct"] is None else f"{row['die_pct']:.2f}"
        ev = "—" if row["ev_cents"] is None else f"{row['ev_cents']:+.2f}"
        evf = "—" if row["ev_after_fee_cents"] is None else f"{row['ev_after_fee_cents']:+.2f}"
        lines.append(
            f"| {x} | {row['n']} | {row['n_die']} | {die_pct} | {ev} | {row['fee_cents']:.2f} | {evf} | {row.get('n_candle', 0)} | {row.get('n_trade_fallback', 0)} | {row['n_last_yes96']} |"
        )
    nyc = s["vs_nyc_90"]
    r90 = s["ladder"]["90"]
    lines += [
        "",
        "## 90¢ line vs NYC",
        "",
        f"- CHI 2026 YTD: n={nyc['chi_n']}, die%={nyc['chi_die_pct']:.2f}, EV after fee={nyc['chi_ev_after_fee_cents']:+.2f}¢",
        f"- NYC 2026 YTD (given, not refetched): n={nyc['nyc_n']}, die%={nyc['nyc_die_pct']}, EV after fee={nyc['nyc_ev_after_fee_cents']:+.1f}¢",
        f"- Fee at 10¢ No = 0.63¢; breakeven die after fee = 10.63%. Observed 90-No die% = {r90['die_pct']:.2f}.",
        "",
        f"## Verdict: **{s['verdict']}**",
        "",
        "Pass only if 90-No is +EV after fee on 2026 YTD. Seasonal splits not claimed unless n per season ≥ ~80.",
        "",
        "## Caveats",
        "",
        "1. **Fill** — assumes a 10¢ No fill at the first 90¢ Yes print (candle `price.high` ≥ 0.90, or YES last≥0.96 fallback).",
        "2. **Judge** — Midway (KMDW / CLIMDW), not O'Hare. Source agency changed NWS→TWC on 2026-08-14; station unchanged.",
        "3. **Coverage** — `max_yes` from candle trade high (`price.high`), not `yes_ask.high` (book can sit at 0.99 with no trade). Last-price-only would miss spike-then-fade dies (Austin trap). Missing NO candles bias die% down.",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    s = score()
    (ROOT / "ytd_90no.json").write_text(json.dumps(s, indent=2) + "\n")
    (ROOT / "ytd_90no.md").write_text(render_md(s))
    print(json.dumps({k: s[k] for k in ("verdict", "vs_nyc_90", "coverage") if k in s}, indent=2))
    print("ladder90", s["ladder"]["90"])


if __name__ == "__main__":
    main()
