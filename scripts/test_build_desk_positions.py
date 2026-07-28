#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("build_desk_positions", ROOT / "scripts" / "build-desk-positions.py")
assert SPEC and SPEC.loader
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class DeskPositionBuilderTests(unittest.TestCase):
    def profiles(self):
        return {
            "schema_version": 1,
            "profiles": {
                "AAA": {"kill": 9.0, "flair": "momentum", "sector": "Tech", "sector_etf": "XLK", "thesis": "A"},
                "BBB": {"kill": None, "flair": "thesis", "sector": "Finance", "sector_etf": "XLF", "thesis": "B"},
            },
        }

    def test_render_uses_live_membership_and_costs_without_private_fields(self):
        holdings = {
            "account_last4": "1234",
            "quantity": "999",
            "cash_percent": 4.4,
            "desk_instruments": {
                "AAA": {
                    "equity_entry": 10.125,
                    "equity_side": "long",
                    "allocation_percent": 7.8,
                    "options": [{"option_type": "call", "strike": 15, "expiration": "2027-01-15", "entry": 2.285}],
                }
            },
        }
        result = builder.render(holdings, self.profiles())
        self.assertEqual([row["symbol"] for row in result["positions"]], ["AAA"])
        self.assertEqual(result["cash_percent"], 4.4)
        self.assertEqual(result["positions"][0]["entry"], 10.12)
        self.assertEqual(result["positions"][0]["allocation_percent"], 7.8)
        self.assertEqual(result["positions"][0]["instrument"], "Equity @ $10.12 · Jan 2027 $15 call @ $2.29")
        public = builder.serialize(result).casefold()
        self.assertNotIn("quantity", public)
        self.assertNotIn("account", public)
        self.assertNotIn("1234", public)

    def test_positions_sort_by_allocation_descending(self):
        holdings = {"cash_percent": 4.4, "desk_instruments": {
            "AAA": {"equity_entry": 10.0, "equity_side": "long", "allocation_percent": 7.8, "options": []},
            "BBB": {"equity_entry": 20.0, "equity_side": "long", "allocation_percent": 23.4, "options": []},
        }}
        result = builder.render(holdings, self.profiles())
        self.assertEqual(result["schema_version"], 2)
        self.assertEqual([row["symbol"] for row in result["positions"]], ["BBB", "AAA"])

    def test_unknown_held_symbol_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "need authored Desk profiles"):
            builder.render({"cash_percent": 4.4, "desk_instruments": {"NEW": {"equity_entry": 5.0, "options": []}}}, self.profiles())

    def test_missing_cash_percent_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "cash_percent"):
            builder.render({"desk_instruments": {"AAA": {"equity_entry": 10.0, "allocation_percent": 7.8, "options": []}}}, self.profiles())

    def test_option_only_position_fails_instead_of_plotting_option_cost_on_stock_chart(self):
        with self.assertRaisesRegex(ValueError, "positive equity_entry"):
            builder.render({"cash_percent": 4.4, "desk_instruments": {"AAA": {"equity_entry": None, "options": [{"option_type": "call", "strike": 15, "expiration": "2027-01-15", "entry": 2.0}]}}}, self.profiles())


if __name__ == "__main__":
    unittest.main()
