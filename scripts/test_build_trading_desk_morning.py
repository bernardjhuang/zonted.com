#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_trading_desk", ROOT / "scripts" / "build-trading-desk.py")
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class MorningDeskChartTests(unittest.TestCase):
    def chart(self):
        return {"dates": ["2026-07-24", "2026-07-27"], "close": [9.0, 10.0], "beta_2y_weekly_vs_spy": 1.2}

    def scan(self):
        return {"series": {"dates": ["2026-07-24", "2026-07-27"], "c": [9.0, 10.0]}, "stats": {"spread_z": 0.4}}

    def test_morning_quote_appends_live_session_to_chart(self):
        source = self.chart()
        market = builder.row_market("AAA", source, self.scan(), {"price": 11.0, "day_pct": 10.0}, dt.date(2026, 7, 28))
        self.assertEqual(market["dates"], ["2026-07-24", "2026-07-27", "2026-07-28"])
        self.assertEqual(market["closes"], [9.0, 10.0, 11.0])
        self.assertEqual(source["dates"], ["2026-07-24", "2026-07-27"], "renderer mutated canonical chart data")

    def test_same_session_rerun_replaces_live_chart_point(self):
        source = {"dates": ["2026-07-27", "2026-07-28"], "close": [10.0, 10.5], "beta_2y_weekly_vs_spy": 1.2}
        market = builder.row_market("AAA", source, None, {"price": 11.0, "day_pct": 10.0}, dt.date(2026, 7, 28))
        self.assertEqual(market["dates"], ["2026-07-27", "2026-07-28"])
        self.assertEqual(market["closes"], [10.0, 11.0])

    def test_quote_requires_a_session_date(self):
        with self.assertRaisesRegex(ValueError, "no session date"):
            builder.row_market("AAA", self.chart(), self.scan(), {"price": 11.0, "day_pct": 10.0})

    def test_quote_artifact_requires_public_schema_version(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "quotes.json"
            path.write_text(json.dumps({"generated_at": "2026-07-28T08:45:00-05:00", "quotes": {}}))
            with self.assertRaisesRegex(ValueError, "schema_version 1"):
                builder.quotes_from(path)


if __name__ == "__main__":
    unittest.main()
