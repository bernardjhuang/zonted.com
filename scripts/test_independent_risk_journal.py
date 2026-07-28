#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "independent_risk_journal.py"
SPEC = importlib.util.spec_from_file_location("independent_risk_journal", MODULE_PATH)
assert SPEC and SPEC.loader
risk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(risk)


class IndependentRiskJournalTest(unittest.TestCase):
    def valid_entry(self, model: dict[str, str]) -> dict:
        return {
            "schema_version": 1,
            "prompt_version": risk.PROMPT_VERSION,
            "decision_status": "publishable",
            "as_of_date": "2026-07-27",
            "session": "post-close",
            "author": model["model_name"],
            "model_id": model["model_id"],
            "stance": "Neutral",
            "risk_appetite": 5.4,
            "score_interpretation": "My framework treats five as balanced and this tape as mildly constructive.",
            "confidence": "Medium",
            "headline": "The model's independent read is balanced.",
            "methodology": {
                "name": f"{model['slug']} regime synthesis",
                "explanation": "I selected and weighted the evidence I considered most relevant.",
                "selected_signals": ["breadth", "credit", "volatility"],
            },
            "journal": ["Paragraph one.", "Paragraph two.", "Paragraph three."],
            "what_supports_risk": ["Support one.", "Support two.", "Support three."],
            "what_holds_it_back": ["Risk one.", "Risk two.", "Risk three."],
            "what_changes_my_mind": ["Upgrade condition.", "Downgrade condition."],
            "sources": [
                {
                    "title": "Primary market source",
                    "url": "https://example.com/market-source",
                    "as_of": "2026-07-27",
                    "claim": "Supports one material observation.",
                }
            ],
            "limitations": ["One slow input may lag the close."],
        }

    def prepare(self, root: pathlib.Path) -> tuple[pathlib.Path, dict]:
        run_dir = root / "run"
        manifest = risk.prepare_run(run_dir, "2026-07-27", "post-close")
        return run_dir, manifest

    def test_prepare_creates_five_blind_prompts_without_touching_journals(self) -> None:
        targets = [ROOT / model["journal_target"] for model in risk.MODELS]
        before = {path: path.read_bytes() for path in targets}
        with tempfile.TemporaryDirectory() as tmp:
            run_dir, manifest = self.prepare(pathlib.Path(tmp))
            self.assertEqual(len(manifest["models"]), 5)
            self.assertEqual(manifest["execution_policy"], "deferred-explicit-user-trigger-only")
            self.assertEqual(
                manifest["method_policy"], "independent-model-selected-methodology"
            )
            for model in risk.MODELS:
                prompt = (run_dir / "prompts" / f"{model['slug']}.txt").read_text()
                self.assertIn(model["model_id"], prompt)
                self.assertIn("Choose your own methodology", prompt)
                self.assertIn("Do not use any mechanical baseline", prompt)
                self.assertIn("Do not try to agree with the other models", prompt)
                self.assertNotIn("{{", prompt)
                self.assertFalse((run_dir / "responses" / f"{model['slug']}.json").exists())
        after = {path: path.read_bytes() for path in targets}
        self.assertEqual(before, after)

    def test_validate_accepts_independent_publishable_entry(self) -> None:
        model = risk.MODELS_BY_SLUG["grok"]
        entry = self.valid_entry(model)
        self.assertIs(
            risk.validate_entry(entry, model, "2026-07-27", "post-close"), entry
        )

    def test_validate_rejects_missing_methodology_and_identity_drift(self) -> None:
        model = risk.MODELS_BY_SLUG["meta"]
        no_method = self.valid_entry(model)
        no_method["methodology"] = None
        with self.assertRaisesRegex(risk.ContractError, "methodology must be an object"):
            risk.validate_entry(no_method, model, "2026-07-27", "post-close")

        wrong_model = self.valid_entry(model)
        wrong_model["model_id"] = "some-other-model"
        with self.assertRaisesRegex(risk.ContractError, "model_id must equal"):
            risk.validate_entry(wrong_model, model, "2026-07-27", "post-close")

    def test_validate_accepts_honest_insufficient_data(self) -> None:
        model = risk.MODELS_BY_SLUG["fable"]
        entry = self.valid_entry(model)
        entry.update(
            {
                "decision_status": "insufficient_data",
                "stance": None,
                "risk_appetite": None,
                "score_interpretation": None,
                "confidence": None,
                "headline": None,
                "methodology": None,
                "journal": [],
                "what_supports_risk": [],
                "what_holds_it_back": [],
                "what_changes_my_mind": [],
                "sources": [],
                "limitations": ["Current market data was unavailable."],
            }
        )
        self.assertIs(
            risk.validate_entry(entry, model, "2026-07-27", "post-close"), entry
        )

    def test_bundle_requires_every_model_and_remains_staged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            run_dir, manifest = self.prepare(root)
            for model in risk.MODELS:
                response = self.valid_entry(model)
                (run_dir / "responses" / f"{model['slug']}.json").write_text(
                    json.dumps(response)
                )
            output = root / "bundle.json"
            bundle = risk.bundle_run(run_dir, output)
            self.assertEqual(len(bundle["entries"]), 5)
            self.assertEqual(
                [entry["model_id"] for entry in bundle["entries"]],
                [model["model_id"] for model in risk.MODELS],
            )
            self.assertEqual(json.loads(output.read_text()), bundle)
            self.assertEqual(manifest["as_of_date"], bundle["as_of_date"])

    def test_validate_run_fails_when_any_model_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir, _ = self.prepare(pathlib.Path(tmp))
            model = risk.MODELS[0]
            (run_dir / "responses" / f"{model['slug']}.json").write_text(
                json.dumps(self.valid_entry(model))
            )
            with self.assertRaisesRegex(risk.ContractError, "missing response"):
                risk.validate_run(run_dir)


if __name__ == "__main__":
    unittest.main()
