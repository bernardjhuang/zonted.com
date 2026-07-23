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

    def test_eight_answer_first_tabs(self):
        tabs = re.findall(r'<button class="trading-tab" id="([^"]+)-tab"[^>]*>(.*?)</button>', self.html, re.S)
        self.assertEqual([name for name, _ in tabs], ["positions", "hypotheses", "brief", "scan", "vwap", "congress", "whales", "crypto"])
        labels = [" ".join(re.sub(r"<[^>]+>", "", body).split()) for _, body in tabs]
        self.assertEqual(labels[0], "Portfolio")
        self.assertRegex(labels[1], r"^Hypotheses \d+$")
        self.assertEqual(labels[2], "Brief")
        self.assertRegex(labels[3], r"^Momentum \d+$")
        self.assertEqual(labels[4:], ["VWAP", "Congress", "13F", "Crypto"])
        self.assertNotIn('id="log-tab"', self.html)

    def test_heading_and_scoped_controls(self):
        self.assertEqual(len(re.findall(r"<h1\b", self.html)), 1)
        self.assertIn('<h1 class="bl-title">Trading</h1>', self.html)
        self.assertIn('id="bl-tools"', self.html)
        self.assertIn('Download positions CSV', self.html)
        self.assertRegex(self.js, r"tools\.hidden\s*=\s*target\.id\s*!==\s*'positions-panel'")
        self.assertNotIn('id="bl-filters"', self.html)
        self.assertNotIn("positive mark", self.js)

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
        self.assertIn('Short setups ·', self.html)
        self.assertIn('class="scan-qualified-links"', self.html)
        self.assertIn('id="scan-universe"', self.html)
        self.assertIn('<details class="scan-universe-disclosure" id="scan-universe" open>', self.html)
        self.assertIn('<details open><summary>All sectors · 50-day Z-score</summary>', self.html)
        self.assertEqual(self.html.count('class="scan-sector-head"'), 11)
        self.assertEqual(self.html.count('class="scan-sector-score"'), 11)
        self.assertIn('data-universe-sort-day', self.js)
        self.assertIn('let universeSortDir = -1;', self.js)
        self.assertIn('if (universe.open) loadUniverse();', self.js)
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
        self.assertEqual(len(vwap["groups"]["us"]), 12)
        self.assertEqual(len(vwap["groups"]["countries"]), 10)
        self.assertTrue(all("z50" in vwap["charts"][symbol] for symbol in vwap["groups"]["countries"]))
        self.assertIn(crypto["default"], crypto["charts"])

    def test_vwap_shows_every_chart_without_picker_controls(self):
        self.assertIn('id="vwap-chart-grid"', self.html)
        self.assertIn('id="vwap-country-chart-grid"', self.html)
        self.assertIn('id="vwap-us-heading">US market + sectors', self.html)
        self.assertIn('id="vwap-countries-heading">Country markets', self.html)
        self.assertLess(self.html.index('id="vwap-chart-grid"'), self.html.index('id="vwap-countries-heading"'))
        self.assertIn('data-url="/trading/vwap-charts.json?', self.html)
        self.assertEqual(self.html.count('>50D Z</th>'), 2)
        self.assertNotIn('id="vwap-selected-chart"', self.html)
        self.assertNotIn('data-vwap-select', self.html)
        self.assertNotIn('data-vwap-scope-button', self.html)
        self.assertNotIn('data-vwap-scope="countries" hidden', self.html)
        self.assertIn("initChartGallery('#vwap-chart-grid'", self.js)
        self.assertIn("initChartGallery('#vwap-country-chart-grid'", self.js)
        self.assertNotIn("initChartPicker('#vwap-selected-chart'", self.js)

    def test_crypto_shows_every_chart_without_picker_controls(self):
        self.assertIn('id="crypto-chart-grid"', self.html)
        self.assertIn('data-url="/trading/crypto-charts.json?', self.html)
        self.assertNotIn('id="crypto-selected-chart"', self.html)
        self.assertNotIn('data-crypto-select', self.html)
        self.assertIn('>Spread Z vs BTC</th>', self.html)
        self.assertIn("initChartGallery('#crypto-chart-grid'", self.js)

    def test_live_setups_open_and_recent_activity_folded(self):
        self.assertIn('aria-expanded="true" aria-controls="${detailId}"', self.js)
        self.assertIn('>Hide setup</button>', self.js)
        self.assertIn("renderSetupChartForSymbol($('[data-position-chart-shell]', detail)", self.js)
        self.assertIn('.slice(0, 20)', self.js)
        self.assertIn('<details class="bl-card activity-disclosure">', self.js)
        self.assertIn('direction / type / P&amp;L', self.js)
        self.assertEqual(self.html.count('class="activity-row"'), 40)

    def test_13f_consensus_generates_top_twenty_per_side(self):
        generator = (ROOT / "scripts" / "update-trading-whales.py").read_text()
        self.assertIn("p['top_bought'][:20]", generator)
        self.assertIn("p['top_sold'][:20]", generator)
        self.assertIn("Most bought across offices · top 20", generator)
        self.assertIn("Most sold across offices · top 20", generator)
        whales_match = re.search(r'<!-- AUTO:WHALES:START -->(.*?)<!-- AUTO:WHALES:END -->', self.html, re.S)
        self.assertIsNotNone(whales_match)
        whales = whales_match.group(1) if whales_match else ""
        for label in ("Most bought across offices · top 20", "Most sold across offices · top 20"):
            body = re.search(re.escape(label) + r".*?<tbody>(.*?)</tbody>", whales, re.S)
            self.assertIsNotNone(body, label)
            rows = body.group(1) if body else ""
            self.assertEqual(rows.count("<tr>"), 20, label)


if __name__ == "__main__":
    unittest.main(verbosity=2)
