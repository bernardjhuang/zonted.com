#!/usr/bin/env python3
"""Publish a validated independent-risk run through the Trading Desk's legacy journals."""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text())


def save(path: pathlib.Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def prepend(entries: list[dict], entry: dict, *, date_key: str, session_key: str | None = None) -> list[dict]:
    def same(old: dict) -> bool:
        if old.get(date_key) != entry.get(date_key):
            return False
        return session_key is None or old.get(session_key) == entry.get(session_key)
    return [entry] + [old for old in entries if not same(old)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=pathlib.Path)
    args = parser.parse_args()
    run = args.run_dir
    subprocess.run(["python3", "scripts/independent_risk_journal.py", "validate", "--run-dir", str(run)], cwd=ROOT, check=True)
    responses = {load(path)["model_id"]: load(path) for path in sorted((run / "responses").glob("*.json"))}

    gpt = responses["gpt-5.6-sol"]
    gpt_data_path = ROOT / "trading" / "risk-journal.json"
    gpt_data = load(gpt_data_path)
    gpt_entry = {
        "date": gpt["as_of_date"], "author": gpt["author"], "stance": gpt["stance"],
        "risk_appetite": gpt["risk_appetite"], "lean": f'{gpt["confidence"]} confidence · {gpt["methodology"]["name"]}',
        "headline": gpt["headline"], "journal": gpt["journal"],
        "what_supports_risk": gpt["what_supports_risk"], "what_holds_it_back": gpt["what_holds_it_back"],
        "what_changes_my_mind": gpt["what_changes_my_mind"],
        "source_note": "Sources: " + " · ".join(source["title"] for source in gpt["sources"]) + ". Limitations: " + " ".join(gpt["limitations"]),
    }
    gpt_data["entries"] = prepend(gpt_data.get("entries", []), gpt_entry, date_key="date")
    save(gpt_data_path, gpt_data)


    fable_path = run / "responses" / "fable.json"
    subprocess.run(["python3", "scripts/update-fable-risk.py", str(fable_path)], cwd=ROOT, check=True)

    grok = responses["grok-4.5"]
    grok_path = ROOT / "trading" / "grok-risk.json"
    grok_data = load(grok_path) if grok_path.exists() else {"schema_version": 1, "model": "Grok 4.5", "entries": []}
    grok_data["entries"] = prepend(grok_data.get("entries", []), grok, date_key="as_of_date", session_key="session")
    save(grok_path, grok_data)

    subprocess.run(["python3", "scripts/update-grok-risk.py"], cwd=ROOT, check=True)
    print("published independent risk entries: GPT, Fable, Grok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
