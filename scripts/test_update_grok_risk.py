#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("update_grok_risk", ROOT / "scripts" / "update-grok-risk.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def entry(date: str, rating: int) -> dict:
    return {
        "as_of_date": date,
        "session": "post-close",
        "model_id": "grok-4.5",
        "stance": "Neutral",
        "risk_appetite": rating,
        "headline": f"Risk rating {rating}",
        "journal": ["Journal."],
        "what_supports_risk": ["Support."],
        "what_holds_it_back": ["Constraint."],
        "what_changes_my_mind": ["Trigger."],
        "methodology": {"name": "Judgment", "explanation": "Subjective."},
        "limitations": ["Not a forecast."],
        "sources": [{"title": "Source", "url": "https://example.com"}],
    }


class GrokRiskRendererTest(unittest.TestCase):
    def test_chart_write_does_not_restore_stale_risk_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp = pathlib.Path(temp)
            data = temp / "grok-risk.json"
            page = temp / "index.html"
            data.write_text(json.dumps({
                "schema_version": 1,
                "model": "Grok 4.5",
                "entries": [entry("2026-08-06", 5), entry("2026-08-05", 6)],
                "market": {
                    "updated": "2026-08-06",
                    "closes": {
                        "SPY": [["2026-08-05", 100], ["2026-08-06", 99]],
                        "QQQ": [["2026-08-05", 100], ["2026-08-06", 98]],
                    },
                },
            }))
            page.write_text(
                f"<html><body>{MODULE.CHART_START}\nold chart\n{MODULE.CHART_END}\n"
                f"{MODULE.START}\n<div data-model=\"Grok 4.5\" data-rating=\"6\">stale</div>\n"
                f"{MODULE.END}</body></html>"
            )
            old_data, old_page = getattr(MODULE, "DATA"), getattr(MODULE, "PAGE")
            setattr(MODULE, "DATA", data)
            setattr(MODULE, "PAGE", page)
            try:
                self.assertEqual(getattr(MODULE, "main")(), 0)
            finally:
                setattr(MODULE, "DATA", old_data)
                setattr(MODULE, "PAGE", old_page)

            rendered = page.read_text()
            self.assertIn('data-model="Grok 4.5" data-rating="5" data-stance="Neutral"', rendered)
            self.assertIn("2026-08-06 · Neutral (5/10)", rendered)
            self.assertNotIn('data-rating="6">stale', rendered)
            self.assertIn("Rating vs the tape", rendered)


if __name__ == "__main__":
    unittest.main()
