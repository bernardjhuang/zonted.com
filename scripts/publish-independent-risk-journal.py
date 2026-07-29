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

    gemini = responses["gemini-3.1-pro-preview"]
    gemini_path = ROOT / "trading" / "gemini-risk.json"
    gemini_data = load(gemini_path)
    gemini_entry = {
        "as_of": gemini["as_of_date"], "market_data_through": gemini["as_of_date"],
        "stance": gemini["stance"], "rating": gemini["risk_appetite"],
        "summary": gemini["headline"],
        "sections": [
            {"title": "Methodology", "paragraphs": [gemini["methodology"]["explanation"], "Selected signals: " + "; ".join(gemini["methodology"]["selected_signals"])]},
            {"title": "Journal", "paragraphs": gemini["journal"]},
            {"title": "What supports risk", "paragraphs": gemini["what_supports_risk"]},
            {"title": "What holds it back", "paragraphs": gemini["what_holds_it_back"]},
            {"title": "What changes Gemini's mind", "paragraphs": gemini["what_changes_my_mind"]},
        ],
        "reasoning": gemini["score_interpretation"],
        "citation_note": "This entry preserves Gemini's independently searched model output. Its own limitations apply. Same-session SIP data put VIX at 20.66, so Gemini's reference to the low 18s appears stale and is retained as a model-data defect rather than silently corrected.",
        "sources": gemini["sources"], "limitations": gemini["limitations"],
    }
    gemini_data["model"] = "Gemini 3.1 Pro Preview"
    gemini_data["entries"] = prepend(gemini_data.get("entries", []), gemini_entry, date_key="as_of")
    save(gemini_path, gemini_data)

    meta = responses["muse-spark-1.1"]
    meta_raw = load(run / "raw" / "meta.json")
    meta_text = "\n".join(
        content.get("text", "")
        for item in meta_raw.get("output", []) if item.get("type") == "message"
        for content in item.get("content", []) if content.get("type") == "output_text"
    )
    search_queries = [
        item.get("action", {}).get("query")
        for item in meta_raw.get("output", [])
        if item.get("type") == "web_search_call" and item.get("action", {}).get("type") == "search"
    ]
    usage = meta_raw["usage"]
    meta_path = ROOT / "trading" / "meta-risk.json"
    meta_data = load(meta_path)
    meta_entry = {
        "as_of": meta["as_of_date"], "status": meta_raw["status"], "http_status": 200,
        "response_id": meta_raw["id"], "stance": meta["stance"], "rating": meta["risk_appetite"],
        "derived_rating": meta["risk_appetite"], "summary": meta["headline"],
        "search_queries": search_queries, "verbatim_response": meta_text,
        "journal": meta["journal"], "what_supports_risk": meta["what_supports_risk"],
        "what_holds_it_back": meta["what_holds_it_back"], "what_changes_my_mind": meta["what_changes_my_mind"],
        "headline": meta["headline"], "sources": meta["sources"], "limitations": meta["limitations"],
        "usage": {
            "input_tokens": usage["input_tokens"], "output_tokens": usage["output_tokens"],
            "reasoning_tokens": usage.get("output_tokens_details", {}).get("reasoning_tokens", 0),
            "total_tokens": usage["total_tokens"], "cached_input_tokens": usage.get("input_tokens_details", {}).get("cached_tokens", 0),
        },
        "integrity_note": "This preserves Meta Muse's output as model evidence, not Zonted fact. One cited GDP source is dated 2026-08-28—after this 2026-07-29 assessment—and is therefore a time-travel sourcing defect. The VIX figure is also stale versus the 20.66 same-session close. Both defects remain visible rather than being laundered away.",
    }
    meta_data["prompt"] = (run / "prompts" / "meta.txt").read_text()
    meta_data["entries"] = prepend(meta_data.get("entries", []), meta_entry, date_key="as_of")
    save(meta_path, meta_data)

    fable_path = run / "responses" / "fable.json"
    subprocess.run(["python3", "scripts/update-fable-risk.py", str(fable_path)], cwd=ROOT, check=True)

    grok = responses["grok-4.5"]
    grok_path = ROOT / "trading" / "grok-risk.json"
    grok_data = load(grok_path) if grok_path.exists() else {"schema_version": 1, "model": "Grok 4.5", "entries": []}
    grok_data["entries"] = prepend(grok_data.get("entries", []), grok, date_key="as_of_date", session_key="session")
    save(grok_path, grok_data)

    subprocess.run(["python3", "scripts/update-gemini-risk.py"], cwd=ROOT, check=True)
    subprocess.run(["python3", "scripts/update-meta-risk.py"], cwd=ROOT, check=True)
    subprocess.run(["python3", "scripts/update-grok-risk.py"], cwd=ROOT, check=True)
    print("published independent risk entries: GPT, Gemini, Meta, Fable, Grok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
