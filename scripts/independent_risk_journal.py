#!/usr/bin/env python3
"""Prepare and validate deferred, independent market-risk model runs.

This CLI never calls a model and never edits public journal data. It creates one
blind prompt per model, validates returned JSON, and bundles complete runs for a
later human/agent-reviewed publish step.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
from typing import Any
from urllib.parse import urlparse

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "prompts" / "independent-market-risk-journal.md"
PROMPT_VERSION = "zonted-independent-risk-v1"
SCHEMA_VERSION = 1
SESSIONS = {"pre-market", "post-close"}
STANCES = {"Risk-on", "Neutral", "Risk-off"}
CONFIDENCE = {"High", "Medium", "Low"}

MODELS = (
    {
        "slug": "gpt",
        "model_id": "gpt-5.6-sol",
        "model_name": "GPT-5.6",
        "journal_target": "trading/risk-journal.json",
    },
    {
        "slug": "fable",
        "model_id": "claude-fable-5",
        "model_name": "Claude Fable 5",
        "journal_target": "trading/fable-risk.json",
    },
    {
        "slug": "grok",
        "model_id": "grok-4.5",
        "model_name": "Grok 4.5",
        "journal_target": "trading/grok-risk/index.html",
    },
)
MODELS_BY_SLUG = {model["slug"]: model for model in MODELS}


class ContractError(ValueError):
    """A staged model response violates the independent journal contract."""


def parse_date(value: str) -> str:
    try:
        return dt.date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ContractError(f"as-of date must be YYYY-MM-DD: {value!r}") from exc


def render_prompt(model: dict[str, str], as_of_date: str, session: str) -> str:
    text = PROMPT_PATH.read_text()
    replacements = {
        "{{MODEL_NAME}}": model["model_name"],
        "{{MODEL_ID}}": model["model_id"],
        "{{AS_OF_DATE}}": as_of_date,
        "{{SESSION}}": session,
    }
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    if "{{" in text or "}}" in text:
        raise ContractError("prompt template contains unresolved placeholders")
    return text


def prepare_run(run_dir: pathlib.Path, as_of_date: str, session: str) -> dict[str, Any]:
    as_of_date = parse_date(as_of_date)
    if session not in SESSIONS:
        raise ContractError(f"session must be one of {sorted(SESSIONS)}")
    if run_dir.exists() and any(run_dir.iterdir()):
        raise ContractError(f"run directory is not empty: {run_dir}")

    prompts_dir = run_dir / "prompts"
    responses_dir = run_dir / "responses"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    responses_dir.mkdir(parents=True, exist_ok=True)

    model_rows = []
    for model in MODELS:
        prompt_name = f"{model['slug']}.txt"
        response_name = f"{model['slug']}.json"
        (prompts_dir / prompt_name).write_text(render_prompt(model, as_of_date, session))
        model_rows.append(
            {
                **model,
                "prompt_file": f"prompts/{prompt_name}",
                "response_file": f"responses/{response_name}",
            }
        )

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "prompt_version": PROMPT_VERSION,
        "as_of_date": as_of_date,
        "session": session,
        "execution_policy": "deferred-explicit-user-trigger-only",
        "method_policy": "independent-model-selected-methodology",
        "models": model_rows,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def _require_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{key} must be a non-empty string")
    return value.strip()


def _require_list(payload: dict[str, Any], key: str, length: int | None = None) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ContractError(f"{key} must be an array")
    if length is not None and len(value) != length:
        raise ContractError(f"{key} must contain exactly {length} items")
    return value


def _validate_text_list(payload: dict[str, Any], key: str, length: int | None = None) -> None:
    values = _require_list(payload, key, length)
    if not all(isinstance(value, str) and value.strip() for value in values):
        raise ContractError(f"{key} must contain non-empty strings")


def _valid_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def validate_entry(
    entry: dict[str, Any], model: dict[str, str], as_of_date: str, session: str
) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise ContractError("response must be one JSON object")
    expected = {
        "schema_version": SCHEMA_VERSION,
        "prompt_version": PROMPT_VERSION,
        "as_of_date": as_of_date,
        "session": session,
        "author": model["model_name"],
        "model_id": model["model_id"],
    }
    for key, value in expected.items():
        if entry.get(key) != value:
            raise ContractError(f"{key} must equal {value!r}")

    status = entry.get("decision_status")
    if status not in {"publishable", "insufficient_data"}:
        raise ContractError("decision_status must be publishable or insufficient_data")
    _validate_text_list(entry, "limitations")

    if status == "insufficient_data":
        null_fields = {
            "stance",
            "risk_appetite",
            "score_interpretation",
            "confidence",
            "headline",
            "methodology",
        }
        for key in null_fields:
            if entry.get(key) is not None:
                raise ContractError(f"{key} must be null when decision_status is insufficient_data")
        for key in (
            "journal",
            "what_supports_risk",
            "what_holds_it_back",
            "what_changes_my_mind",
            "sources",
        ):
            if entry.get(key) != []:
                raise ContractError(f"{key} must be empty when decision_status is insufficient_data")
        if not entry["limitations"]:
            raise ContractError("insufficient_data requires at least one limitation")
        return entry

    if entry.get("stance") not in STANCES:
        raise ContractError(f"stance must be one of {sorted(STANCES)}")
    score = entry.get("risk_appetite")
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 10:
        raise ContractError("risk_appetite must be a number from 0 through 10")
    if entry.get("confidence") not in CONFIDENCE:
        raise ContractError(f"confidence must be one of {sorted(CONFIDENCE)}")
    for key in ("score_interpretation", "headline"):
        _require_text(entry, key)

    methodology = entry.get("methodology")
    if not isinstance(methodology, dict):
        raise ContractError("methodology must be an object")
    for key in ("name", "explanation"):
        _require_text(methodology, key)
    _validate_text_list(methodology, "selected_signals")
    if not methodology["selected_signals"]:
        raise ContractError("methodology.selected_signals must not be empty")

    _validate_text_list(entry, "journal", 3)
    _validate_text_list(entry, "what_supports_risk", 3)
    _validate_text_list(entry, "what_holds_it_back", 3)
    _validate_text_list(entry, "what_changes_my_mind", 2)

    sources = _require_list(entry, "sources")
    if not sources:
        raise ContractError("publishable response requires at least one source")
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise ContractError(f"sources[{index}] must be an object")
        for key in ("title", "as_of", "claim"):
            try:
                _require_text(source, key)
            except ContractError as exc:
                raise ContractError(f"sources[{index}].{exc}") from exc
        url = source.get("url")
        if not isinstance(url, str) or not _valid_http_url(url):
            raise ContractError(f"sources[{index}].url must be an http(s) URL")
    return entry


def load_manifest(run_dir: pathlib.Path) -> dict[str, Any]:
    path = run_dir / "manifest.json"
    if not path.is_file():
        raise ContractError(f"manifest not found: {path}")
    manifest = json.loads(path.read_text())
    if manifest.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("manifest schema_version mismatch")
    if manifest.get("prompt_version") != PROMPT_VERSION:
        raise ContractError("manifest prompt_version mismatch")
    return manifest


def validate_run(run_dir: pathlib.Path) -> list[dict[str, Any]]:
    manifest = load_manifest(run_dir)
    entries = []
    for row in manifest.get("models", []):
        model = MODELS_BY_SLUG.get(row.get("slug"))
        if model is None or any(row.get(key) != model[key] for key in model):
            raise ContractError(f"manifest model metadata mismatch: {row.get('slug')!r}")
        response_path = run_dir / row["response_file"]
        if not response_path.is_file():
            raise ContractError(f"missing response: {response_path}")
        try:
            entry = json.loads(response_path.read_text())
        except json.JSONDecodeError as exc:
            raise ContractError(f"invalid JSON in {response_path}: {exc}") from exc
        entries.append(
            validate_entry(entry, model, manifest["as_of_date"], manifest["session"])
        )
    if len(entries) != len(MODELS):
        raise ContractError(f"run must contain all {len(MODELS)} configured models")
    return entries


def bundle_run(run_dir: pathlib.Path, output_path: pathlib.Path) -> dict[str, Any]:
    manifest = load_manifest(run_dir)
    entries = validate_run(run_dir)
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "prompt_version": PROMPT_VERSION,
        "as_of_date": manifest["as_of_date"],
        "session": manifest["session"],
        "method_policy": manifest["method_policy"],
        "entries": entries,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n")
    return bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare", help="create prompts; make no API calls")
    prepare.add_argument("--as-of", required=True, dest="as_of_date")
    prepare.add_argument("--session", choices=sorted(SESSIONS), required=True)
    prepare.add_argument("--run-dir", type=pathlib.Path, required=True)

    validate = commands.add_parser("validate", help="validate all staged model responses")
    validate.add_argument("--run-dir", type=pathlib.Path, required=True)

    bundle = commands.add_parser("bundle", help="validate and bundle; do not publish")
    bundle.add_argument("--run-dir", type=pathlib.Path, required=True)
    bundle.add_argument("--output", type=pathlib.Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "prepare":
            manifest = prepare_run(args.run_dir, args.as_of_date, args.session)
            print(
                f"prepared {len(manifest['models'])} independent prompts in {args.run_dir}; "
                "no models called and no journals changed"
            )
        elif args.command == "validate":
            entries = validate_run(args.run_dir)
            print(f"validated {len(entries)} independent model responses")
        else:
            bundle = bundle_run(args.run_dir, args.output)
            print(
                f"bundled {len(bundle['entries'])} responses at {args.output}; "
                "public journals unchanged"
            )
    except (ContractError, OSError, json.JSONDecodeError) as exc:
        print(f"independent-risk-journal: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
