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

    def test_brbr_is_authored_for_the_legacy_live_holding(self):
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        self.assertEqual(profiles["BRBR"]["flair"], "thesis")
        self.assertEqual(profiles["BRBR"]["sector"], "Consumer Staples")
        self.assertEqual(profiles["BRBR"]["sector_etf"], "XLP")
        self.assertIn("Legacy Robinhood", profiles["BRBR"]["thesis"])
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        valuations = json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"]
        self.assertIn('id="hypothesis-brbr-setup"', source)
        self.assertIn('data-desk-catalyst-name="Est. fiscal Q4 earnings"', source)
        self.assertEqual(valuations["BRBR"]["entry_levels"], {"bear": 7.9, "base": 10.85, "bull": 42.68})

    def test_mos_is_authored_for_the_live_fertilizer_position(self):
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        self.assertEqual(profiles["MOS"]["flair"], "thesis")
        self.assertEqual(profiles["MOS"]["sector"], "Materials")
        self.assertEqual(profiles["MOS"]["sector_etf"], "XLB")
        self.assertIn("sulfur-cost pressure", profiles["MOS"]["thesis"])
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        valuations = json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"]
        self.assertIn('id="hypothesis-mos-setup"', source)
        self.assertIn('data-desk-catalyst-name="Est. Q3 earnings"', source)
        self.assertEqual(valuations["MOS"]["entry_levels"], {"bear": 19.82, "base": 22.6, "bull": 31.04})

    def test_way_live_holding_has_exact_canonical_owners(self):
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        valuations = json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"]
        scan = json.loads((ROOT / "trading" / "scan-universe.json").read_text())
        charts = json.loads((ROOT / "trading" / "scan-charts.json").read_text())["charts"]
        universe = {row["symbol"]: row for row in scan["rows"]}
        self.assertEqual(profiles["WAY"]["flair"], "thesis")
        self.assertEqual(profiles["WAY"]["sector"], "Health Care")
        self.assertEqual(profiles["WAY"]["sector_etf"], "XLV")
        self.assertIn('id="hypothesis-way-setup"', source)
        self.assertEqual(set(valuations["WAY"]["entry_levels"]), {"bear", "base", "bull"})
        self.assertEqual(universe["WAY"]["sector"], "Health Care")
        self.assertEqual(charts["WAY"]["sector_etf"], "XLV")
        self.assertEqual(charts["WAY"]["series"]["dates"][-1], scan["last_bar"])

    def test_aaon_live_holding_has_exact_canonical_owners(self):
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        valuations = json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"]
        scan = json.loads((ROOT / "trading" / "scan-universe.json").read_text())
        charts = json.loads((ROOT / "trading" / "scan-charts.json").read_text())["charts"]
        universe = {row["symbol"]: row for row in scan["rows"]}
        self.assertEqual(profiles["AAON"]["flair"], "thesis")
        self.assertEqual(profiles["AAON"]["sector"], "Industrials")
        self.assertEqual(profiles["AAON"]["sector_etf"], "XLI")
        self.assertIn('id="hypothesis-aaon-setup"', source)
        self.assertIn('data-desk-catalyst="2026-11-05" data-desk-catalyst-name="Est. Q3 earnings"', source)
        self.assertIn("AAON has not confirmed the 2026 date", source)
        self.assertEqual(valuations["AAON"]["entry_levels"], {"bear": 71.77, "base": 87.67, "bull": 148.15})
        self.assertEqual(universe["AAON"]["sector"], "Industrials")
        self.assertEqual(charts["AAON"]["sector_etf"], "XLI")
        self.assertEqual(charts["AAON"]["series"]["dates"][-1], scan["last_bar"])

    def test_nke_live_holding_has_exact_canonical_owners(self):
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        valuations = json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"]
        scan = json.loads((ROOT / "trading" / "scan-universe.json").read_text())
        charts = json.loads((ROOT / "trading" / "scan-charts.json").read_text())["charts"]
        universe = {row["symbol"]: row for row in scan["rows"]}
        self.assertEqual(profiles["NKE"]["flair"], "thesis")
        self.assertEqual(profiles["NKE"]["sector"], "Consumer Discretionary")
        self.assertEqual(profiles["NKE"]["sector_etf"], "XLY")
        self.assertIn('id="hypothesis-nke-setup"', source)
        self.assertIn('data-desk-catalyst="2026-09-08" data-desk-catalyst-name="Confirmed annual meeting"', source)
        self.assertIn("NIKE has not announced its fiscal Q1 2027 earnings date", source)
        self.assertEqual(valuations["NKE"]["entry_levels"], {"bear": 40.51, "base": 40.73, "bull": 77.06})
        self.assertEqual(universe["NKE"]["sector"], "Consumer Disc")
        self.assertEqual(charts["NKE"]["sector_etf"], "XLY")
        self.assertEqual(charts["NKE"]["series"]["dates"][-1], scan["last_bar"])

    def test_august_17_live_additions_have_exact_canonical_owners(self):
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        valuations = json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"]
        scan = json.loads((ROOT / "trading" / "scan-universe.json").read_text())
        charts = json.loads((ROOT / "trading" / "scan-charts.json").read_text())["charts"]
        universe = {row["symbol"]: row for row in scan["rows"]}
        expected = {
            "BOT": ("Technology", "XLK", "2026-08-30", "Est. July NAV update"),
            "CYPH": ("Financials", "XLF", "2026-11-11", "Est. Q3 results"),
            "GRND": ("Communication Services", "XLC", "2026-11-05", "Est. Q3 results"),
            "OSCR": ("Health Care", "XLV", "2026-11-05", "Est. Q3 results"),
        }
        for symbol, (sector, etf, catalyst, catalyst_name) in expected.items():
            with self.subTest(symbol=symbol):
                slug = symbol.lower()
                self.assertEqual(profiles[symbol]["flair"], "thesis")
                self.assertEqual(profiles[symbol]["sector"], sector)
                self.assertEqual(profiles[symbol]["sector_etf"], etf)
                self.assertIn(f'id="hypothesis-{slug}-setup"', source)
                self.assertIn(
                    f'data-desk-catalyst="{catalyst}" data-desk-catalyst-name="{catalyst_name}"',
                    source,
                )
                self.assertEqual(set(valuations[symbol]["entry_levels"]), {"bear", "base", "bull"})
                self.assertEqual(universe[symbol]["sector"], charts[symbol]["sector"])
                self.assertEqual(charts[symbol]["sector_etf"], etf)
                self.assertEqual(charts[symbol]["series"]["dates"][-1], scan["last_bar"])

    def test_august_18_live_additions_have_exact_canonical_owners(self):
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        valuations = json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"]
        scan = json.loads((ROOT / "trading" / "scan-universe.json").read_text())
        charts = json.loads((ROOT / "trading" / "scan-charts.json").read_text())["charts"]
        universe = {row["symbol"]: row for row in scan["rows"]}
        expected = {
            "CRWV": ("Technology", "XLK", "2026-11-10", "Est. Q3 earnings"),
            "CTVA": ("Materials", "XLB", "2026-09-15", "Confirmed investor days"),
            "DASH": ("Consumer Discretionary", "XLY", "2026-11-04", "Est. Q3 earnings"),
            "FIGR": ("Financials", "XLF", "2026-11-12", "Est. Q3 earnings"),
            "HIMS": ("Health Care", "XLV", "2026-11-09", "Est. Q3 earnings"),
            "LYV": ("Communication Services", "XLC", "2026-10-29", "Est. Q3 earnings"),
            "TOST": ("Technology", "XLK", "2026-11-03", "Est. Q3 earnings"),
        }
        for symbol, (sector, etf, catalyst, catalyst_name) in expected.items():
            with self.subTest(symbol=symbol):
                slug = symbol.lower()
                self.assertEqual(profiles[symbol]["flair"], "thesis")
                self.assertEqual(profiles[symbol]["sector"], sector)
                self.assertEqual(profiles[symbol]["sector_etf"], etf)
                self.assertIn(f'id="hypothesis-{slug}-setup"', source)
                self.assertIn(
                    f'data-desk-catalyst="{catalyst}" data-desk-catalyst-name="{catalyst_name}"',
                    source,
                )
                if symbol == "CTVA":
                    self.assertIn("Corteva confirmed webcast investor days", source)
                else:
                    self.assertIn("has not confirmed the date", source)
                self.assertEqual(set(valuations[symbol]["entry_levels"]), {"bear", "base", "bull"})
                self.assertEqual(universe[symbol]["sector"], charts[symbol]["sector"])
                self.assertEqual(charts[symbol]["sector_etf"], etf)
                self.assertEqual(charts[symbol]["series"]["dates"][-1], scan["last_bar"])

    def test_live_owner_chart_assertions_follow_the_refreshable_scan_date(self):
        tests = Path(__file__).read_text()
        brittle = re.findall(
            r'charts\[[^\n]+\]\["series"\]\["dates"\]\[-1\], "\d{4}-\d{2}-\d{2}"',
            tests,
        )
        self.assertEqual(brittle, [], "chart-end assertions must compare with scan['last_bar']")

    def test_djt_live_holding_has_exact_canonical_owners(self):
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        valuations = json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"]
        scan = json.loads((ROOT / "trading" / "scan-universe.json").read_text())
        charts = json.loads((ROOT / "trading" / "scan-charts.json").read_text())["charts"]
        universe = {row["symbol"]: row for row in scan["rows"]}

        self.assertEqual(profiles["DJT"]["flair"], "thesis")
        self.assertEqual(profiles["DJT"]["sector"], "Communication Services")
        self.assertEqual(profiles["DJT"]["sector_etf"], "XLC")
        self.assertIn('id="hypothesis-djt-setup"', source)
        self.assertIn(
            'data-desk-catalyst="2026-11-09" data-desk-catalyst-name="Est. Q3 earnings"',
            source,
        )
        self.assertIn("Trump Media has not confirmed the date", source)
        self.assertEqual(valuations["DJT"]["entry_levels"], {"bear": 7.06, "base": 8.06, "bull": 18.5})
        self.assertEqual(universe["DJT"]["sector"], charts["DJT"]["sector"])
        self.assertEqual(charts["DJT"]["sector_etf"], "XLC")
        self.assertEqual(charts["DJT"]["series"]["dates"][-1], scan["last_bar"])

    def test_xle_live_holding_has_exact_canonical_owners(self):
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        valuations = json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"]
        scan = json.loads((ROOT / "trading" / "scan-universe.json").read_text())
        charts = json.loads((ROOT / "trading" / "scan-charts.json").read_text())["charts"]
        long_history = json.loads((ROOT / "trading" / "hypothesis-charts.json").read_text())
        universe = {row["symbol"]: row for row in scan["rows"]}

        self.assertEqual(profiles["XLE"]["flair"], "thesis")
        self.assertEqual(profiles["XLE"]["sector"], "Energy")
        self.assertEqual(profiles["XLE"]["sector_etf"], "XLE")
        self.assertIn('id="hypothesis-xle-setup"', source)
        self.assertIn(
            'data-desk-catalyst="2026-09-09" data-desk-catalyst-name="Confirmed EIA STEO"',
            source,
        )
        self.assertIn("next STEO release for September 9, 2026", source)
        self.assertEqual(valuations["XLE"]["entry_levels"], {"bear": 41.24, "base": 63.68, "bull": 63.68})
        self.assertEqual(universe["XLE"]["sector"], "Energy")
        self.assertEqual(charts["XLE"]["sector_etf"], "XLE")
        self.assertEqual(charts["XLE"]["series"]["dates"][-1], scan["last_bar"])
        self.assertEqual(long_history["charts"]["XLE"]["dates"][-1], long_history["as_of"])

    def test_payx_live_holding_has_exact_canonical_owners(self):
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        valuations = json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"]
        scan = json.loads((ROOT / "trading" / "scan-universe.json").read_text())
        charts = json.loads((ROOT / "trading" / "scan-charts.json").read_text())["charts"]
        long_history = json.loads((ROOT / "trading" / "hypothesis-charts.json").read_text())
        universe = {row["symbol"]: row for row in scan["rows"]}

        self.assertEqual(profiles["PAYX"]["flair"], "thesis")
        self.assertEqual(profiles["PAYX"]["sector"], "Industrials")
        self.assertEqual(profiles["PAYX"]["sector_etf"], "XLI")
        self.assertIn('id="hypothesis-payx-setup"', source)
        self.assertIn(
            'data-desk-catalyst="2026-09-30" data-desk-catalyst-name="Est. fiscal Q1 earnings"',
            source,
        )
        self.assertIn("Paychex has not confirmed the fiscal 2027 date", source)
        self.assertEqual(valuations["PAYX"]["entry_levels"], {"bear": 83.61, "base": 119.93, "bull": 134.87})
        self.assertEqual(universe["PAYX"]["sector"], "Industrials")
        self.assertEqual(charts["PAYX"]["sector_etf"], "XLI")
        self.assertEqual(charts["PAYX"]["series"]["dates"][-1], scan["last_bar"])
        self.assertEqual(long_history["charts"]["PAYX"]["dates"][-1], long_history["as_of"])

    def test_august_live_holdings_have_exact_canonical_owners(self):
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        valuations = json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"]
        scan = json.loads((ROOT / "trading" / "scan-universe.json").read_text())
        charts = json.loads((ROOT / "trading" / "scan-charts.json").read_text())["charts"]
        long_history = json.loads((ROOT / "trading" / "hypothesis-charts.json").read_text())
        universe = {row["symbol"]: row for row in scan["rows"]}
        expected = {
            "AVAV": ("Industrials", "Industrials", "XLI", "2026-09-09", "Est. fiscal Q1 earnings"),
            "LULU": ("Consumer Discretionary", "Consumer Disc", "XLY", "2026-09-03", "Confirmed fiscal Q2 earnings"),
            "SBUX": ("Consumer Discretionary", "Consumer Disc", "XLY", "2026-10-28", "Est. fiscal Q4 earnings"),
        }

        for symbol, (sector, scan_sector, sector_etf, catalyst, catalyst_name) in expected.items():
            self.assertEqual(profiles[symbol]["flair"], "thesis")
            self.assertEqual(profiles[symbol]["sector"], sector)
            self.assertEqual(profiles[symbol]["sector_etf"], sector_etf)
            self.assertIn(f'id="hypothesis-{symbol.lower()}-setup"', source)
            self.assertIn(
                f'data-desk-catalyst="{catalyst}" data-desk-catalyst-name="{catalyst_name}"',
                source,
            )
            self.assertEqual(set(valuations[symbol]["entry_levels"]), {"bear", "base", "bull"})
            self.assertEqual(universe[symbol]["sector"], scan_sector)
            self.assertEqual(charts[symbol]["sector_etf"], sector_etf)
            self.assertEqual(charts[symbol]["series"]["dates"][-1], scan["last_bar"])
            self.assertEqual(long_history["charts"][symbol]["dates"][-1], long_history["as_of"])

    def test_intu_live_holding_has_exact_canonical_owners(self):
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        valuations = json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"]
        scan = json.loads((ROOT / "trading" / "scan-universe.json").read_text())
        charts = json.loads((ROOT / "trading" / "scan-charts.json").read_text())["charts"]
        long_history = json.loads((ROOT / "trading" / "hypothesis-charts.json").read_text())
        universe = {row["symbol"]: row for row in scan["rows"]}

        self.assertEqual(profiles["INTU"]["flair"], "thesis")
        self.assertEqual(profiles["INTU"]["sector"], "Technology")
        self.assertEqual(profiles["INTU"]["sector_etf"], "XLK")
        self.assertIn('id="hypothesis-intu-setup"', source)
        self.assertIn(
            'data-desk-catalyst="2026-09-17" data-desk-catalyst-name="Confirmed Investor Day"',
            source,
        )
        self.assertIn("Intuit reported fiscal Q4 on August 25", source)
        self.assertIn("Fiscal Q4 revenue rose <strong>14% to $4.4B</strong>", source)
        self.assertIn("<strong>9%–10%</strong> total revenue growth", source)
        self.assertEqual(valuations["INTU"]["entry_levels"], {"bear": 253.95, "base": 361.87, "bull": 709.24})
        self.assertEqual(universe["INTU"]["sector"], "Technology")
        self.assertEqual(charts["INTU"]["sector_etf"], "XLK")
        self.assertEqual(charts["INTU"]["series"]["dates"][-1], scan["last_bar"])
        self.assertEqual(long_history["charts"]["INTU"]["dates"][-1], long_history["as_of"])

    def test_app_live_holding_has_exact_canonical_owners(self):
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        valuations = json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"]
        scan = json.loads((ROOT / "trading" / "scan-universe.json").read_text())
        charts = json.loads((ROOT / "trading" / "scan-charts.json").read_text())["charts"]
        long_history = json.loads((ROOT / "trading" / "hypothesis-charts.json").read_text())
        universe = {row["symbol"]: row for row in scan["rows"]}

        self.assertEqual(profiles["APP"]["flair"], "thesis")
        self.assertEqual(profiles["APP"]["sector"], "Technology")
        self.assertEqual(profiles["APP"]["sector_etf"], "XLK")
        self.assertIn('id="hypothesis-app-setup"', source)
        self.assertIn(
            'data-desk-catalyst="2026-11-04" data-desk-catalyst-name="Est. Q3 earnings"',
            source,
        )
        self.assertIn("AppLovin has not confirmed the date", source)
        self.assertEqual(valuations["APP"]["entry_levels"], {"bear": 298.59, "base": 298.59, "bull": 733.6})
        self.assertEqual(universe["APP"]["sector"], "Technology")
        self.assertEqual(charts["APP"]["sector_etf"], "XLK")
        self.assertEqual(charts["APP"]["series"]["dates"][-1], scan["last_bar"])
        self.assertEqual(long_history["charts"]["APP"]["dates"][-1], long_history["as_of"])

    def test_rtx_live_holding_has_exact_canonical_owners(self):
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        valuations = json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"]
        scan = json.loads((ROOT / "trading" / "scan-universe.json").read_text())
        charts = json.loads((ROOT / "trading" / "scan-charts.json").read_text())["charts"]
        long_history = json.loads((ROOT / "trading" / "hypothesis-charts.json").read_text())["charts"]
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
        self.assertEqual(long_history["RTX"]["dates"][-1], scan["last_bar"])

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
