#!/usr/bin/env python3
"""Regression checks for the generated /trading decision surface."""
from __future__ import annotations

import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "trading" / "index.html"
JS = ROOT / "js" / "trading-broker-light.js"


class TradingUiContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text()
        cls.js = JS.read_text()

    def test_six_answer_first_tabs(self):
        tabs = re.findall(r'<button class="trading-tab" id="([^"]+)-tab"[^>]*>(.*?)</button>', self.html, re.S)
        self.assertEqual([name for name, _ in tabs], ["positions", "scan", "vwap", "congress", "whales", "crypto"])
        labels = [" ".join(re.sub(r"<[^>]+>", "", body).split()) for _, body in tabs]
        self.assertEqual(labels[0], "Portfolio")
        self.assertRegex(labels[1], r"^Momentum \d+$")
        self.assertEqual(labels[2:], ["VWAP", "Congress", "13F", "Crypto"])
        self.assertNotIn('id="log-tab"', self.html)

    def test_heading_and_scoped_controls(self):
        self.assertEqual(len(re.findall(r"<h1\b", self.html)), 1)
        self.assertIn('<h1 class="bl-title">Trading</h1>', self.html)
        self.assertIn('id="bl-tools"', self.html)
        self.assertIn('Download positions CSV', self.html)
        self.assertRegex(self.js, r"tools\.hidden\s*=\s*target\.id\s*!==\s*'positions-panel'")

    def test_legacy_deep_links_survive(self):
        self.assertIn("'#watchlist': '#scan'", self.js)
        self.assertIn("'#log': ''", self.js)

    def test_answer_first_and_progressive_disclosure(self):
        for panel in ("scan", "vwap", "congress", "whales", "crypto"):
            match = re.search(
                rf'<!-- AUTO:{panel.upper()}:START -->(.*?)<!-- AUTO:{panel.upper()}:END -->',
                self.html,
                re.S,
            )
            self.assertIsNotNone(match, panel)
            block = match.group(1) if match else ""
            self.assertIn('class="trading-takeaway"', block, panel)
            self.assertIn('<details class="trading-method"', block, panel)
        self.assertIn('No qualified shorts today.', self.html)
        self.assertIn('id="scan-universe"', self.html)
        self.assertNotIn('aria-label="Full momentum scan of the tracked universe"', self.html)

    def test_chart_payloads_are_external_and_small_shell(self):
        self.assertLess(PAGE.stat().st_size, 200_000)
        self.assertNotIn("data-d='", self.html)
        self.assertLess(len(re.findall(r"<svg\b", self.html)), 5)
        for name in ("scan-universe.json", "vwap-charts.json", "crypto-charts.json"):
            path = ROOT / "trading" / name
            self.assertTrue(path.exists(), name)
            payload = json.loads(path.read_text())
            self.assertTrue(payload, name)

    def test_signal_vocabulary_is_preserved(self):
        universe = json.loads((ROOT / "trading" / "scan-universe.json").read_text())
        labels = {row["signal"] for row in universe["rows"]}
        self.assertIn("ENTER+", labels)
        self.assertTrue(labels <= {"ENTER+", "ENTER", "WATCH", "AVOID", "NO DATA", "SHORT+", "SHORT", "BREAKING"})
        self.assertIn("<b>ENTER+</b> = qualified", self.html)

    def test_generated_asset_contracts(self):
        vwap = json.loads((ROOT / "trading" / "vwap-charts.json").read_text())
        crypto = json.loads((ROOT / "trading" / "crypto-charts.json").read_text())
        self.assertEqual(len(vwap["charts"]), 22)
        self.assertEqual(len(crypto["charts"]), 7)
        self.assertEqual(vwap["default"], "SPY")
        self.assertIn(crypto["default"], crypto["charts"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
