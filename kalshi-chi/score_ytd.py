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


def load_trades() -> dict[str, dict]:
    path = ROOT / "trades_summary.jsonl"
    out: dict[str, dict] = {}
    if not path.exists():
        return out
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        if rec.get("ok") and rec.get("ticker"):
            out[rec["ticker"]] = rec
    return out


def classify_rules(text: str) -> dict[str, bool]:
    t = (text or "").lower()
    midway = any(
        s in t
        for s in (
            "midway",
            "climdw",
            "issuedby=mdw",
            "kmdw",
            "chicago (climdw)",
        )
    )
    ohare = any(s in t for s in ("o'hare", "ohare", "o’hare", "kord", "cliord", "ord"))
    return {"midway": midway, "ohare": ohare}


def printed_x(m: dict, trade: dict | None, x: int) -> tuple[bool, str]:
    """Return (printed, source). Trade max_yes preferred. Last-price fallback only for YES>=0.96."""
    if trade and trade.get("max_yes") is not None:
        my = float(trade["max_yes"])
        return my + 1e-12 >= x / 100.0, "max_yes"
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
    trades = load_trades()
    events = sorted({m.get("event_ticker") for m in markets if m.get("event_ticker")})
    y2026 = [m for m in markets if (m.get("event_ticker") or "").startswith("KXHIGHCHI-26")]

    n_midway = n_ohare = n_rules = 0
    for m in y2026:
        rules = m.get("rules_primary") or ""
        if rules:
            n_rules += 1
            flags = classify_rules(rules)
            if flags["midway"]:
                n_midway += 1
            if flags["ohare"]:
                n_ohare += 1

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

    have_max = [m for m in y2026 if (trades.get(m.get("ticker") or "") or {}).get("max_yes") is not None]
    missing_no_vol = []
    for m in y2026:
        if (m.get("result") or "").lower() != "no":
            continue
        vol = parse_float(m.get("volume_fp")) or 0.0
        if vol <= 0:
            continue
        t = trades.get(m.get("ticker") or "")
        if not t or t.get("max_yes") is None:
            missing_no_vol.append(m.get("ticker"))

    yes_need = []
    for m in y2026:
        if (m.get("result") or "").lower() != "yes":
            continue
        t = trades.get(m.get("ticker") or "")
        last = parse_float(m.get("last_price_dollars")) or 0.0
        vol = parse_float(m.get("volume_fp")) or 0.0
        if not t or t.get("max_yes") is None:
            if last >= 0.70 or vol > 0:
                yes_need.append({"ticker": m.get("ticker"), "last": last, "volume_fp": m.get("volume_fp")})

    ladder = {}
    for x in LEVELS:
        prints = []
        sources = Counter()
        for m in y2026:
            hit, src = printed_x(m, trades.get(m.get("ticker") or ""), x)
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
            "n_max_yes": sources.get("max_yes", 0),
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
            "n_with_trade_max_yes": len(have_max),
            "n_missing_no_volume_tapes": len(missing_no_vol),
            "missing_no_volume_tickers": missing_no_vol,
            "n_yes_still_missing_tape": len(yes_need),
            "yes_missing_tape": yes_need,
            "note": "Missing NO-with-volume tapes bias die% DOWN (spike-then-fade 90s not seen). Last-price fallback is YES>=0.96 lives only.",
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
        f"- Confirmed from event `rules_primary`: {j['n_rules_midway_climdw']} / {j['n_rules']} mention Midway/CLIMDW; {j['n_rules_ohare']} mention O'Hare.",
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
        f"- Tickers with real trade `max_yes`: **{c['n_with_trade_max_yes']}** / {c['n_settled_markets']}",
        f"- Missing NO-with-volume tapes: **{c['n_missing_no_volume_tapes']}** (these bias die% **down**)",
        f"- YES still missing tape (last≥0.70 or volume): **{c['n_yes_still_missing_tape']}**",
        f"- Last-price fallback used only for YES with last≥0.96 (lives). Die% is **not** scored from last_price-only.",
        "",
        "## 2026 YTD ladder (Buy No at 100−X¢ on first X Yes print)",
        "",
        "| X¢ Yes | n | die | die% | EV¢ | fee¢ | EV after fee¢ | max_yes n | YES≥96 fallback n |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for x in LEVELS:
        row = s["ladder"][str(x)]
        die_pct = "—" if row["die_pct"] is None else f"{row['die_pct']:.2f}"
        ev = "—" if row["ev_cents"] is None else f"{row['ev_cents']:+.2f}"
        evf = "—" if row["ev_after_fee_cents"] is None else f"{row['ev_after_fee_cents']:+.2f}"
        lines.append(
            f"| {x} | {row['n']} | {row['n_die']} | {die_pct} | {ev} | {row['fee_cents']:.2f} | {evf} | {row['n_max_yes']} | {row['n_last_yes96']} |"
        )
    nyc = s["vs_nyc_90"]
    r90 = s["ladder"]["90"]
    lines += [
        "",
        "## 90¢ line vs NYC",
        "",
        f"- CHI 2026 YTD: n={nyc['chi_n']}, die%={nyc['chi_die_pct']}, EV after fee={nyc['chi_ev_after_fee_cents']}¢",
        f"- NYC 2026 YTD (given, not refetched): n={nyc['nyc_n']}, die%={nyc['nyc_die_pct']}, EV after fee={nyc['nyc_ev_after_fee_cents']:+.1f}¢",
        f"- Fee at 10¢ No = 0.63¢; breakeven die after fee = 10.63%. Observed 90-No die% = {r90['die_pct']}.",
        "",
        f"## Verdict: **{s['verdict']}**",
        "",
        "Pass only if 90-No is +EV after fee on 2026 YTD. Seasonal splits not claimed unless n per season ≥ ~80.",
        "",
        "## Caveats",
        "",
        "1. **Fill** — assumes a 10¢ No fill at the first 90¢ Yes print (trade max_yes ≥ 0.90, or YES last≥0.96 fallback).",
        "2. **Judge** — Midway (KMDW / CLIMDW), not O'Hare. Source agency changed NWS→TWC on 2026-08-14; station unchanged.",
        "3. **Coverage** — last_price fallback on YES≥96 undercounts spike-then-fade if NO tapes are missing. Missing NO-with-volume tapes bias die% down.",
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
