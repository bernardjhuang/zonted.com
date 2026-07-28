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


def risk(
    exposure: float,
    *,
    capital: float = 19.4,
    premium: float = 19.2,
    theta: float = -0.12,
    iv: float | None = 27.0,
    delta: float | None = 0.3436,
    dte: int | None = 171,
    unstable: bool = False,
):
    return {
        "exposure_percent": exposure,
        "capital_percent": capital,
        "premium_at_risk_percent": premium,
        "theta_percent_per_day": theta,
        "implied_volatility_percent": iv,
        "delta_used": delta,
        "min_dte": dte,
        "unstable_delta": unstable,
    }


def summary():
    return {
        "gross_delta_leverage": 3.98,
        "net_delta_exposure_percent": 398.5,
        "premium_at_risk_percent": 35.9,
        "theta_percent_per_day": -0.91,
        "cash_percent": 5.9,
        "quantity_basis": "gross held positions; pending orders not netted",
    }


class DeskPositionBuilderTests(unittest.TestCase):
    def profiles(self):
        return {
            "schema_version": 1,
            "profiles": {
                "AAA": {"kill": 9.0, "flair": "momentum", "sector": "Tech", "sector_etf": "XLK", "thesis": "A"},
                "BBB": {"kill": None, "flair": "thesis", "sector": "Finance", "sector_etf": "XLF", "thesis": "B"},
            },
        }

    def test_render_uses_live_membership_and_risk_without_private_fields(self):
        holdings = {
            "account_last4": "1234",
            "quantity": "999",
            "total_value": "10000",
            "risk_summary": summary(),
            "desk_instruments": {
                "AAA": {
                    "equity_entry": 10.125,
                    "equity_side": "long",
                    **risk(171.4),
                    "options": [{"option_type": "call", "strike": 15, "expiration": "2027-01-15", "entry": 2.285}],
                }
            },
        }
        result = builder.render(holdings, self.profiles())
        self.assertEqual(result["schema_version"], 3)
        self.assertEqual(result["risk_summary"], summary())
        self.assertEqual(result["sleeves"]["momentum"], {
            "capital_percent": 19.4,
            "exposure_percent": 171.4,
            "premium_at_risk_percent": 19.2,
        })
        self.assertEqual([row["symbol"] for row in result["positions"]], ["AAA"])
        self.assertEqual(result["positions"][0]["entry"], 10.12)
        self.assertEqual(result["positions"][0]["exposure_percent"], 171.4)
        self.assertEqual(result["positions"][0]["capital_percent"], 19.4)
        self.assertEqual(result["positions"][0]["implied_volatility_percent"], 27.0)
        self.assertEqual(result["positions"][0]["instrument"], "Equity @ $10.12 · Jan 2027 $15 call @ $2.29")
        public = builder.serialize(result).casefold()
        for forbidden in ("quantity\"", "account", "1234", "total_value", "allocation_percent"):
            self.assertNotIn(forbidden, public)

    def test_positions_sort_by_delta_exposure_descending_without_capping_at_100(self):
        holdings = {"risk_summary": summary(), "desk_instruments": {
            "AAA": {"equity_entry": 10.0, "equity_side": "long", **risk(171.4), "options": []},
            "BBB": {"equity_entry": 20.0, "equity_side": "long", **risk(23.4, iv=None, delta=None, dte=None, premium=0, theta=0), "options": []},
        }}
        result = builder.render(holdings, self.profiles())
        self.assertEqual([row["symbol"] for row in result["positions"]], ["AAA", "BBB"])
        self.assertGreater(result["positions"][0]["exposure_percent"], 100)

    def test_unknown_held_symbol_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "need authored Desk profiles"):
            builder.render({"risk_summary": summary(), "desk_instruments": {"NEW": {"equity_entry": 5.0, "options": []}}}, self.profiles())

    def test_missing_risk_summary_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "risk_summary"):
            builder.render({"desk_instruments": {"AAA": {"equity_entry": 10.0, **risk(7.8), "options": []}}}, self.profiles())

    def test_option_only_position_fails_instead_of_plotting_option_cost_on_stock_chart(self):
        with self.assertRaisesRegex(ValueError, "positive equity_entry"):
            builder.render({"risk_summary": summary(), "desk_instruments": {"AAA": {"equity_entry": None, **risk(7.8), "options": [{"option_type": "call", "strike": 15, "expiration": "2027-01-15", "entry": 2.0}]}}}, self.profiles())


if __name__ == "__main__":
    unittest.main()
