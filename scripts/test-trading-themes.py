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
        cls.energy = next(theme for theme in cls.payload["themes"] if theme["id"] == "ai-power-scarcity")
        cls.frontier = next(theme for theme in cls.payload["themes"] if theme["id"] == "frontier-intelligence-value-capture")
        cls.theme = cls.energy

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
        self.assertEqual(len(self.payload["themes"]), 9)
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
            ["Grok 4.5", "Claude Fable", "Gemini 3.1 Pro", "GPT-5.6"],
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
        self.assertIn("never invented", self.payload["method"]["consensus"])

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

    def test_frontier_intelligence_theme_is_complete_and_honest(self) -> None:
        theme = self.frontier
        self.assertEqual(theme["category"], "Frontier intelligence")
        self.assertEqual(len(theme["layer_scorecard"]), 11)
        self.assertEqual([row["model"] for row in theme["model_reviews"]], ["GPT-5.6", "Claude Fable"])
        self.assertNotIn("Gemini", " ".join(row["model"] for row in theme["model_reviews"]))
        self.assertIsInstance(theme["adversarial_review"], list)
        self.assertGreaterEqual(len(theme["what_survived"]), 6)
        self.assertGreaterEqual(len(theme["residual_edge"]), 7)
        self.assertGreaterEqual(len(theme["falsifiers"]), 7)
        self.assertGreaterEqual(len(theme["sources"]), 12)
        self.assertEqual(theme["valuation_snapshot"]["date"], self.payload["as_of"])
        self.assertGreaterEqual(len(theme["valuation_snapshot"]["rows"]), 10)
        self.assertIn("missing model scores are never invented", self.payload["method"]["consensus"])

    def test_every_theme_consensus_is_the_median_of_scored_reviews(self) -> None:
        for theme in self.payload["themes"]:
            scored = [row for row in theme["model_reviews"] if row["knowledge_saturation"] is not None]
            self.assertGreaterEqual(len(scored), 1, theme["id"])
            for field in ("knowledge_saturation", "price_saturation"):
                values = [row[field] for row in scored]
                self.assertTrue(all(isinstance(value, int) and 0 <= value <= 100 for value in values))
                self.assertEqual(theme["consensus_scores"][field], int(statistics.median(values)), theme["id"])

    def test_frontier_adversarial_review_covers_the_stale_stock_map(self) -> None:
        columns = self.frontier["adversarial_review"]
        self.assertGreaterEqual(len(columns), 3)
        fable = next(row for row in columns if "lap behind" in row["title"])
        self.assertGreaterEqual(len(fable["bullets"]), 6)
        prose = " ".join(fable["bullets"])
        for claim in ("opening prints", "ICH M15", "Altaris", "vacancy"):
            self.assertIn(claim, prose)

    def test_valuation_snapshots_use_closing_prices_not_opens(self) -> None:
        """Regression: the frontier table originally shipped Friday's opening prints."""
        opens_that_shipped_by_mistake = {
            "TMO": "$573.64", "TER": "$365.48", "RKLB": "$69.31",
            "VEEV": "$182.00", "CDNS": "$335.24", "PGR": "$210.76",
        }
        closes = {row["symbol"]: row["price"] for row in self.frontier["valuation_snapshot"]["rows"]}
        for symbol, stale in opens_that_shipped_by_mistake.items():
            self.assertNotEqual(closes[symbol], stale, f"{symbol} reverted to the opening print")
        self.assertEqual(closes["TMO"], "$568.27")
        self.assertEqual(closes["RKLB"], "$63.92")
        self.assertIn("closing prices", self.frontier["valuation_snapshot"]["note"].lower())

    def test_renderer_escapes_copy_and_exposes_all_sections(self) -> None:
        self.assertIn("const esc =", self.script)
        self.assertIn("const sectionId =", self.script)
        self.assertIn("const renderAdversarial =", self.script)
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

    def test_geo_themes_follow_ledger_rules(self) -> None:
        geo = [t for t in self.payload["themes"] if t["category"] == "Geographies"]
        self.assertEqual(len(geo), 7)
        self.assertEqual(len({t["id"] for t in geo}), 7)
        for theme in geo:
            for field in ("owner_belief", "conviction", "final_verdict"):
                self.assertTrue(theme[field], theme["id"])
            scores = theme["consensus_scores"]
            for value in scores.values():
                self.assertTrue(isinstance(value, int) and 0 <= value <= 100, theme["id"])
            # single-reviewer themes: consensus must equal the identified review, never invented
            reviews = theme["model_reviews"]
            self.assertEqual(len(reviews), 1, theme["id"])
            self.assertEqual(reviews[0]["knowledge_saturation"], scores["knowledge_saturation"], theme["id"])
            self.assertEqual(reviews[0]["price_saturation"], scores["price_saturation"], theme["id"])
            self.assertIn("single reviewer", theme["status"], theme["id"])
            # renderer accesses every section unconditionally
            for field in ("layer_scorecard", "adversarial_review", "what_survived",
                          "residual_edge", "research_priority", "falsifiers",
                          "watch_next", "sources"):
                self.assertTrue(theme[field], f'{theme["id"]}.{field}')
            self.assertTrue(theme["valuation_snapshot"]["rows"], theme["id"])
            for row in theme["layer_scorecard"]:
                self.assertTrue(0 <= row["knowledge_saturation"] <= 100, theme["id"])
                self.assertTrue(0 <= row["price_saturation"] <= 100, theme["id"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
