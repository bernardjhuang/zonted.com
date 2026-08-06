#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import pathlib
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "publish-gpt-risk-journal.py"
SPEC = importlib.util.spec_from_file_location("publish_gpt_risk_journal", MODULE_PATH)
assert SPEC and SPEC.loader
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


def response(date: str = "2026-08-05") -> dict:
    return {
        "schema_version": 1,
        "prompt_version": "zonted-independent-risk-v1",
        "decision_status": "publishable",
        "as_of_date": date,
        "session": "post-close",
        "author": "GPT-5.6",
        "model_id": "gpt-5.6-sol",
        "stance": "Neutral",
        "risk_appetite": 5.5,
        "score_interpretation": "Five is balanced; 5.5 is a mild risk-on lean.",
        "confidence": "Medium",
        "headline": "Balanced tape with incomplete confirmation.",
        "methodology": {
            "name": "Cross-asset close",
            "explanation": "Compare completed-session equity, credit, rates, and volatility evidence.",
            "selected_signals": ["SPY", "HYG", "VIX"],
        },
        "journal": ["Observation.", "Contradiction.", "Bottom line."],
        "what_supports_risk": ["Support one.", "Support two.", "Support three."],
        "what_holds_it_back": ["Risk one.", "Risk two.", "Risk three."],
        "what_changes_my_mind": ["Upgrade condition.", "Downgrade condition."],
        "sources": [
            {
                "title": "Official source",
                "url": "https://example.com/official",
                "as_of": date,
                "claim": "Completed-session evidence.",
            }
        ],
        "limitations": ["No complete exchange breadth feed."],
    }


class GptRiskPublisherTests(unittest.TestCase):
    def test_publish_updates_only_gpt_journal_contract_and_runs_shell_builder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            market = tmp_path / "market.json"
            journal = tmp_path / "journal.json"
            raw = tmp_path / "response.json"
            market.write_text(json.dumps({"as_of": "2026-08-05"}))
            journal.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "author": "GPT-5.6",
                        "updated_at": "2026-08-04T20:00:00Z",
                        "entries": [{"date": "2026-08-04", "author": "GPT-5.6"}],
                    }
                )
            )
            raw.write_text(json.dumps(response()))
            with (
                mock.patch.object(publisher, "MARKET", market),
                mock.patch.object(publisher, "JOURNAL", journal),
                mock.patch.object(publisher, "refresh_market") as refresh_market,
                mock.patch.object(publisher, "render_chart_page") as render_chart_page,
                mock.patch.object(publisher.subprocess, "run") as run,
            ):
                entry = publisher.publish(raw)

            payload = json.loads(journal.read_text())
            self.assertEqual(payload["entries"][0]["date"], "2026-08-05")
            self.assertEqual(payload["entries"][1]["date"], "2026-08-04")
            self.assertEqual(entry["sources"][0]["url"], "https://example.com/official")
            self.assertIn("https://example.com/official", entry["source_note"])
            refresh_market.assert_called_once()
            self.assertEqual(refresh_market.call_args.args[1], "2026-08-05")
            render_chart_page.assert_called_once()
            run.assert_called_once_with(
                ["python3", "scripts/build-trading-desk.py", "--mode", "close"],
                cwd=ROOT,
                check=True,
            )

    def test_rejects_date_mismatch_before_mutating_journal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = pathlib.Path(tmp)
            market = tmp_path / "market.json"
            journal = tmp_path / "journal.json"
            raw = tmp_path / "response.json"
            market.write_text(json.dumps({"as_of": "2026-08-05"}))
            original = json.dumps({"entries": [{"date": "2026-08-04"}]})
            journal.write_text(original)
            raw.write_text(json.dumps(response("2026-08-04")))
            with mock.patch.object(publisher, "MARKET", market), mock.patch.object(publisher, "JOURNAL", journal):
                with self.assertRaisesRegex(ValueError, "does not match market date"):
                    publisher.publish(raw)
            self.assertEqual(journal.read_text(), original)

    def test_rejects_future_dated_source(self) -> None:
        payload = response()
        payload["sources"][0]["as_of"] = "2026-08-06"
        with self.assertRaisesRegex(ValueError, "after journal cutoff"):
            publisher.validate_source_dates(payload)

    def test_refresh_market_requires_both_series_through_journal_date(self) -> None:
        journal: dict = {
            "entries": [{"date": "2026-08-05"}, {"date": "2026-08-04"}],
        }
        closes = {
            "SPY": [["2026-08-04", 100.0], ["2026-08-05", 101.0]],
            "QQQ": [["2026-08-04", 200.0], ["2026-08-05", 202.0]],
        }
        with mock.patch.object(publisher, "fetch_closes", return_value=closes):
            publisher.refresh_market(journal, "2026-08-05")
        self.assertEqual(journal["chart"]["market"]["updated"], "2026-08-05")
        self.assertEqual(journal["chart"]["market"]["closes"], closes)

        with mock.patch.object(
            publisher,
            "fetch_closes",
            return_value={"SPY": closes["SPY"], "QQQ": closes["QQQ"][:-1]},
        ):
            with self.assertRaisesRegex(ValueError, "do not include completed session"):
                publisher.refresh_market({"entries": journal["entries"]}, "2026-08-05")

    def test_chart_matches_gpt_ratings_and_market_window(self) -> None:
        payload = {
            "entries": [
                {"date": "2026-08-05", "risk_appetite": 6.8, "stance": "Risk-on"},
                {"date": "2026-08-04", "risk_appetite": 5.0, "stance": "Neutral"},
            ],
            "chart": {
                "market": {
                    "updated": "2026-08-05",
                    "closes": {
                        "SPY": [["2026-08-04", 100.0], ["2026-08-05", 101.0]],
                        "QQQ": [["2026-08-04", 200.0], ["2026-08-05", 198.0]],
                    },
                }
            },
        }
        chart = publisher.build_chart(payload)
        self.assertIn("Rating vs the tape", chart)
        self.assertIn("GPT rating (0–10, left)", chart)
        self.assertIn("SPY %", chart)
        self.assertIn("QQQ %", chart)
        self.assertIn("% from 2026-08-04 close · prices thru 2026-08-05", chart)
        self.assertIn("2026-08-05 · model journal · Risk-on · 6.8/10", chart)
        self.assertEqual(chart.count("<circle "), 2)

    def test_chart_is_inserted_above_the_journal_mount(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            page = pathlib.Path(tmp) / "index.html"
            page.write_text('<div class="phead"></div><div id="risk-live"></div>')
            payload = {
                "entries": [
                    {"date": "2026-08-05", "risk_appetite": 6.8, "stance": "Risk-on"},
                    {"date": "2026-08-04", "risk_appetite": 5.0, "stance": "Neutral"},
                ],
                "chart": {
                    "market": {
                        "updated": "2026-08-05",
                        "closes": {
                            "SPY": [["2026-08-04", 100.0], ["2026-08-05", 101.0]],
                            "QQQ": [["2026-08-04", 200.0], ["2026-08-05", 198.0]],
                        },
                    }
                },
            }
            with mock.patch.object(publisher, "PAGE", page):
                publisher.render_chart_page(payload)
                publisher.render_chart_page(payload)
            rendered = page.read_text()
            self.assertEqual(rendered.count(publisher.CHART_START), 1)
            self.assertLess(rendered.index("Rating vs the tape"), rendered.index('id="risk-live"'))


if __name__ == "__main__":
    unittest.main()
