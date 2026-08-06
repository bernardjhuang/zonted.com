#!/usr/bin/env python3
"""Validate and publish one GPT post-close risk journal response.

This adapter intentionally owns only GPT's journal and generated Trading Desk shells.
It never mutates Grok or Fable journal data.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import pathlib
import subprocess
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
JOURNAL = ROOT / "trading" / "risk-journal.json"
MARKET = ROOT / "trading" / "market-ytd.json"
RISK_MODULE = ROOT / "scripts" / "independent_risk_journal.py"


def load(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def save_atomic(path: pathlib.Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def risk_contract_module():
    spec = importlib.util.spec_from_file_location("independent_risk_journal", RISK_MODULE)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load independent risk journal contract")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_source_dates(response: dict[str, Any]) -> None:
    cutoff = dt.date.fromisoformat(response["as_of_date"])
    for index, source in enumerate(response["sources"]):
        raw = str(source["as_of"]).strip()[:10]
        try:
            source_date = dt.date.fromisoformat(raw)
        except ValueError:
            continue
        if source_date > cutoff:
            raise ValueError(f"sources[{index}].as_of {source_date} is after journal cutoff {cutoff}")


def adapt_entry(response: dict[str, Any]) -> dict[str, Any]:
    methodology = response["methodology"]
    return {
        "date": response["as_of_date"],
        "author": response["author"],
        "stance": response["stance"],
        "risk_appetite": response["risk_appetite"],
        "lean": f'{response["confidence"]} confidence · {methodology["name"]}',
        "headline": response["headline"],
        "journal": response["journal"],
        "what_supports_risk": response["what_supports_risk"],
        "what_holds_it_back": response["what_holds_it_back"],
        "what_changes_my_mind": response["what_changes_my_mind"],
        "source_note": "Sources: "
        + " · ".join(f'{source["title"]} — {source["url"]}' for source in response["sources"])
        + ". Limitations: "
        + " ".join(response["limitations"]),
        "score_interpretation": response["score_interpretation"],
        "methodology": methodology,
        "sources": response["sources"],
        "limitations": response["limitations"],
    }


def prepend_for_date(entries: list[dict[str, Any]], entry: dict[str, Any]) -> list[dict[str, Any]]:
    return [entry] + [old for old in entries if old.get("date") != entry["date"]]


def publish(response_path: pathlib.Path) -> dict[str, Any]:
    response = load(response_path)
    market_date = str(load(MARKET).get("as_of") or "")
    if not market_date:
        raise ValueError("market-ytd.json has no as_of date")
    if response.get("as_of_date") != market_date:
        raise ValueError(
            f'GPT response date {response.get("as_of_date")!r} does not match market date {market_date!r}'
        )
    if response.get("session") != "post-close":
        raise ValueError("GPT journal publisher accepts post-close responses only")

    contract = risk_contract_module()
    contract.validate_entry(
        response,
        contract.MODELS_BY_SLUG["gpt"],
        market_date,
        "post-close",
    )
    if response["decision_status"] != "publishable":
        raise ValueError("refusing to publish an insufficient_data response")
    validate_source_dates(response)

    journal = load(JOURNAL)
    entry = adapt_entry(response)
    journal["updated_at"] = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    journal["entries"] = prepend_for_date(journal.get("entries", []), entry)
    save_atomic(JOURNAL, journal)

    subprocess.run(
        ["python3", "scripts/build-trading-desk.py", "--mode", "close"],
        cwd=ROOT,
        check=True,
    )
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--response", required=True, type=pathlib.Path)
    args = parser.parse_args()
    entry = publish(args.response)
    print(
        f'published GPT risk journal {entry["date"]}: '
        f'{entry["stance"]} ({entry["risk_appetite"]:g}/10)'
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
