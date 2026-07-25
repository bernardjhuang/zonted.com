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
CORE = ROOT / "scripts" / "trading_risk_core.py"

spec = importlib.util.spec_from_file_location("generate_trading_risk", GENERATOR)
if spec is None or spec.loader is None:
    raise RuntimeError("unable to load risk generator")
risk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(risk)

core_spec = importlib.util.spec_from_file_location("trading_risk_core", CORE)
if core_spec is None or core_spec.loader is None:
    raise RuntimeError("unable to load risk core")
core = importlib.util.module_from_spec(core_spec)
core_spec.loader.exec_module(core)


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

    def test_trailing_percentile_excludes_current_observation(self):
        values = list(range(1, 253)) + [10_000]
        result = core.trailing_percentiles(values, window=756, minimum=252)
        self.assertIsNone(result[251])
        self.assertEqual(result[252], 100.0)

    def test_staleness_uses_reference_sessions_not_calendar_days(self):
        sessions = ["2026-07-17", "2026-07-20", "2026-07-21", "2026-07-22", "2026-07-23", "2026-07-24"]
        self.assertEqual(core.session_age("2026-07-22", "2026-07-24", sessions), 2)
        self.assertFalse(core.is_stale("2026-07-22", "2026-07-24", sessions, maximum_age=2))
        self.assertTrue(core.is_stale("2026-07-21", "2026-07-24", sessions, maximum_age=2))

    def test_credit_observations_are_available_next_session(self):
        rows = [{"date": "2026-07-20", "value": 3.0}, {"date": "2026-07-21", "value": 3.1}]
        sessions = ["2026-07-20", "2026-07-21", "2026-07-22"]
        self.assertEqual(core.lag_to_next_session(rows, sessions), [
            {"date": "2026-07-21", "observation_date": "2026-07-20", "value": 3.0},
            {"date": "2026-07-22", "observation_date": "2026-07-21", "value": 3.1},
        ])

    def test_constant_maturity_interpolation(self):
        contracts = [
            {"days": 20, "value": 18.0},
            {"days": 50, "value": 21.0},
            {"days": 80, "value": 24.0},
        ]
        curve = core.constant_maturity_curve(contracts)
        self.assertAlmostEqual(curve["cm30"], 19.0)
        self.assertAlmostEqual(curve["cm60"], 22.0)
        self.assertAlmostEqual(curve["slope_percent"], (22.0 / 19.0 - 1) * 100, places=4)

    def test_score_normalizes_active_components_and_zeroes_stale(self):
        metrics = {
            "vvix": {"risk_percentile": 90.0, "stale": False},
            "curve": {"risk_percentile": 70.0, "stale": False},
            "move": {"risk_percentile": 99.0, "stale": True},
            "skew": {"risk_percentile": 20.0, "stale": False},
            "hy_oas": {"risk_percentile": 90.0, "stale": False},
        }
        score = core.conditions_score(metrics)
        self.assertEqual(score["components"]["move"]["points"], 0)
        self.assertFalse(score["components"]["move"]["active"])
        self.assertEqual(score["active_maximum"], 85)
        self.assertEqual(score["total"], 73.53)

    def test_forward_targets_use_future_sessions_only(self):
        vix = [20.0, 24.0, 26.0, 22.0]
        spy = [100.0, 99.0, 94.0, 96.0]
        target = core.forward_targets(vix, spy, index=0, horizon=3)
        self.assertTrue(target["vix_above_25"])
        self.assertTrue(target["spy_drawdown_5"])
        self.assertAlmostEqual(target["spy_max_drawdown_percent"], -6.0)

    def test_direction_uses_5_and_20_session_changes(self):
        values = [100.0] * 20 + [101.0, 102.0, 103.0, 104.0, 106.0]
        result = core.metric_changes(values)
        self.assertEqual(result["change_5d"], 6.0)
        self.assertEqual(result["direction"], "deteriorating")

    def test_percentile_score_boundaries(self):
        def metrics(percentile):
            return {name: {"risk_percentile": percentile, "stale": False} for name in core.COMPONENT_WEIGHTS}

        self.assertEqual(core.conditions_score(metrics(59.99))["total"], 0)
        self.assertEqual(core.conditions_score(metrics(60))["total"], 50)
        self.assertEqual(core.conditions_score(metrics(85.01))["total"], 100)
        self.assertEqual(core.conditions_score(metrics(70))["label"], "Elevated")

    def test_score_is_sum_of_disclosed_components(self):
        score = self.payload["score"]
        self.assertEqual(score["total"], sum(row["points"] for row in score["components"].values()))
        self.assertEqual(sum(row["maximum"] for row in score["components"].values()), 100)
        self.assertIn(score["label"], {"Contained", "Watchful", "Elevated"})
        self.assertEqual(len(score["rules"]), 5)

    def test_curve_definition_and_snapshot(self):
        current = self.payload["current"]
        self.assertAlmostEqual(current["curve_spread"], current["m2"] - current["m1"], places=4)
        self.assertAlmostEqual(current["curve_slope_percent"], (current["curve_cm60"] / current["curve_cm30"] - 1) * 100, places=3)
        self.assertEqual([row["label"] for row in self.payload["curve"]], ["Spot", "M1", "M2", "M3", "M4", "M5", "M6"])
        self.assertIn("positive slope means contango", self.payload["method"])
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
        self.assertTrue(any("constant-maturity" in line for line in commentary))

    def test_stage_one_history_is_long_and_falsifiable(self):
        self.assertEqual(self.payload["schema_version"], 2)
        history = self.payload["history"]["score"]
        dates = [row["date"] for row in history]
        self.assertGreater(len(history), 2_500)
        self.assertEqual(dates, sorted(set(dates)))
        self.assertLess(self.payload["scorable_start"], "2015-01-01")
        self.assertTrue(self.payload["history"]["vix_spikes"])
        self.assertTrue(all(0 <= row["score"] <= 100 for row in history))

    def test_current_metrics_publish_percentiles_deltas_and_staleness(self):
        metrics = self.payload["current"]["metrics"]
        self.assertEqual(set(metrics), set(core.COMPONENT_WEIGHTS))
        for row in metrics.values():
            self.assertIn("percentile", row)
            self.assertIn("change_5d", row)
            self.assertIn("change_20d", row)
            self.assertIn(row["direction"], {"improving", "stable", "deteriorating", "mixed"})
        self.assertTrue(metrics["move"]["stale"])
        self.assertFalse(self.payload["score"]["components"]["move"]["active"])
        self.assertEqual(self.payload["current"]["hy_oas_available_as_of"], self.payload["as_of"])
        self.assertLess(self.payload["current"]["hy_oas_as_of"], self.payload["current"]["hy_oas_available_as_of"])

    def test_frequency_table_reconciles_to_base_rates(self):
        table = self.payload["conditional_frequencies"]
        self.assertEqual(table["horizons"], [21, 42])
        for horizons in table["targets"].values():
            for horizon in ("21", "42"):
                summary = horizons[horizon]
                self.assertGreater(summary["observations"], 2_500)
                self.assertEqual(summary["events"], sum(row["events"] for row in summary["bands"].values()))
                self.assertEqual(summary["observations"], sum(row["observations"] for row in summary["bands"].values()))
                self.assertGreaterEqual(summary["frequency"], 0)
                self.assertLessEqual(summary["frequency"], 100)

    def test_curve_ratios_and_gate_policy_are_machine_readable(self):
        self.assertTrue(self.payload["series"]["vix9d_vix"])
        self.assertTrue(self.payload["series"]["vix_vix3m"])
        policy = self.payload["gate_policy"]
        self.assertIsInstance(policy["hard_gate_enabled"], bool)
        self.assertIn(policy["elevated_action"], {"gate", "shadow_gate"})
        self.assertEqual(len(policy["evidence"]), 2)
        scanner = self.payload["scanner_policy"]
        self.assertEqual(scanner["stage"], "risk_v2_stage2")
        self.assertEqual(scanner["as_of"], self.payload["as_of"])
        self.assertEqual(scanner["elevated_hard_gate_enabled"], policy["hard_gate_enabled"])
        self.assertEqual(scanner["watchful_action"], "annotate_half_size")
        self.assertEqual(self.payload["model_status"]["status"], "not_evaluated")


if __name__ == "__main__":
    unittest.main()
