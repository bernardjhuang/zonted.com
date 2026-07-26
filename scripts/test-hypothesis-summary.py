#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build-hypothesis-summary.py"
SPEC = importlib.util.spec_from_file_location("hypothesis_summary", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load {SCRIPT}")
summary = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = summary
SPEC.loader.exec_module(summary)


class HypothesisSummaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.page = (ROOT / "trading" / "hypotheses" / "index.html").read_text()
        self.config = json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())
        self.charts = json.loads((ROOT / "trading" / "hypothesis-charts.json").read_text())

    def test_summary_is_generated_for_every_hypothesis(self) -> None:
        symbols = summary.extract_hypothesis_symbols(self.page)
        self.assertEqual(symbols, list(self.config["rows"]))
        self.assertEqual(set(symbols), set(self.charts["charts"]))
        self.assertEqual(self.page.count('data-hypothesis-summary-row="'), len(symbols))
        self.assertIn("<!-- AUTO:HYPOTHESIS_SUMMARY:START -->", self.page)
        self.assertIn("<!-- AUTO:HYPOTHESIS_SUMMARY:END -->", self.page)
        for symbol in symbols:
            self.assertIn(f'data-hypothesis-summary-row="{symbol}"', self.page)
            self.assertIn(f'href="#hypothesis-{symbol.lower()}-setup"', self.page)

    def test_every_row_has_two_year_chart_metrics_and_three_case_levels(self) -> None:
        symbols = list(self.config["rows"])
        for case in ("bear", "base", "bull"):
            self.assertEqual(
                self.page.count(f'class="entry-line entry-line--{case}"'),
                len(symbols),
                case,
            )
        for symbol, row in self.config["rows"].items():
            self.assertGreaterEqual(len(row["valuation_metrics"]), 2, symbol)
            self.assertEqual(set(row["entry_levels"]), {"bear", "base", "bull"}, symbol)
            self.assertTrue(all(float(value) > 0 for value in row["entry_levels"].values()), symbol)
            chart = self.charts["charts"][symbol]
            self.assertGreaterEqual(len(chart["dates"]), 80, symbol)
            self.assertEqual(len(chart["dates"]), len(chart["close"]), symbol)
            self.assertLess(chart["dates"][0], chart["dates"][-1], symbol)
            for case, value in row["entry_levels"].items():
                self.assertIn(
                    f'data-entry-level="{case}" data-entry-price="{float(value):.2f}"',
                    self.page,
                    symbol,
                )

    def test_confidence_labels_are_explained(self) -> None:
        self.assertIn("Medium confidence means", self.page)
        self.assertIn("Low confidence means", self.page)
        self.assertIn("Confidence measures model reliability—not expected upside", self.page)

    def test_summary_stylesheet_version_is_unique(self) -> None:
        self.assertEqual(self.page.count("/trading/hypothesis-summary.css?v=3"), 1)
        self.assertEqual(self.page.count("/trading/hypothesis-summary.css?v="), 1)

    def test_checked_in_page_matches_renderer(self) -> None:
        rendered = summary.render_page(self.page, self.config, self.charts)
        self.assertEqual(rendered, self.page)
        block = re.search(
            r"<!-- AUTO:HYPOTHESIS_SUMMARY:START -->(.*?)<!-- AUTO:HYPOTHESIS_SUMMARY:END -->",
            self.page,
            re.S,
        )
        self.assertIsNotNone(block)
        body = block.group(1) if block else ""
        self.assertIn("2-year stock chart", body)
        self.assertIn("Bear", body)
        self.assertIn("Base", body)
        self.assertIn("Bull", body)
        self.assertIn("Valuation", body)


if __name__ == "__main__":
    unittest.main()
