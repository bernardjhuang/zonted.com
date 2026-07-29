#!/usr/bin/env python3
"""Build the public Desk position artifact from a reduced live holdings snapshot."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ROOT / "trading" / "desk-position-profiles.json"
OUTPUT = ROOT / "trading" / "desk-positions.json"


def level(value: Any) -> str:
    number = float(value)
    return f"{number:.2f}".rstrip("0").rstrip(".")


def option_label(row: dict[str, Any]) -> str:
    expiration = dt.date.fromisoformat(str(row["expiration"]))
    option_type = str(row["option_type"]).lower()
    if option_type not in {"call", "put"}:
        raise ValueError(f"unsupported option type: {option_type}")
    return f"{expiration.strftime('%b %Y')} ${level(row['strike'])} {option_type}"


def render(holdings: dict[str, Any], profiles_payload: dict[str, Any]) -> dict[str, Any]:
    if profiles_payload.get("schema_version") != 1 or not isinstance(profiles_payload.get("profiles"), dict):
        raise ValueError("desk position profiles must use schema_version 1")
    instruments = holdings.get("desk_instruments")
    if not isinstance(instruments, dict) or not instruments:
        raise ValueError("live holdings snapshot contains no desk_instruments")
    risk_summary = holdings.get("risk_summary")
    if not isinstance(risk_summary, dict):
        raise ValueError("live holdings snapshot needs risk_summary")
    summary_rules = {
        "gross_delta_leverage": lambda value: value >= 0,
        "net_delta_exposure_percent": lambda value: True,
        "premium_at_risk_percent": lambda value: value >= 0,
        "theta_percent_per_day": lambda value: True,
        "cash_percent": lambda value: True,
    }
    for key, valid in summary_rules.items():
        value = risk_summary.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not valid(float(value)):
            raise ValueError(f"risk_summary needs valid {key}")
    quantity_basis = risk_summary.get("quantity_basis")
    if not isinstance(quantity_basis, str) or not quantity_basis.strip():
        raise ValueError("risk_summary needs quantity_basis")

    profiles = profiles_payload["profiles"]
    missing = sorted(set(instruments) - set(profiles))
    if missing:
        raise ValueError(f"held symbols need authored Desk profiles: {missing}")

    positions: list[dict[str, Any]] = []
    for symbol in sorted(instruments):
        live = instruments[symbol]
        side = str(live.get("equity_side") or "long")
        if side not in {"long", "short"}:
            raise ValueError(f"{symbol} has unsupported equity_side: {side}")

        risk_values: dict[str, Any] = {}
        for key in ("exposure_percent", "capital_percent", "premium_at_risk_percent", "theta_percent_per_day"):
            value = live.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{symbol} needs finite {key}")
            if key in {"capital_percent", "premium_at_risk_percent"} and value < 0:
                raise ValueError(f"{symbol} needs nonnegative {key}")
            risk_values[key] = round(float(value), 2 if key == "theta_percent_per_day" else 1)
        if risk_values["premium_at_risk_percent"] > risk_values["capital_percent"] + 0.1:
            raise ValueError(f"{symbol} premium risk cannot exceed capital")

        iv = live.get("implied_volatility_percent")
        delta_used = live.get("delta_used")
        min_dte = live.get("min_dte")
        if iv is None:
            if delta_used is not None or min_dte is not None:
                raise ValueError(f"{symbol} option risk fields must be all present or all null")
        else:
            if isinstance(iv, bool) or not isinstance(iv, (int, float)) or not math.isfinite(iv) or iv <= 0:
                raise ValueError(f"{symbol} needs positive implied_volatility_percent")
            if isinstance(delta_used, bool) or not isinstance(delta_used, (int, float)) or not -1 <= delta_used <= 1:
                raise ValueError(f"{symbol} needs delta_used between -1 and 1")
            if isinstance(min_dte, bool) or not isinstance(min_dte, int) or min_dte < 0:
                raise ValueError(f"{symbol} needs nonnegative min_dte")
        unstable = live.get("unstable_delta")
        if not isinstance(unstable, bool):
            raise ValueError(f"{symbol} needs boolean unstable_delta")

        parts = ["Short equity" if side == "short" else "Equity"]
        options = live.get("options") or []
        if not isinstance(options, list):
            raise ValueError(f"{symbol} options must be an array")
        parts.extend(option_label(row) for row in sorted(options, key=lambda row: (str(row["expiration"]), float(row["strike"]), str(row["option_type"]))))
        profile = profiles[symbol]
        positions.append({
            "symbol": symbol,
            "instrument": " · ".join(parts),
            **risk_values,
            "implied_volatility_percent": round(float(iv), 1) if iv is not None else None,
            "delta_used": round(float(delta_used), 4) if delta_used is not None else None,
            "min_dte": min_dte,
            "unstable_delta": unstable,
            "kill": profile.get("kill"),
            "flair": profile["flair"],
            "sector": profile["sector"],
            "sector_etf": profile["sector_etf"],
            "thesis": profile["thesis"],
        })
    positions.sort(key=lambda row: (-row["exposure_percent"], row["symbol"]))
    sleeves: dict[str, dict[str, float]] = {}
    for row in positions:
        sleeve = sleeves.setdefault(row["flair"], {
            "capital_percent": 0.0,
            "exposure_percent": 0.0,
            "premium_at_risk_percent": 0.0,
        })
        for key in sleeve:
            sleeve[key] += float(row[key])
    for sleeve in sleeves.values():
        for key, value in sleeve.items():
            sleeve[key] = round(value, 1)
    public_summary = {key: risk_summary[key] for key in (*summary_rules, "quantity_basis")}
    return {"schema_version": 3, "risk_summary": public_summary, "sleeves": sleeves, "positions": positions}


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
