#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
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

    def test_new_listing_without_spread_z_keeps_price_feed(self):
        scan = self.scan()
        scan["stats"]["spread_z"] = None
        market = builder.row_market("AAA", self.chart(), scan, None)
        self.assertTrue(market["feed"])
        self.assertIn("No feed", builder.spread_cell(market))

    def test_robinhood_quote_activates_otc_market_row(self):
        market = builder.row_market(
            "BYDDY",
            self.chart(),
            None,
            {"price": 12.03, "day_pct": 1.52, "source": "robinhood"},
            dt.date(2026, 7, 28),
        )
        self.assertTrue(market["feed"])
        self.assertEqual(market["last"], 12.03)
        self.assertEqual(market["day"], 1.52)
        self.assertEqual(market["dates"][-1], "2026-07-28")
        self.assertEqual(market["closes"][-1], 12.03)
        self.assertEqual(market["source"], "robinhood")
        self.assertIn("No feed", builder.spread_cell(market))

    def test_close_mode_defaults_to_checked_in_fallback_quotes(self):
        with tempfile.TemporaryDirectory() as root:
            fallback = Path(root) / "desk-close-quotes.json"
            fallback.write_text("{}")
            self.assertEqual(builder.resolve_quote_path("close", None, fallback), fallback)
            self.assertIsNone(builder.resolve_quote_path("morning", None, fallback))

    def test_quote_requires_a_session_date(self):
        with self.assertRaisesRegex(ValueError, "no session date"):
            builder.row_market("AAA", self.chart(), self.scan(), {"price": 11.0, "day_pct": 10.0})

    def test_quote_artifact_requires_public_schema_version(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "quotes.json"
            path.write_text(json.dumps({"generated_at": "2026-07-28T08:45:00-05:00", "quotes": {}}))
            with self.assertRaisesRegex(ValueError, "schema_version 1"):
                builder.quotes_from(path)

    def test_live_stamp_is_always_rendered_in_central_time(self):
        stamp = dt.datetime.fromisoformat("2026-07-29T14:12:00+00:00")
        self.assertEqual(builder.live_stamp(stamp), "Live · July 29, 2026 · 9:12 AM CT")

    def test_negative_cash_is_labeled_margin_debit(self):
        summary = {
            "gross_delta_leverage": 1.0,
            "net_delta_exposure_percent": 90.0,
            "premium_at_risk_percent": 5.0,
            "theta_percent_per_day": -0.1,
            "cash_percent": -12.5,
            "quantity_basis": "gross held positions; pending orders not netted",
        }
        rendered = builder.risk_strip(summary, {})
        self.assertIn("Margin debit <b>-12.5%</b>", rendered)
        self.assertNotIn("Cash liquidity", rendered)

    def test_no_feed_position_renders_without_intraday_fields(self):
        position = {
            "symbol": "BYDDY",
            "instrument": "Equity",
            "exposure_percent": 5.9,
            "capital_percent": 5.9,
            "premium_at_risk_percent": 0.0,
            "theta_percent_per_day": 0.0,
            "unstable_delta": False,
            "kill": None,
            "flair": "thesis",
            "sector": "Consumer Discretionary",
            "thesis": "China EV recovery thesis.",
        }
        metadata = {"BYDDY": {"catalyst": "2026-08-27", "catalyst-name": "August deliveries"}}
        markets = {"BYDDY": {"feed": False, "beta": 0.8}}
        valuations = {"BYDDY": {
            "valuation_metrics": [{"label": "Market cap", "value": "$101B"}, {"label": "TTM P/E", "value": "25×"}],
            "entry_levels": {"bear": 4.77, "base": 6.35, "bull": 7.94},
            "method": "Reported earnings",
            "confidence": "low",
        }}
        rendered = builder.position_rows([position], metadata, markets, valuations, dt.date(2026, 7, 30))
        self.assertIn('data-desk-symbol="BYDDY"', rendered)
        self.assertIn('data-edge="no-feed" data-feed-state="no-feed"', rendered)
        self.assertIn("No feed", rendered)
        self.assertIn('data-label="Beta">0.80<', rendered)


if __name__ == "__main__":
    unittest.main()
