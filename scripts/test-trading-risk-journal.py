#!/usr/bin/env python3
from __future__ import annotations

import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = ROOT / "trading" / "risk-journal.json"


class RiskJournalContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.payload = json.loads(DATA.read_text())

    def test_schema_and_subjective_method_are_explicit(self) -> None:
        self.assertEqual(self.payload["schema_version"], 1)
        self.assertEqual(self.payload["author"], "GPT-5.6")
        self.assertIn("subjective", self.payload["methodology"].lower())

    def test_entries_are_unique_and_newest_first(self) -> None:
        entries = self.payload["entries"]
        self.assertGreaterEqual(len(entries), 1)
        dates = [row["date"] for row in entries]
        self.assertEqual(dates, sorted(dates, reverse=True))
        self.assertEqual(len(dates), len(set(dates)))
        self.assertEqual(dates[0], "2026-07-30")
        self.assertIn("2026-07-27", dates)

    def test_each_entry_is_an_honest_journal_read(self) -> None:
        required_lists = (
            "journal",
            "what_supports_risk",
            "what_holds_it_back",
            "what_changes_my_mind",
        )
        for entry in self.payload["entries"]:
            self.assertEqual(entry["author"], "GPT-5.6")
            self.assertIn(entry["stance"], {"Risk-on", "Neutral", "Risk-off"})
            self.assertGreaterEqual(entry["risk_appetite"], 1)
            self.assertLessEqual(entry["risk_appetite"], 10)
            self.assertTrue(entry["headline"].strip())
            self.assertTrue(entry["source_note"].strip())
            for key in required_lists:
                self.assertGreaterEqual(len(entry[key]), 1, (entry["date"], key))
                self.assertTrue(all(str(value).strip() for value in entry[key]))

    def test_grok_log_has_current_structured_entry_and_history(self) -> None:
        page = (ROOT / "trading" / "grok-risk" / "index.html").read_text()
        data = json.loads((ROOT / "trading" / "grok-risk.json").read_text())
        latest = data["entries"][0]
        self.assertEqual(latest["as_of_date"], "2026-07-29")
        self.assertEqual(latest["risk_appetite"], 3)
        self.assertIn('data-model="Grok 4.5" data-rating="3" data-stance="Risk-off"', page)
        self.assertIn("2026-07-29 · Risk-off (3/10)", page)
        self.assertIn("2026-07-27 · Risk On (6.5/10)", page)
        self.assertLess(page.index("2026-07-29"), page.index("2026-07-27"))

    def test_metric_dashboard_payload_is_not_reintroduced(self) -> None:
        forbidden = {"series", "curve", "score", "gauges", "components", "model_status"}
        self.assertTrue(forbidden.isdisjoint(self.payload))
        for entry in self.payload["entries"]:
            self.assertTrue(forbidden.isdisjoint(entry))


if __name__ == "__main__":
    unittest.main()
