#!/usr/bin/env python3
"""Unit tests for the momentum scanner's Risk v2 decision overlay."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("update-trading-scan.py")
SPEC = importlib.util.spec_from_file_location("update_trading_scan", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
scan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scan)


class ScannerRiskPolicyTest(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"symbol": "AAA", "verdict": "ENTER+", "short_verdict": None},
            {"symbol": "BBB", "verdict": "ENTER", "short_verdict": None},
            {"symbol": "CCC", "verdict": "AVOID", "short_verdict": "SHORT+"},
            {"symbol": "DDD", "verdict": "WATCH", "short_verdict": None},
        ]

    def risk(self, label="Contained", *, fresh=True, hard=False):
        return {
            "source": "risk-ytd.json",
            "source_digest": "abc123",
            "as_of": "2026-07-24" if fresh else "2026-07-23",
            "label": label,
            "score": 50.0 if label == "Elevated" else 35.0 if label == "Watchful" else 10.0,
            "fresh": fresh,
            "policy": {
                "watchful_action": "annotate_half_size",
                "elevated_action": "gate" if hard else "shadow_log",
                "elevated_hard_gate_enabled": hard,
                "stage1_bands_separate_from_unconditional_base_rate": hard,
            },
        }

    def test_contained_leaves_every_signal_unchanged(self):
        rows, counts = scan.apply_risk_policy(self.rows, self.risk())
        self.assertEqual([scan.signal(row)[0] for row in rows], ["ENTER+", "ENTER", "SHORT+", "WATCH"])
        self.assertEqual(counts["none"], 4)
        self.assertEqual([row["verdict"] for row in rows], [row["verdict"] for row in self.rows])

    def test_watchful_annotates_only_qualified_longs(self):
        rows, counts = scan.apply_risk_policy(self.rows, self.risk("Watchful"))
        self.assertEqual(counts["annotate_watchful"], 2)
        self.assertEqual([row["risk_decision"]["action"] for row in rows], ["annotate_watchful", "annotate_watchful", "none", "none"])
        self.assertEqual([scan.signal(row)[0] for row in rows], ["ENTER+", "ENTER", "SHORT+", "WATCH"])

    def test_elevated_hard_gate_changes_only_public_long_verdicts(self):
        rows, counts = scan.apply_risk_policy(self.rows, self.risk("Elevated", hard=True))
        self.assertEqual(counts["gated_elevated"], 2)
        self.assertEqual([scan.signal(row)[0] for row in rows], ["WATCH", "WATCH", "SHORT+", "WATCH"])
        self.assertEqual([row["verdict"] for row in rows[:2]], ["ENTER+", "ENTER"])
        self.assertTrue(all(row["risk_decision"]["hard_gate"] for row in rows[:2]))
        self.assertEqual(rows[2]["risk_decision"]["action"], "none")

    def test_elevated_without_evidence_is_shadow_only(self):
        rows, counts = scan.apply_risk_policy(self.rows, self.risk("Elevated", hard=False))
        self.assertEqual(counts["shadow_elevated"], 2)
        self.assertEqual([scan.signal(row)[0] for row in rows], ["ENTER+", "ENTER", "SHORT+", "WATCH"])
        self.assertTrue(all(row["risk_decision"]["would_gate"] for row in rows[:2]))
        self.assertTrue(all(not row["risk_decision"]["hard_gate"] for row in rows[:2]))

    def test_stale_risk_can_never_gate(self):
        rows, counts = scan.apply_risk_policy(self.rows, self.risk("Elevated", fresh=False, hard=True))
        self.assertEqual(counts["stale_risk_shadow"], 2)
        self.assertEqual([scan.signal(row)[0] for row in rows], ["ENTER+", "ENTER", "SHORT+", "WATCH"])

    def test_loader_requires_same_session_unless_backfill_is_explicit(self):
        payload = {
            "schema_version": 2,
            "as_of": "2026-07-23",
            "score": {"label": "Elevated", "total": 60},
            "scanner_policy": {
                "schema_version": 1,
                "stage": "risk_v2_stage2",
                "as_of": "2026-07-23",
                "watchful_action": "annotate_half_size",
                "elevated_action": "gate",
                "elevated_hard_gate_enabled": True,
                "stage1_bands_separate_from_unconditional_base_rate": True,
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "risk.json"
            path.write_text(json.dumps(payload))
            with self.assertRaisesRegex(ValueError, "must match scan session"):
                scan.load_risk_context(path, "2026-07-24")
            context = scan.load_risk_context(path, "2026-07-24", allow_stale=True)
        self.assertFalse(context["fresh"])
        self.assertFalse(context["policy"]["elevated_hard_gate_enabled"])
        self.assertEqual(context["source"], "risk.json")


if __name__ == "__main__":
    unittest.main()
