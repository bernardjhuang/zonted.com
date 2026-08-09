#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import re
import sys
import unittest
from unittest import mock

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
        self.page = (ROOT / "trading" / "hypothesis-source.txt").read_text()
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
            self.assertIn(f'data-hypothesis-chart-open="{symbol}"', self.page)

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
            self.assertGreaterEqual(len(chart["dates"]), summary.MIN_CHART_POINTS, symbol)
            self.assertEqual(len(chart["dates"]), len(chart["close"]), symbol)
            self.assertLess(chart["dates"][0], chart["dates"][-1], symbol)
            self.assertTrue(-5 < float(chart["beta_2y_weekly_vs_spy"]) < 30, symbol)
            self.assertGreaterEqual(int(chart["beta_observations"]), summary.MIN_BETA_OBSERVATIONS, symbol)
            self.assertIn(
                f'data-label="Beta vs SPY" title="Beta using {chart["beta_observations"]} aligned weekly adjusted-close returns versus SPY">{float(chart["beta_2y_weekly_vs_spy"]):.2f}</td>',
                self.page,
                symbol,
            )
            for case, value in row["entry_levels"].items():
                self.assertIn(
                    f'data-entry-level="{case}" data-entry-price="{float(value):.2f}"',
                    self.page,
                    symbol,
                )

    def test_beta_calculation_matches_linear_weekly_returns(self) -> None:
        dates = [
            (summary.dt.date(2025, 1, 3) + summary.dt.timedelta(days=7 * index)).isoformat()
            for index in range(60)
        ]
        benchmark_close = [100.0]
        asset_close = [100.0]
        for index in range(1, len(dates)):
            market_return = 0.01 if index % 2 else -0.005
            benchmark_close.append(benchmark_close[-1] * (1 + market_return))
            asset_close.append(asset_close[-1] * (1 + 2 * market_return))
        beta, observations = summary.beta_against_benchmark(
            {"dates": dates, "close": asset_close},
            {"dates": dates, "close": benchmark_close},
        )
        self.assertEqual(beta, 2.0)
        self.assertEqual(observations, 59)

    def test_unchanged_chart_refresh_preserves_generation_stamp(self) -> None:
        symbols = list(self.charts["charts"])

        def fetch(symbol: str) -> dict:
            if symbol == "SPY":
                raise RuntimeError("benchmark deliberately unavailable")
            return json.loads(json.dumps(self.charts["charts"][symbol]))

        with mock.patch.object(summary, "fetch_chart", side_effect=fetch):
            refreshed = summary.refresh_charts(symbols, self.charts)
        self.assertEqual(refreshed, self.charts)

    def test_confidence_labels_are_explained(self) -> None:
        self.assertIn("Medium confidence means", self.page)
        self.assertIn("Low confidence means", self.page)
        self.assertIn("Confidence measures model reliability—not expected upside", self.page)
        self.assertIn("Trading-reference rows are explicitly not intrinsic values", self.page)
        self.assertNotIn("bear / base / bull intrinsic entry levels", self.page)
        symbol = "LTH"
        display = self.config["rows"][symbol]["entry_level_display"]
        self.assertEqual(display["heading"], "Trading reference levels")
        self.assertEqual(display["labels"]["base"], "Cost basis")
        self.assertIn("not intrinsic value", self.config["rows"][symbol]["method"])
        self.assertNotIn("PG", self.config["rows"])
        self.assertIn("PL", self.config["rows"])
        self.assertIn('id="hypothesis-pl-setup"', self.page)
        self.assertIn('id="hypothesis-pl-setup" aria-labelledby="hypothesis-pl-title"', self.page)
        self.assertRegex(self.page, r'id="hypothesis-pl-setup"[^>]+data-desk-stance="open-position"')

    def test_summary_stylesheet_asset_is_unique(self) -> None:
        self.assertEqual(self.page.count(summary.CSS_HREF), 1)
        self.assertEqual(self.page.count("/trading/hypothesis-summary"), 1)
        for href, suffix in ((summary.CSS_HREF, ".css"), (summary.MODAL_SCRIPT_HREF, ".js")):
            asset = ROOT / href.removeprefix("/")
            payload = asset.read_bytes()
            digest = hashlib.sha1(f"blob {len(payload)}\0".encode() + payload).hexdigest()[:8]
            self.assertIn(f".{digest}{suffix}", href)

    def test_chart_modal_uses_watchlist_assets_and_sector_pairs(self) -> None:
        symbols = summary.extract_hypothesis_symbols(self.page)
        self.assertEqual(self.page.count('class="hyp-summary-chart-launch"'), len(symbols))
        self.assertEqual(self.page.count('id="hypothesis-chart-dialog"'), 1)
        self.assertEqual(self.page.count(summary.MODAL_SCRIPT_HREF), 1)
        match = re.search(r'<script type="application/json" id="scan-chart-config">(.*?)</script>', self.page)
        self.assertIsNotNone(match)
        chart_config = json.loads(match.group(1) if match else "{}")
        self.assertEqual(chart_config["url"], summary.versioned_asset(summary.SCAN_CHARTS))
        self.assertEqual(chart_config["vwap_url"], summary.versioned_asset(summary.VWAP_CHARTS))
        scan_charts = json.loads(summary.SCAN_CHARTS.read_text())["charts"]
        sector_charts = json.loads(summary.VWAP_CHARTS.read_text())["charts"]
        missing = {symbol for symbol in symbols if symbol not in scan_charts}
        self.assertFalse(missing)
        for symbol in set(symbols) - missing:
            self.assertIn(scan_charts[symbol]["sector_etf"], sector_charts, symbol)

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
        self.assertEqual(body.count('class="hyp-summary-beta"'), len(self.config["rows"]))
        self.assertNotIn("hyp-summary-chart-meta", body)
        self.assertIn('<th class="num">Beta vs SPY</th><th>Valuation</th>', body)
        self.assertIn("Beta uses up to two years of weekly adjusted-close returns versus SPY", body)

    def test_net_dcf_receipt_matches_the_public_levels(self) -> None:
        retired = {"HPQ", "JBS", "NTDOY"}
        self.assertFalse(retired & set(self.config["rows"]))
        self.assertTrue(all(f'hypothesis-{symbol.lower()}-setup' not in self.page for symbol in retired))

        receipt_path = ROOT / "trading" / "research" / "net-dcf-2026-07-29.json"
        workbook_path = receipt_path.with_suffix(".xlsx")
        receipt = json.loads(receipt_path.read_text())
        levels = self.config["rows"]["NET"]["entry_levels"]
        self.assertEqual(receipt["symbol"], "NET")
        self.assertEqual(receipt["valuation_date"], "2026-07-29")
        self.assertEqual(
            levels,
            {
                case: round(receipt["scenarios"][case]["fair_value_per_share"], 2)
                for case in ("bear", "base", "bull")
            },
        )
        self.assertGreater(receipt["reverse_dcf_growth"]["constant_revenue_growth_2027_2035"], 0.40)
        self.assertIn("net-dcf-2026-07-29.xlsx", self.page)
        self.assertGreater(workbook_path.stat().st_size, 10_000)

    def test_new_valuation_receipts_match_public_levels(self) -> None:
        specs = {
            "MU": ("mu-normalized-earnings-2026-08-07.json", {"bear": 300.0, "base": 700.0, "bull": 1280.0}),
            "ZS": ("zs-dcf-2026-08-07.json", {"bear": 75.18, "base": 150.96, "bull": 275.22}),
            "SIEGY": ("siegy-normalized-earnings-2026-08-07.json", {"bear": 93.43, "base": 152.26, "bull": 224.93}),
        }
        for symbol, (filename, expected) in specs.items():
            receipt_path = ROOT / "trading" / "research" / filename
            receipt = json.loads(receipt_path.read_text())
            levels = self.config["rows"][symbol]["entry_levels"]
            actual = {
                case: round(receipt["scenarios"][case]["fair_value_per_share"], 2)
                for case in ("bear", "base", "bull")
            }
            self.assertEqual(receipt["symbol"], symbol)
            self.assertEqual(receipt["valuation_date"], "2026-08-07")
            self.assertEqual(levels, expected)
            self.assertEqual(actual, expected)
            self.assertIn(filename.replace(".json", ".xlsx"), self.page)
            self.assertGreater(receipt_path.with_suffix(".xlsx").stat().st_size, 10_000)

        self.assertGreater(self.config["rows"]["MU"]["entry_levels"]["bull"], 1000)
        self.assertGreater(self.config["rows"]["ZS"]["entry_levels"]["base"], 100)
        self.assertGreater(
            json.loads((ROOT / "trading" / "research" / specs["ZS"][0]).read_text())["reverse_dcf_growth"]["constant_revenue_growth_2027_2035"],
            0.15,
        )

if __name__ == "__main__":
    unittest.main()
