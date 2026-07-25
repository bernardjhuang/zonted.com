#!/usr/bin/env python3
"""Regression tests for Risk v2's persistence gauntlet."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest

SCRIPT = Path(__file__).with_name("evaluate-trading-risk.py")
SPEC = importlib.util.spec_from_file_location("evaluate_trading_risk", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
evaluate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(evaluate)
ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "trading" / "risk-evaluation.json"


class RiskEvaluationTest(unittest.TestCase):
    def test_first_hit_excludes_today_and_respects_horizon(self):
        sessions = [f"2026-01-{day:02d}" for day in range(1, 7)]
        vix = [30, 20, 26, 20, 20, 20]
        spy = [100, 100, 100, 94, 100, 100]
        self.assertEqual(evaluate.first_hit(vix, spy, sessions, index=0, horizon=2, target="vix_above_25"), sessions[2])
        self.assertIsNone(evaluate.first_hit(vix, spy, sessions, index=1, horizon=1, target="spy_drawdown_5"))
        self.assertEqual(evaluate.first_hit(vix, spy, sessions, index=1, horizon=2, target="spy_drawdown_5"), sessions[3])

    def test_positive_hits_cluster_and_calm_blocks_do_not_overlap(self):
        rows = []
        positives = {1: "2026-01-05", 2: "2026-01-06", 8: "2026-01-20"}
        for index in range(12):
            actual = int(index in positives)
            rows.append({
                "date": f"2026-01-{index + 1:02d}",
                "origin_index": index,
                "event_3d": actual,
                "event_3d_first_hit": positives.get(index),
            })
        blocks = evaluate.assign_blocks(rows, "event_3d", 3)
        self.assertEqual(blocks["2026-01-02"], blocks["2026-01-03"])
        self.assertNotEqual(blocks["2026-01-02"], blocks["2026-01-09"])
        negative_counts = {}
        for row in rows:
            block = blocks[row["date"]]
            if block.startswith("N"):
                negative_counts[block] = negative_counts.get(block, 0) + 1
        self.assertTrue(all(count <= 3 for count in negative_counts.values()))

    def test_feature_registry_is_frozen_and_sparse(self):
        self.assertEqual(len(evaluate.FEATURES), 5)
        self.assertEqual(tuple(row["name"] for row in evaluate.FEATURES), evaluate.FEATURE_NAMES)
        self.assertEqual(len(evaluate.FEATURE_HASH), 64)
        self.assertEqual(evaluate.HORIZONS, (21, 42))
        self.assertEqual(evaluate.TARGETS, ("vix_above_25", "spy_drawdown_5"))

    def test_public_receipt_contract(self):
        self.assertTrue(ARTIFACT.exists(), "run scripts/evaluate-trading-risk.py first")
        payload = json.loads(ARTIFACT.read_text())
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["manifest"]["feature_hash"], evaluate.FEATURE_HASH)
        self.assertEqual(len(payload["scores"]), 4)
        self.assertEqual({(row["target"], row["horizon"]) for row in payload["scores"]}, {
            ("vix_above_25", 21), ("vix_above_25", 42),
            ("spy_drawdown_5", 21), ("spy_drawdown_5", 42),
        })
        self.assertTrue(all(row["observations"] > 1_000 for row in payload["scores"]))
        self.assertTrue(all(row["total_blocks"] >= 20 for row in payload["scores"]))
        self.assertIn(payload["model_status"]["status"], {"shipped", "withheld"})
        if payload["model_status"]["status"] == "withheld":
            self.assertIsNone(payload["model_status"]["live_probabilities"])
            self.assertTrue(payload["model_status"]["reasons"])
        self.assertTrue(payload["oos_predictions"])
        self.assertTrue(all(row["date"] >= evaluate.OOS_START for row in payload["oos_predictions"]))


if __name__ == "__main__":
    unittest.main()
