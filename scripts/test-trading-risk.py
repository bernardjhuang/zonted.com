#!/usr/bin/env python3
"""Contract and arithmetic checks for the generated Forward Risk dashboard."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "trading" / "risk-ytd.json"
GENERATOR = ROOT / "scripts" / "generate-trading-risk.py"

spec = importlib.util.spec_from_file_location("generate_trading_risk", GENERATOR)
if spec is None or spec.loader is None:
    raise RuntimeError("unable to load risk generator")
risk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(risk)


class RiskDataContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads(DATA.read_text())

    def test_official_2026_monthly_expirations(self):
        expected = [
            "2026-01-21", "2026-02-18", "2026-03-18", "2026-04-15",
            "2026-05-19", "2026-06-17", "2026-07-22", "2026-08-19",
            "2026-09-16", "2026-10-21", "2026-11-18", "2026-12-16",
        ]
        actual = [risk.vx_monthly_expiration(2026, month).isoformat() for month in range(1, 13)]
        self.assertEqual(actual, expected)

    def test_score_boundaries(self):
        self.assertEqual(risk.threshold_score(89.99, 0.51, 79.99, 129.99)["total"], 0)
        self.assertEqual(risk.threshold_score(90, 0.5, 80, 130)["total"], 50)
        self.assertEqual(risk.threshold_score(110.01, -0.01, 100.01, 145.01)["total"], 100)
        self.assertEqual(risk.threshold_score(100, 0.75, 70, 150)["label"], "Watchful")

    def test_score_is_sum_of_disclosed_components(self):
        score = self.payload["score"]
        self.assertEqual(score["total"], sum(row["points"] for row in score["components"].values()))
        self.assertEqual(sum(row["maximum"] for row in score["components"].values()), 100)
        self.assertIn(score["label"], {"Contained", "Watchful", "Elevated"})
        self.assertEqual(len(score["rules"]), 5)

    def test_curve_definition_and_snapshot(self):
        current = self.payload["current"]
        self.assertAlmostEqual(current["curve_spread"], current["m2"] - current["m1"], places=4)
        self.assertEqual([row["label"] for row in self.payload["curve"]], ["Spot", "M1", "M2", "M3", "M4", "M5", "M6"])
        self.assertIn("positive values correctly mean contango", self.payload["method"])
        self.assertEqual(current["curve_as_of"], self.payload["as_of"])

    def test_series_are_ordered_unique_and_ytd(self):
        for name, rows in self.payload["series"].items():
            self.assertTrue(rows, name)
            dates = [row["date"] for row in rows]
            self.assertEqual(dates, sorted(set(dates)), name)
            self.assertTrue(all(day.startswith(f"{self.payload['year']}-") for day in dates), name)

    def test_latest_values_have_source_dates(self):
        current = self.payload["current"]
        self.assertEqual(set(current["dates"]), {"vix", "vvix", "move", "skew"})
        for name in current["dates"]:
            self.assertEqual(current["dates"][name], self.payload["series"][name][-1]["date"])
            self.assertEqual(current[name], self.payload["series"][name][-1]["value"])
        self.assertIsNotNone(current["hy_oas"])
        self.assertEqual(current["hy_oas_as_of"], self.payload["series"]["hy_oas"][-1]["date"])

    def test_commentary_is_plain_english_and_caveated(self):
        commentary = self.payload["commentary"]
        self.assertGreaterEqual(len(commentary), 3)
        self.assertLessEqual(len(commentary), 5)
        self.assertIn("not a forecast", commentary[0])
        self.assertTrue(any("M2−M1" in line for line in commentary))


if __name__ == "__main__":
    unittest.main()
