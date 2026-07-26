#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import statistics
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "trading" / "themes" / "index.html"
DATA = ROOT / "trading" / "themes.json"
SCRIPT = ROOT / "js" / "trading-themes.js"


class TradingThemesContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.page = PAGE.read_text()
        cls.payload = json.loads(DATA.read_text())
        cls.script = SCRIPT.read_text()
        cls.theme = cls.payload["themes"][0]

    def test_route_loads_exact_versioned_assets(self) -> None:
        data_hash = hashlib.sha256(DATA.read_bytes()).hexdigest()[:12]
        script_hash = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()[:12]
        self.assertIn(f'/trading/themes.json?v={data_hash}', self.page)
        self.assertIn(f'/js/trading-themes.js?v={script_hash}', self.page)
        self.assertIn('<title>Themes — Trading Desk — Zonted</title>', self.page)
        self.assertIn('aria-current="page">Themes</a>', self.page)
        self.assertIn('id="themes-live"', self.page)

    def test_energy_theme_has_final_adversarial_synthesis(self) -> None:
        self.assertEqual(self.payload["schema_version"], 1)
        self.assertEqual(self.payload["as_of"], "2026-07-24")
        self.assertEqual(len(self.payload["themes"]), 1)
        self.assertEqual(self.theme["id"], "ai-power-scarcity")
        self.assertEqual(self.theme["category"], "Energy")
        self.assertIn("The demand thesis survives", self.theme["final_verdict"])
        self.assertGreaterEqual(len(self.theme["adversarial_review"]["grok"]), 5)
        self.assertGreaterEqual(len(self.theme["adversarial_review"]["fable"]), 5)
        self.assertGreaterEqual(len(self.theme["what_survived"]), 5)
        self.assertGreaterEqual(len(self.theme["residual_edge"]), 6)
        self.assertGreaterEqual(len(self.theme["falsifiers"]), 6)
        self.assertNotIn("198 GW", " ".join(self.theme["what_survived"]))

    def test_model_scores_are_honest_and_consensus_is_median(self) -> None:
        reviews = self.theme["model_reviews"]
        self.assertEqual(
            [row["model"] for row in reviews],
            ["Grok (version not supplied)", "Claude Fable", "Gemini 3.1 Pro", "GPT-5.6"],
        )
        grok = reviews[0]
        self.assertEqual(grok["role"], "User-supplied original map")
        self.assertIn("Bernard supplied", grok["verdict"])
        self.assertIsNone(grok["knowledge_saturation"])
        self.assertIsNone(grok["price_saturation"])
        scored = reviews[1:]
        for field in ("knowledge_saturation", "price_saturation"):
            values = [row[field] for row in scored]
            self.assertTrue(all(isinstance(value, int) and 0 <= value <= 100 for value in values))
            self.assertEqual(self.theme["consensus_scores"][field], int(statistics.median(values)))
        self.assertIn("none was invented", self.payload["method"]["consensus"])

    def test_layer_scores_and_research_buckets_are_complete(self) -> None:
        layers = self.theme["layer_scorecard"]
        self.assertEqual(len(layers), 8)
        self.assertEqual(len({row["layer"] for row in layers}), len(layers))
        for row in layers:
            self.assertTrue(row["symbols"])
            self.assertTrue(row["read"])
            self.assertTrue(0 <= row["knowledge_saturation"] <= 100)
            self.assertTrue(0 <= row["price_saturation"] <= 100)
        self.assertEqual(
            [row["bucket"] for row in self.theme["research_priority"]],
            ["Investigate first", "Good businesses, crowded prices", "Speculation, not core exposure"],
        )

    def test_sources_and_market_snapshot_are_auditable(self) -> None:
        self.assertEqual(self.theme["valuation_snapshot"]["date"], self.payload["as_of"])
        self.assertGreaterEqual(len(self.theme["valuation_snapshot"]["rows"]), 10)
        self.assertGreaterEqual(len(self.theme["sources"]), 8)
        self.assertTrue(all(row["url"].startswith("https://") for row in self.theme["sources"]))
        self.assertTrue(any("pjm.com" in row["url"] for row in self.theme["sources"]))
        self.assertTrue(any("ercot.com" in row["url"] for row in self.theme["sources"]))

    def test_renderer_escapes_copy_and_exposes_all_sections(self) -> None:
        self.assertIn("const esc =", self.script)
        self.assertIn("replaceAll('&', '&amp;')", self.script)
        for text in (
            "Model reviews",
            "Saturation by layer",
            "Adversarial review",
            "What survives the attack",
            "Where edge may remain",
            "Research priority",
            "Valuation snapshot",
            "Falsifiers",
            "Watch next",
            "Sources",
        ):
            self.assertIn(text, self.script)
        self.assertRegex(self.script, r"fetch\(shell\.dataset\.url")


if __name__ == "__main__":
    unittest.main(verbosity=2)
