#!/usr/bin/env python3
"""Build the public Desk position artifact from a reduced live holdings snapshot."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "trading" / "desk-position-profiles.json"
OUTPUT = ROOT / "trading" / "desk-positions.json"


def level(value: Any) -> str:
    number = float(value)
    return f"{number:.2f}".rstrip("0").rstrip(".")


def money(value: Any) -> str:
    return f"{float(value):.2f}"


def option_label(row: dict[str, Any]) -> str:
    expiration = dt.date.fromisoformat(str(row["expiration"]))
    option_type = str(row["option_type"]).lower()
    if option_type not in {"call", "put"}:
        raise ValueError(f"unsupported option type: {option_type}")
    return (
        f"{expiration.strftime('%b %Y')} ${level(row['strike'])} {option_type} "
        f"@ ${money(row['entry'])}"
    )


def render(holdings: dict[str, Any], profiles_payload: dict[str, Any]) -> dict[str, Any]:
    if profiles_payload.get("schema_version") != 1 or not isinstance(profiles_payload.get("profiles"), dict):
        raise ValueError("desk position profiles must use schema_version 1")
    instruments = holdings.get("desk_instruments")
    if not isinstance(instruments, dict) or not instruments:
        raise ValueError("live holdings snapshot contains no desk_instruments")
    profiles = profiles_payload["profiles"]
    missing = sorted(set(instruments) - set(profiles))
    if missing:
        raise ValueError(f"held symbols need authored Desk profiles: {missing}")

    positions: list[dict[str, Any]] = []
    for symbol in sorted(instruments):
        live = instruments[symbol]
        entry = live.get("equity_entry")
        if not isinstance(entry, (int, float)) or entry <= 0:
            raise ValueError(f"{symbol} needs a positive equity_entry for its Desk price chart")
        side = str(live.get("equity_side") or "long")
        if side not in {"long", "short"}:
            raise ValueError(f"{symbol} has unsupported equity_side: {side}")
        parts = [f"{'Short equity' if side == 'short' else 'Equity'} @ ${money(entry)}"]
        options = live.get("options") or []
        if not isinstance(options, list):
            raise ValueError(f"{symbol} options must be an array")
        parts.extend(option_label(row) for row in sorted(options, key=lambda row: (str(row["expiration"]), float(row["strike"]), str(row["option_type"]))))
        profile = profiles[symbol]
        positions.append({
            "symbol": symbol,
            "instrument": " · ".join(parts),
            "entry": round(float(entry), 2),
            "kill": profile.get("kill"),
            "flair": profile["flair"],
            "sector": profile["sector"],
            "sector_etf": profile["sector_etf"],
            "thesis": profile["thesis"],
        })
    return {"schema_version": 1, "positions": positions}


def serialize(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--holdings", type=Path, required=True, help="reduced live holdings JSON")
    parser.add_argument("--profiles", type=Path, default=PROFILES)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = serialize(render(json.loads(args.holdings.read_text()), json.loads(args.profiles.read_text())))
    if args.check:
        if not args.output.exists() or args.output.read_text() != rendered:
            print("[desk-positions] stale")
            return 1
        print("[desk-positions] current")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    temp.write_text(rendered)
    os.replace(temp, args.output)
    print(f"[desk-positions] built {len(json.loads(rendered)['positions'])} live symbols")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
