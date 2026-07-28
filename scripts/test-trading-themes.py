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
        self.assertEqual(len(self.payload["themes"]), 36)
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
        self.assertIn("missing model scores are never invented", self.payload["method"]["consensus"].lower())

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
        self.assertIn("const renderProvenance =", self.script)
        self.assertIn('aria-label="Model provenance"', self.script)
        self.assertIn("theme.source_model", self.script)
        self.assertIn("theme.reviewed_by", self.script)
        self.assertIn(".prov-grok i", self.page)
        self.assertIn(".prov-meta i", self.page)
        self.assertIn("const sortThemesByGapDescending =", self.script)
        self.assertIn("const themes = sortThemesByGapDescending(payload.themes);", self.script)
        self.assertIn("return bGap - aGap;", self.script)
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

    def test_renderer_ships_ledger_dumbbell_and_record_overlay(self) -> None:
        """v2 index: filters + dumbbell gap chart + sortable ledger + record overlay."""
        for token in (
            "const renderDumbbell =",
            "const renderLedger =",
            "const renderControls =",
            "const stageOf =",
            "const openRecord =",
            "const syncFromHash =",
            "data-theme-id",
            "rec-overlay",
            "themes-ledger",
        ):
            self.assertIn(token, self.script)
        for token in (
            ".mi-claude", ".mi-gpt", ".mi-grok", ".mi-gemini", ".mi-meta",
            "model-icons/fable.svg",
            ".rec-panel", ".fpill", ".themes-ledger", ".db-tip",
        ):
            self.assertIn(token, self.page)

    def test_hunt_themes_follow_ledger_rules(self) -> None:
        counts = {"Geographies": 7, "Sectors": 5, "Emerging": 6}
        grok_review_ids = {
            "geo-yen-forcing-chain",
            "sector-click-to-agent-rails",
            "geo-barrels-to-flops",
            "emerging-glp1-actuarial",
            "sector-munitions-energetics",
        }
        new_ids = {
            "geo-eu-traceability-stack",
            "sector-treasury-collateral-tax",
            "sector-medicaid-churn-economy",
            "sector-upper-cband-capex-echo",
            "emerging-pfas-testing-wave",
            "emerging-live-experience-k",
            "emerging-ai-compute-water-geography",
            "emerging-autonomous-science-verification-wall",
            "emerging-orbital-compute-relief-valve",
            "emerging-precision-fermentation-molecules",
            "emerging-radiative-cooling-everything-grid",
            "meta-power-wall-rate-shock",
            "meta-humanoid-labor-wage-shock",
            "meta-partial-reprogramming-humans",
            "meta-silicon-sovereignty-stack-split",
            "meta-y2q-post-quantum-rebuild",
        }
        hunt = [
            t for t in self.payload["themes"]
            if t["category"] in counts and t["id"] not in new_ids
        ]
        for category, expected in counts.items():
            self.assertEqual(sum(1 for t in hunt if t["category"] == category), expected, category)
        self.assertEqual(len({t["id"] for t in hunt}), len(hunt))
        for theme in hunt:
            for field in ("owner_belief", "conviction", "final_verdict"):
                self.assertTrue(theme[field], theme["id"])
            scores = theme["consensus_scores"]
            for value in scores.values():
                self.assertTrue(isinstance(value, int) and 0 <= value <= 100, theme["id"])
            reviews = theme["model_reviews"]
            expected_models = ["Claude Fable 5", "GPT-5.6"]
            if theme["id"] in grok_review_ids:
                expected_models.append("Grok 4.5")
                self.assertEqual(reviews[-1]["role"], "Independent review supplied by Bernard")
                self.assertEqual(
                    (reviews[-1]["knowledge_saturation"], reviews[-1]["price_saturation"]),
                    (scores["knowledge_saturation"], scores["price_saturation"]),
                )
            self.assertEqual([row["model"] for row in reviews], expected_models, theme["id"])
            for field in ("knowledge_saturation", "price_saturation"):
                self.assertEqual(scores[field], int(statistics.median(row[field] for row in reviews)), theme["id"])
            expected_count = "3 reviewers" if theme["id"] in grok_review_ids else "2 reviewers"
            self.assertIn(expected_count, theme["status"], theme["id"])
            # renderer accesses every section unconditionally
            for field in ("layer_scorecard", "adversarial_review", "what_survived",
                          "residual_edge", "research_priority", "falsifiers",
                          "watch_next", "sources"):
                self.assertTrue(theme[field], f'{theme["id"]}.{field}')
            self.assertTrue(theme["valuation_snapshot"]["rows"], theme["id"])
            for row in theme["layer_scorecard"]:
                self.assertTrue(0 <= row["knowledge_saturation"] <= 100, theme["id"])
                self.assertTrue(0 <= row["price_saturation"] <= 100, theme["id"])

        supplied_grok_ids = {
            theme["id"] for theme in self.payload["themes"]
            if any(row["role"] == "Independent review supplied by Bernard" for row in theme["model_reviews"])
        }
        self.assertEqual(supplied_grok_ids, grok_review_ids)
        self.assertIn("Grok 4.5 added to five named reviews supplied by Bernard", self.payload["method"]["consensus"])

    def test_frontier_signal_themes_are_complete_and_independently_scored(self) -> None:
        expected = {
            "emerging-ai-compute-water-geography": (58, 28, 58, 28),
            "emerging-autonomous-science-verification-wall": (52, 22, 58, 22),
            "emerging-orbital-compute-relief-valve": (45, 8, 60, 20),
            "emerging-precision-fermentation-molecules": (65, 35, 70, 52),
            "emerging-radiative-cooling-everything-grid": (60, 25, 60, 34),
        }
        found = {theme["id"]: theme for theme in self.payload["themes"] if theme["id"] in expected}
        self.assertEqual(set(found), set(expected))
        for theme_id, (grok_known, grok_priced, consensus_known, consensus_priced) in expected.items():
            theme = found[theme_id]
            self.assertEqual(theme["category"], "Emerging")
            self.assertEqual(theme["status"], "Frontier signal · 3 reviewers")
            self.assertEqual([row["model"] for row in theme["model_reviews"]],
                             ["Grok 4.5", "GPT-5.6", "Claude Fable 5"])
            self.assertEqual(theme["source_model"], "Grok 4.5")
            self.assertEqual(theme["reviewed_by"], ["GPT-5.6", "Claude Fable 5"])
            self.assertEqual(
                (theme["model_reviews"][0]["knowledge_saturation"], theme["model_reviews"][0]["price_saturation"]),
                (grok_known, grok_priced),
            )
            self.assertEqual(
                (theme["consensus_scores"]["knowledge_saturation"], theme["consensus_scores"]["price_saturation"]),
                (consensus_known, consensus_priced),
            )
            for field in (
                "owner_belief", "conviction", "final_verdict", "layer_scorecard", "adversarial_review",
                "what_survived", "residual_edge", "research_priority", "falsifiers", "watch_next", "sources",
            ):
                self.assertTrue(theme[field], f"{theme_id}.{field}")
            self.assertGreaterEqual(len(theme["layer_scorecard"]), 4)
            self.assertGreaterEqual(len(theme["valuation_snapshot"]["rows"]), 5)
            self.assertEqual(theme["valuation_snapshot"]["date"], self.payload["as_of"])
            self.assertTrue(all(source["url"].startswith("https://") for source in theme["sources"]))

    def test_every_theme_exposes_source_reviewers_and_has_gpt(self) -> None:
        for theme in self.payload["themes"]:
            models = [row["model"] for row in theme["model_reviews"]]
            self.assertIn(theme["source_model"], models, theme["id"])
            self.assertEqual(theme["reviewed_by"], [model for model in models if model != theme["source_model"]], theme["id"])
            self.assertTrue(any(model.startswith("GPT") for model in models), theme["id"])

        live = next(theme for theme in self.payload["themes"] if theme["id"] == "emerging-live-experience-k")
        self.assertEqual([row["model"] for row in live["model_reviews"]], ["Claude Fable 5", "GPT-5.6"])
        self.assertEqual(live["consensus_scores"], {"knowledge_saturation": 68, "price_saturation": 51})
        self.assertEqual(live["status"], "Theme hunt · 2 reviewers")

    def test_meta_frontier_themes_are_complete_and_independently_scored(self) -> None:
        expected = {
            "meta-power-wall-rate-shock": ("Energy", 68, 32, 80, 56),
            "meta-humanoid-labor-wage-shock": ("Emerging", 38, 14, 58, 30),
            "meta-partial-reprogramming-humans": ("Emerging", 24, 8, 36, 14),
            "meta-silicon-sovereignty-stack-split": ("Sectors", 54, 26, 78, 55),
            "meta-y2q-post-quantum-rebuild": ("Emerging", 18, 5, 45, 20),
        }
        found = {theme["id"]: theme for theme in self.payload["themes"] if theme["id"] in expected}
        self.assertEqual(set(found), set(expected))
        for theme_id, (category, meta_known, meta_priced, consensus_known, consensus_priced) in expected.items():
            theme = found[theme_id]
            self.assertEqual(theme["category"], category)
            self.assertEqual(theme["status"], "Meta frontier · 3 reviewers")
            self.assertEqual([row["model"] for row in theme["model_reviews"]],
                             ["Meta AI", "GPT-5.6", "Claude Fable 5"])
            self.assertEqual(theme["source_model"], "Meta AI")
            self.assertEqual(theme["reviewed_by"], ["GPT-5.6", "Claude Fable 5"])
            self.assertEqual(
                (theme["model_reviews"][0]["knowledge_saturation"], theme["model_reviews"][0]["price_saturation"]),
                (meta_known, meta_priced),
            )
            self.assertEqual(
                (theme["consensus_scores"]["knowledge_saturation"], theme["consensus_scores"]["price_saturation"]),
                (consensus_known, consensus_priced),
            )
            for field in (
                "owner_belief", "conviction", "final_verdict", "layer_scorecard", "adversarial_review",
                "what_survived", "residual_edge", "research_priority", "falsifiers", "watch_next", "sources",
            ):
                self.assertTrue(theme[field], f"{theme_id}.{field}")
            self.assertGreaterEqual(len(theme["layer_scorecard"]), 4)
            self.assertGreaterEqual(len(theme["valuation_snapshot"]["rows"]), 6)
            self.assertEqual(theme["valuation_snapshot"]["date"], self.payload["as_of"])
            self.assertTrue(all(source["url"].startswith("https://") for source in theme["sources"]))

        self.assertIn("Meta frontier set", self.payload["method"]["consensus"])

    def test_gpt_origin_second_order_themes_are_complete(self) -> None:
        expected = {
            "geo-eu-traceability-stack": "Geographies",
            "sector-treasury-collateral-tax": "Sectors",
            "sector-medicaid-churn-economy": "Sectors",
            "sector-upper-cband-capex-echo": "Sectors",
            "emerging-pfas-testing-wave": "Emerging",
        }
        found = {theme["id"]: theme for theme in self.payload["themes"] if theme["id"] in expected}
        self.assertEqual(set(found), set(expected))
        self.assertEqual(len({theme["id"] for theme in self.payload["themes"]}), len(self.payload["themes"]))
        for theme_id, category in expected.items():
            theme = found[theme_id]
            self.assertEqual(theme["category"], category)
            self.assertEqual([row["model"] for row in theme["model_reviews"]],
                             ["GPT-5.6", "Claude Fable 5"])
            self.assertEqual(theme["reviewed_by"], ["Claude Fable 5"])
            self.assertIn("2 reviewers", theme["status"])
            for field in (
                "layer_scorecard", "adversarial_review", "what_survived", "residual_edge",
                "research_priority", "falsifiers", "watch_next", "sources",
            ):
                self.assertTrue(theme[field], f"{theme_id}.{field}")
            self.assertGreaterEqual(len(theme["layer_scorecard"]), 4)
            self.assertGreaterEqual(len(theme["valuation_snapshot"]["rows"]), 5)
            self.assertTrue(all(source["url"].startswith("https://") for source in theme["sources"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
