#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import re
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
    def test_every_canonical_hypothesis_has_a_position_profile(self):
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        hypotheses = {
            symbol.upper()
            for symbol in re.findall(
                r'id="hypothesis-([a-z0-9.-]+)-setup"',
                source,
            )
        }
        self.assertFalse(hypotheses - set(profiles))
        self.assertIn("JCI", profiles)
        self.assertEqual(profiles["JCI"]["sector"], "Industrials")
        self.assertEqual(profiles["JCI"]["sector_etf"], "XLI")
        self.assertEqual(profiles["JCI"]["flair"], "thesis")

    def test_reset_keeps_only_live_positions_in_the_canonical_thesis_registry(self):
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        hypotheses = {
            symbol.upper()
            for symbol in re.findall(r'id="hypothesis-([a-z0-9.-]+)-setup"', source)
        }
        valuations = set(json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"])
        charts = set(json.loads((ROOT / "trading" / "hypothesis-charts.json").read_text())["charts"])
        positions = {
            row["symbol"]
            for row in json.loads((ROOT / "trading" / "desk-positions.json").read_text())["positions"]
        }
        desk = (ROOT / "trading" / "index.html").read_text()

        self.assertEqual(hypotheses, positions)
        self.assertEqual(valuations, positions)
        self.assertEqual(charts, positions)
        self.assertNotIn('data-desk-kind="hypothesis"', desk)
        self.assertIn("New hunt starts empty. Add only researched setups worth tracking.", desk)

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
        self.assertEqual(result["sleeves"]["thesis"], {
            "capital_percent": 0.0,
            "exposure_percent": 0.0,
            "premium_at_risk_percent": 0.0,
        })
        self.assertEqual([row["symbol"] for row in result["positions"]], ["AAA"])
        self.assertEqual(result["positions"][0]["exposure_percent"], 171.4)
        self.assertEqual(result["positions"][0]["capital_percent"], 19.4)
        self.assertEqual(result["positions"][0]["implied_volatility_percent"], 27.0)
        self.assertEqual(result["positions"][0]["instrument"], "Equity · Jan 2027 $15 call")
        self.assertNotIn("entry", result["positions"][0])
        public = builder.serialize(result).casefold()
        for forbidden in ("quantity\"", "account", "1234", "total_value", "allocation_percent", "equity_entry", "@ $10.12", "@ $2.29"):
            self.assertNotIn(forbidden, public)

    def test_positions_sort_by_delta_exposure_descending_without_capping_at_100(self):
        holdings = {"risk_summary": summary(), "desk_instruments": {
            "AAA": {"equity_entry": 10.0, "equity_side": "long", **risk(171.4), "options": []},
            "BBB": {"equity_entry": 20.0, "equity_side": "long", **risk(23.4, iv=None, delta=None, dte=None, premium=0, theta=0), "options": []},
        }}
        result = builder.render(holdings, self.profiles())
        self.assertEqual([row["symbol"] for row in result["positions"]], ["AAA", "BBB"])
        self.assertGreater(result["positions"][0]["exposure_percent"], 100)

    def test_signed_margin_cash_is_valid_public_summary(self):
        signed_summary = summary()
        signed_summary["cash_percent"] = -12.5
        holdings = {"risk_summary": signed_summary, "desk_instruments": {
            "AAA": {"equity_entry": 10.0, "equity_side": "long", **risk(7.8), "options": []},
        }}
        result = builder.render(holdings, self.profiles())
        self.assertEqual(result["risk_summary"]["cash_percent"], -12.5)

    def test_unknown_held_symbol_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "need authored Desk profiles"):
            builder.render({"risk_summary": summary(), "desk_instruments": {"NEW": {"equity_entry": 5.0, "options": []}}}, self.profiles())

    def test_pl_is_authored_as_a_thesis_position(self):
        profiles = self.profiles()
        profiles["profiles"]["PL"] = {
            "kill": None,
            "flair": "thesis",
            "sector": "Technology",
            "sector_etf": "XLK",
            "thesis": "Daily Earth imagery and defense demand must convert backlog into durable recurring revenue.",
        }
        result = builder.render({"risk_summary": summary(), "desk_instruments": {
            "PL": {"equity_entry": 22.63, "equity_side": "long", **risk(3.5, iv=None, delta=None, dte=None, premium=0, theta=0), "options": []},
        }}, profiles)
        self.assertEqual(result["positions"][0]["symbol"], "PL")
        self.assertEqual(result["positions"][0]["flair"], "thesis")
        self.assertEqual(result["positions"][0]["sector_etf"], "XLK")

    def test_live_owner_chart_assertions_follow_the_refreshable_scan_date(self):
        tests = Path(__file__).read_text()
        brittle = re.findall(
            r'charts\[[^\n]+\]\["series"\]\["dates"\]\[-1\], "\d{4}-\d{2}-\d{2}"',
            tests,
        )
        self.assertEqual(brittle, [], "chart-end assertions must compare with scan['last_bar']")

    def test_rtx_live_holding_has_exact_canonical_owners(self):
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        valuations = json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"]
        scan = json.loads((ROOT / "trading" / "scan-universe.json").read_text())
        charts = json.loads((ROOT / "trading" / "scan-charts.json").read_text())["charts"]
        long_history = json.loads((ROOT / "trading" / "hypothesis-charts.json").read_text())
        universe = {row["symbol"]: row for row in scan["rows"]}

        self.assertEqual(profiles["RTX"]["flair"], "thesis")
        self.assertEqual(profiles["RTX"]["sector"], "Industrials")
        self.assertEqual(profiles["RTX"]["sector_etf"], "XLI")
        self.assertIn('id="hypothesis-rtx-setup"', source)
        self.assertIn(
            'data-desk-catalyst="2026-10-20" data-desk-catalyst-name="Est. Q3 earnings"',
            source,
        )
        self.assertIn("RTX has not confirmed the 2026 date", source)
        self.assertEqual(valuations["RTX"]["entry_levels"], {"bear": 149.53, "base": 210.28, "bull": 225.49})
        self.assertEqual(universe["RTX"]["sector"], "Industrials")
        self.assertEqual(charts["RTX"]["sector_etf"], "XLI")
        self.assertEqual(charts["RTX"]["series"]["dates"][-1], scan["last_bar"])
        self.assertEqual(long_history["charts"]["RTX"]["dates"][-1], long_history["as_of"])

    def test_hood_live_holding_has_exact_canonical_owners(self):
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        valuations = json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"]
        scan = json.loads((ROOT / "trading" / "scan-universe.json").read_text())
        charts = json.loads((ROOT / "trading" / "scan-charts.json").read_text())["charts"]
        long_history = json.loads((ROOT / "trading" / "hypothesis-charts.json").read_text())
        universe = {row["symbol"]: row for row in scan["rows"]}

        self.assertEqual(profiles["HOOD"]["flair"], "thesis")
        self.assertEqual(profiles["HOOD"]["sector"], "Financials")
        self.assertEqual(profiles["HOOD"]["sector_etf"], "XLF")
        self.assertIn('id="hypothesis-hood-setup"', source)
        self.assertIn(
            'data-desk-catalyst="2026-11-04" data-desk-catalyst-name="Est. Q3 earnings"',
            source,
        )
        self.assertIn("Robinhood has not confirmed the 2026 date", source)
        self.assertEqual(valuations["HOOD"]["entry_levels"], {"bear": 65.16, "base": 104.26, "bull": 152.46})
        self.assertEqual(universe["HOOD"]["sector"], "Financials")
        self.assertEqual(charts["HOOD"]["sector_etf"], "XLF")
        self.assertEqual(charts["HOOD"]["series"]["dates"][-1], scan["last_bar"])
        self.assertEqual(long_history["charts"]["HOOD"]["dates"][-1], long_history["as_of"])

    def test_september_live_additions_have_exact_canonical_owners(self):
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        valuations = json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"]
        scan = json.loads((ROOT / "trading" / "scan-universe.json").read_text())
        charts = json.loads((ROOT / "trading" / "scan-charts.json").read_text())["charts"]
        long_history = json.loads((ROOT / "trading" / "hypothesis-charts.json").read_text())
        universe = {row["symbol"]: row for row in scan["rows"]}
        expected = {
            "BABA": ("Consumer Discretionary", "Consumer Disc", "XLY", "2026-11-19", "Est. September-quarter earnings", "Alibaba has not confirmed", {"bear": 94.81, "base": 112.85, "bull": 187.62}),
            "KOPN": ("Technology", "Technology", "XLK", "2026-11-10", "Est. Q3 earnings", "Kopin has not confirmed", {"bear": 1.82, "base": 4.21, "bull": 6.39}),
        }
        for symbol, (sector, scan_sector, sector_etf, catalyst, catalyst_name, unconfirmed, levels) in expected.items():
            with self.subTest(symbol=symbol):
                self.assertEqual(profiles[symbol]["flair"], "thesis")
                self.assertEqual(profiles[symbol]["sector"], sector)
                self.assertEqual(profiles[symbol]["sector_etf"], sector_etf)
                self.assertIn(f'id="hypothesis-{symbol.lower()}-setup"', source)
                self.assertIn(
                    f'data-desk-catalyst="{catalyst}" data-desk-catalyst-name="{catalyst_name}"',
                    source,
                )
                self.assertIn(unconfirmed, source)
                self.assertEqual(valuations[symbol]["entry_levels"], levels)
                self.assertEqual(universe[symbol]["sector"], scan_sector)
                self.assertEqual(charts[symbol]["sector_etf"], sector_etf)
                self.assertEqual(charts[symbol]["series"]["dates"][-1], scan["last_bar"])
                self.assertEqual(long_history["charts"][symbol]["dates"][-1], scan["last_bar"])

    def test_missing_risk_summary_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "risk_summary"):
            builder.render({"desk_instruments": {"AAA": {"equity_entry": 10.0, **risk(7.8), "options": []}}}, self.profiles())

    def test_private_entry_values_are_not_required_or_published(self):
        result = builder.render({"risk_summary": summary(), "desk_instruments": {"AAA": {"equity_entry": None, "equity_side": "long", **risk(7.8), "options": [{"option_type": "call", "strike": 15, "expiration": "2027-01-15", "entry": 2.0}]}}}, self.profiles())
        public = builder.serialize(result)
        self.assertNotIn('"entry"', public)
        self.assertNotIn("@ $2.00", public)


if __name__ == "__main__":
    unittest.main()
