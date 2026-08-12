#!/usr/bin/env python3
"""Regression checks for the generated /trading decision surface."""
from __future__ import annotations

import json
import hashlib
import os
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "trading" / "pipeline.html"
DESK_HOME = ROOT / "trading" / "index.html"
HYPOTHESES_SOURCE = ROOT / "trading" / "hypothesis-source.txt"
JS = ROOT / "js" / "trading-broker-light.js"
RESULTS = ROOT / "trading" / "results-ytd.json"
RISK = ROOT / "trading" / "risk-ytd.json"


class TradingUiContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text()
        cls.js = JS.read_text()
        cls.results = json.loads(RESULTS.read_text())
        cls.risk = json.loads(RISK.read_text())

    def test_pipeline_contains_only_live_route_regions(self):
        markers = set(re.findall(r"<!-- AUTO:([A-Z_]+):START -->", self.html))
        self.assertEqual(markers, {"SCAN", "VWAP", "CRYPTO", "RESULTS"})
        for stale in ("ROBINHOOD", "TRADES", "HYPOTHESES", "BRIEF", "GROK_BRIEF", "RISK"):
            self.assertNotIn(f"AUTO:{stale}", self.html)
        self.assertFalse((ROOT / "trading" / "classic").exists())
        self.assertFalse((ROOT / "trading" / "brief").exists())
        public_routes = {
            path.parent.name
            for path in (ROOT / "trading").glob("*/index.html")
        }
        self.assertEqual(
            public_routes,
            {"themes", "vwap-setups", "momentum", "mentality", "performance", "autonomous", "autonomous-psy", "gpt-risk", "grok-risk", "fable-risk"},
        )

    def test_deploy_checks_the_active_desk_cadence(self):
        workflow = (ROOT / ".github" / "workflows" / "deploy.yml").read_text()
        self.assertIn('<span class=\\"stamp\\">Live ·', workflow)
        self.assertIn("export ZONTED_DESK_MORNING_QUOTES=trading/desk-morning-quotes.json", workflow)
        self.assertIn('build-trading-desk.py --mode morning --quotes "$ZONTED_DESK_MORNING_QUOTES" --check', workflow)
        self.assertIn("build-trading-desk.py --mode close --check", workflow)

    def test_gpt_brief_is_slack_only(self):
        self.assertNotIn("AUTO:GPT_BRIEF", self.html)
        self.assertNotIn('id="gpt-brief-tab"', self.html)
        self.assertNotIn('/trading/gpt-brief/', self.html)
        self.assertFalse((ROOT / "trading" / "gpt-brief.json").exists())
        self.assertFalse((ROOT / "trading" / "gpt-brief-charts.json").exists())
        self.assertFalse((ROOT / "js" / "trading-gpt-brief.js").exists())

    def test_trading_home_has_no_needs_attention_block(self):
        home = (ROOT / "trading" / "index.html").read_text()
        self.assertNotIn("Needs attention", home)
        self.assertNotIn('class="alert"', home)
        self.assertNotIn('aria-label="Trading mentality reminders"', home)
        self.assertNotIn('id="market-overview-live"', home)


    def test_hypotheses_are_explicit_and_scannable(self):
        hypotheses_html = HYPOTHESES_SOURCE.read_text()
        expected_symbols = set(json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"])
        self.assertEqual(hypotheses_html.count('class="hypothesis-detail"'), len(expected_symbols))
        details = {
            symbol.upper(): block
            for symbol, block in re.findall(
                r'<article class="hypothesis-detail" id="hypothesis-([a-z]+)-setup"(.*?)</article>',
                hypotheses_html,
                re.S,
            )
        }
        self.assertEqual(set(details), expected_symbols)
        self.assertNotIn("PG", details)
        self.assertEqual(hypotheses_html.count('class="hypothesis-status"'), len(expected_symbols))
        self.assertIn('<span class="hypothesis-status">Unfolded · thesis only</span>', details["HIMS"])
        self.assertIn('<strong>No position.</strong>', details["HIMS"])
        self.assertIn('<h4>Watch plan</h4>', details["HIMS"])
        for symbol, block in details.items():
            self.assertIn(f'id="hypothesis-{symbol.lower()}-setup"', hypotheses_html)
            self.assertIn(f'href="/trading/vwap-setups/?chart={symbol}#scan"', block)
            self.assertEqual(block.count('data-thesis-scan="benefit"'), 1, symbol)
            self.assertEqual(block.count('data-thesis-scan="threat"'), 1, symbol)
        hypotheses_route = HYPOTHESES_SOURCE.read_text()
        for symbol in details:
            self.assertIn(f'href="/trading/vwap-setups/?chart={symbol}#scan"', hypotheses_route)
        route_details = re.findall(r'class="hypothesis-detail"\s+id="hypothesis-[a-z0-9-]+-setup"', hypotheses_route)
        self.assertEqual(hypotheses_route.count('class="hypothesis-chart-link"'), len(route_details))

        self.assertIn('thesis play on gyms becoming social clubs', details["LTH"])
        self.assertIn('wellness third place', details["LTH"])
        self.assertIn('Life Time 2025 Form 10-K', details["LTH"])
        self.assertIn('November 3', details["LTH"])
        self.assertIn('Current market value is published only as a rounded percentage', details["LTH"])
        self.assertIn('Slightly underpriced', details["HOOD"])
        self.assertIn('$940–980B', details["HOOD"])
        self.assertIn('$69.1B', details["HOOD"])
        self.assertIn('Monthly operating metrics', details["HOOD"])
        self.assertIn('June 2026 month-to-date trading update', details["HOOD"])
        for retired in ("ABT", "HPQ", "JBS", "NTDOY", "ZM"):
            self.assertNotIn(retired, details)
        self.assertIn('35% to 132M', details["RBLX"])
        self.assertIn('monetized over 50% better', details["RBLX"])
        self.assertIn('October 29, 2026', details["RBLX"])
        self.assertIn('$596M', details["RBLX"])
        self.assertIn('$6.62B, up 13%', details["ADBE"])
        self.assertIn('AI-first ARR', details["ADBE"])
        self.assertIn('$190.12 bear / $260.24 base / $370.86 bull', details["ADBE"])
        self.assertIn('No live position assumed', details["ADBE"])
        self.assertIn('55 GW', details["CEG"])
        self.assertIn('1,121 MW', details["CEG"])
        self.assertIn('November 6, 2026', details["CEG"])
        self.assertIn('$11.00–$12.00', details["CEG"])
        self.assertIn('69% to $663M', details["RDDT"])
        self.assertIn('126.8M', details["RDDT"])
        self.assertIn('October 29, 2026', details["RDDT"])
        self.assertIn('$715–725M', details["RDDT"])
        self.assertIn('Open position · profitable fintech', details["FIGR"])
        self.assertIn('record loan volume', details["FIGR"])
        self.assertIn('elite business, extreme expectations', details["NET"])
        self.assertIn('$37 bear / $61 base / $108 bull', details["NET"])
        self.assertIn('40.3% annual revenue growth', details["NET"])
        self.assertIn('net-dcf-2026-07-29.xlsx', details["NET"])
        self.assertIn('October 29, 2026', details["NET"])
        self.assertIn('5% organic growth', details["TMO"])
        self.assertIn('$1.68B', details["TMO"])
        self.assertIn('October 21, 2026', details["TMO"])
        self.assertIn('$193 bear / $275 base / $378 bull', details["TMO"])
        self.assertIn('data-desk-catalyst="2026-11-10"', details["CRWV"])
        self.assertIn('data-desk-catalyst-name="Est. Q3 earnings"', details["CRWV"])
        self.assertIn('$2.575B', details["CRWV"])
        self.assertIn('$104B', details["CRWV"])
        self.assertIn('$640M', details["CRWV"])
        self.assertIn('more than $25B of net new customer commitments', details["CRWV"])
        profiles = json.loads((ROOT / "trading" / "desk-position-profiles.json").read_text())["profiles"]
        self.assertEqual(profiles["CRWV"]["next_catalyst"], "Est. Q3 earnings Nov 10")
        self.assertIn('Open position · Ethereum thesis', details["BMNR"])
        self.assertIn('$16.33 bear / $18.10 base / $24.98 bull', details["BMNR"])
        self.assertIn('5,805,238 ETH', details["BMNR"])
        self.assertIn('January 15, 2027 $20 calls', details["BMNR"])
        self.assertIn('estimated August 17, 2026', details["BMNR"])
        self.assertIn('Robinhood Chain is an Ethereum Layer 2', details["BMNR"])
        self.assertIn('President Trump\'s family received more than $1.4B', details["BMNR"])
        self.assertIn('Web3 valuations as depressed', details["BMNR"])
        self.assertEqual(profiles["BMNR"]["flair"], "thesis")
        self.assertEqual(profiles["BMNR"]["kill"], 16.33)
        self.assertIn('Open position · starter-size AI water-infrastructure thesis · through January 2027 call expiry', details["XYL"])
        self.assertIn('<strong>Small equity position plus January 15, 2027 $125 calls.</strong>', details["XYL"])
        self.assertIn('$3.1B, up 42% reported and 41% organically', details["XYL"])
        self.assertIn('$64.07 bear / $83.59 base / $124.57 bull', details["XYL"])
        self.assertIn('estimated October 27, 2026', details["XYL"])
        self.assertIn('Xylem data-center water solutions', details["XYL"])
        self.assertEqual(profiles["XYL"]["flair"], "thesis")
        self.assertIsNone(profiles["XYL"]["kill"])
        self.assertIn('Open position · momentum', details["MDB"])
        self.assertIn('$334 bear / $374 base / $445 bull', details["MDB"])
        self.assertIn('25% to $687.6M', details["MDB"])
        self.assertIn('August 28 $400 calls', details["MDB"])
        self.assertIn('August 25, 2026', details["MDB"])
        self.assertEqual(profiles["MDB"]["flair"], "momentum")
        self.assertEqual(profiles["MDB"]["kill"], 333.6)

    def test_hypothesis_source_metadata_feeds_the_merged_desk(self):
        hypotheses_route = HYPOTHESES_SOURCE.read_text()
        expected_symbols = set(json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"])
        articles = re.findall(r'<article class="hypothesis-detail" id="hypothesis-([a-z0-9.-]+)-setup"([^>]*)>', hypotheses_route)
        self.assertEqual(len(articles), len(expected_symbols))
        self.assertEqual({symbol.upper() for symbol, _attrs in articles}, expected_symbols)
        completed_session = json.loads((ROOT / "trading" / "market-ytd.json").read_text())["as_of"]
        for symbol, attrs in articles:
            self.assertRegex(attrs, r'data-desk-catalyst="\d{4}-\d{2}-\d{2}"', symbol)
            catalyst_match = re.search(r'data-desk-catalyst="(\d{4}-\d{2}-\d{2})"', attrs)
            if catalyst_match is None:
                self.fail(f"{symbol} catalyst date is missing")
            catalyst_date = catalyst_match.group(1)
            self.assertGreater(catalyst_date, completed_session, f"{symbol} catalyst is not after the latest completed session")
            self.assertRegex(attrs, r'data-desk-trigger="[^"]+"', symbol)
            self.assertRegex(attrs, r'data-desk-stance="(constructive|speculative|research-only|open-position)"', symbol)

        desk = DESK_HOME.read_text()
        position_count = len(json.loads((ROOT / "trading" / "desk-positions.json").read_text())["positions"])
        self.assertEqual(desk.count('data-desk-kind="position"'), position_count)
        self.assertEqual(desk.count('data-desk-kind="hypothesis"'), len(expected_symbols) - position_count)
        self.assertIn(f'data-desk-source-articles="{len(expected_symbols)}"', desk)
        source_hash = hashlib.sha256(HYPOTHESES_SOURCE.read_bytes()).hexdigest()[:12]
        self.assertIn(f'data-thesis-source="/trading/hypothesis-source.txt?v={source_hash}"', desk)
        self.assertEqual(desk.count('class="desk-thesis-cell-button"'), len(expected_symbols))
        self.assertIn("Current holdings are reconciled on the Desk.", hypotheses_route)
        self.assertNotIn("Six are live positions.", hypotheses_route)

    def test_results_is_quantity_free_with_outcome_stats(self):
        match = re.search(r'<!-- AUTO:RESULTS:START -->(.*?)<!-- AUTO:RESULTS:END -->', self.html, re.S)
        self.assertIsNotNone(match)
        block = match.group(1) if match else ""
        self.assertRegex(block, r'<h2 id="results-heading">[+−]\d+\.\d{2}%</h2>')
        self.assertIn('Robinhood · YTD', block)
        self.assertIn('YTD portfolio performance', block)
        self.assertIn('class="results-chart"', block)
        self.assertIn('Daily EOD snapshots', block)
        self.assertIn('Quantity-free YTD outcome statistics', block)
        self.assertEqual(
            re.findall(r'<span>(Last \d+ days)</span>', block),
            ['Last 7 days', 'Last 30 days', 'Last 90 days'],
        )
        self.assertLess(block.index('class="results-chart"'), block.index('class="results-stats"'))
        self.assertNotRegex(block, r'Current (wins|losses|none) streak')
        self.assertNotIn('Longest win', block)
        self.assertIn('Private quantities and dollar amounts are never published', block)
        stats = re.search(
            r'data-results-wins="(\d+)" data-results-losses="(\d+)" '
            r'data-results-breakevens="(\d+)" data-results-decided="(\d+)" '
            r'data-results-win-rate="([\d.]+)"',
            block,
        )
        if stats is None:
            self.fail("quantity-free results data attributes are missing")
        wins, losses, _breakevens, decided = map(int, stats.groups()[:4])
        win_rate = float(stats.group(5))
        self.assertEqual(decided, wins + losses)
        self.assertAlmostEqual(win_rate, wins / decided * 100, places=1)
        self.assertIn('class="performance-actions"', block)
        self.assertIn('Last 14 days', block)
        action_items = re.findall(r'<li class="performance-action(?: performance-action--(?:win|loss))?" data-performance-side="(buy|sell)" data-performance-type="(stock|option)" data-performance-symbol="([A-Z][A-Z0-9.\-]{0,9})" data-performance-date="(\d{4}-\d{2}-\d{2})">(.*?)</li>', block, re.S)
        self.assertTrue(action_items)
        for side, asset_type, symbol, action_date, item in action_items:
            self.assertIn(f'<b>{symbol}</b> · {side.title()} · {asset_type.title()}', item)
            self.assertIn(f'<time datetime="{action_date}">', item)
            self.assertRegex(item, r'<strong class="(?:positive|negative)">[+−][\d.]+%</strong>|<strong class="">—</strong>')
        self.assertRegex(block, r'class="performance-action performance-action--win" data-performance-side="sell"[\s\S]*?<strong class="positive">')
        self.assertRegex(block, r'class="performance-action performance-action--loss" data-performance-side="sell"[\s\S]*?<strong class="negative">')
        self.assertIn(".performance-action-list{display:grid;grid-template-columns:1fr", (ROOT / "trading" / "desk.css").read_text())
        for forbidden in ('$', 'balance', 'buying power', 'account number', 'order id'):
            self.assertNotIn(forbidden, block.casefold())

    def test_results_history_is_unique_ordered_and_matches_chart(self):
        points = self.results["points"]
        dates = [row["date"] for row in points]
        self.assertTrue(points)
        self.assertEqual(dates, sorted(set(dates)))
        self.assertEqual(self.results["year"], int(dates[-1][:4]))
        match = re.search(r'<h2 id="results-heading">([+−]\d+\.\d{2}%)</h2>', self.html)
        self.assertIsNotNone(match)
        latest = f"{float(points[-1]['ytd_percent']):+.2f}%".replace("-", "−")
        self.assertEqual(match.group(1) if match else "", latest)
        self.assertIn(f'data-results-points="{len(points)}"', self.html)

    def test_forward_risk_data_contract(self):
        current = self.risk["current"]
        score = self.risk["score"]
        self.assertEqual(self.risk["schema_version"], 2)
        self.assertAlmostEqual(score["total"], sum(row["points"] for row in score["components"].values()), places=2)
        self.assertAlmostEqual(sum(row["maximum"] for row in score["components"].values()), 100, places=2)
        self.assertAlmostEqual(current["curve_spread"], current["m2"] - current["m1"], places=4)
        self.assertIn("positive slope means contango", self.risk["method"])
        self.assertEqual([row["label"] for row in self.risk["curve"]], ["Spot", "M1", "M2", "M3", "M4", "M5", "M6"])
        self.assertGreater(len(self.risk["history"]["score"]), 2_500)
        self.assertEqual(self.risk["conditional_frequencies"]["horizons"], [21, 42])
        self.assertEqual(self.risk["model_status"]["status"], "withheld")
        self.assertEqual(self.risk["model_status"]["endpoints_passed"], 0)
        self.assertEqual(self.risk["model_status"]["endpoints_total"], 4)
        self.assertIsNone(self.risk["model_status"]["live_probabilities"])
        self.assertGreaterEqual(len(self.risk["commentary"]), 3)
        self.assertLessEqual(len(self.risk["commentary"]), 5)
        self.assertNotIn("AUTO:RISK", self.html)
        self.assertFalse((ROOT / "js" / "trading-risk.js").exists())
        self.assertFalse((ROOT / "css" / "trading-risk.css").exists())

    def test_heading_without_portfolio_tools(self):
        self.assertEqual(len(re.findall(r"<h1\b", self.html)), 1)
        self.assertIn('<h1 class="bl-title">Trading</h1>', self.html)
        self.assertNotIn('id="bl-tools"', self.html)
        self.assertNotIn('id="bl-q"', self.html)
        self.assertNotIn('id="bl-export"', self.html)
        self.assertNotIn("$('#bl-export')", self.js)
        self.assertNotIn('id="bl-filters"', self.html)
        self.assertNotIn("positive mark", self.js)

    def test_legacy_deep_links_survive(self):
        self.assertIn("'#watchlist': '#scan'", self.js)
        self.assertIn("'#log': ''", self.js)

    def test_answer_first_and_progressive_disclosure(self):
        for panel in ("scan", "vwap", "crypto"):
            match = re.search(
                rf'<!-- AUTO:{panel.upper()}:START -->(.*?)<!-- AUTO:{panel.upper()}:END -->',
                self.html,
                re.S,
            )
            self.assertIsNotNone(match, panel)
            block = match.group(1) if match else ""
            self.assertIn('class="trading-takeaway"', block, panel)
            self.assertIn('<details class="trading-method"', block, panel)
        self.assertIn('Short setups ·', self.html)
        self.assertIn('class="scan-qualified-links"', self.html)
        self.assertIn('id="scan-universe"', self.html)
        self.assertIn('<details class="scan-universe-disclosure" id="scan-universe" open>', self.html)
        self.assertIn('<details open><summary>All sectors · 50-day Z-score</summary>', self.html)
        self.assertEqual(self.html.count('class="scan-sector-head"'), 11)
        self.assertEqual(self.html.count('class="scan-sector-score"'), 11)
        self.assertIn('data-universe-sort-day', self.js)
        self.assertIn('data-universe-sort-strength', self.js)
        self.assertIn("let universeSortKey = 'day_pct';", self.js)
        self.assertIn("universeSortKey = nextKey;", self.js)
        self.assertIn('let universeSortDir = -1;', self.js)
        self.assertIn('if (universe.open) loadUniverse();', self.js)
        self.assertNotIn('aria-label="Full momentum scan of the tracked universe"', self.html)

    def test_chart_payloads_are_external_and_small_shell(self):
        # Generated chart payloads stay external; the pipeline buffer is stripped
        # before deploy, so shell-size limits cover only linked public routes.
        for name in ("momentum", "vwap-setups", "performance", "themes"):
            deployed = ROOT / "trading" / name / "index.html"
            self.assertLess(deployed.stat().st_size, 175_000, str(deployed))
        desk_html = DESK_HOME.read_text()
        desk_rows = desk_html.count('class="desk-main-row"')
        position_rows = desk_html.count('data-desk-kind="position"')
        # Position rows carry risk, instrument, level, and one-year-chart data that
        # tracked-hypothesis rows do not. Keep both row classes linearly bounded.
        shell_budget = 90_000 + 4_300 * desk_rows + 1_400 * position_rows
        self.assertLess(DESK_HOME.stat().st_size, shell_budget)
        self.assertNotIn("data-d='", self.html)
        self.assertLess(len(re.findall(r"<svg\b", self.html)), 5)
        for name in ("scan-universe.json", "vwap-charts.json", "crypto-charts.json", "results-ytd.json", "risk-ytd.json"):
            path = ROOT / "trading" / name
            self.assertTrue(path.exists(), name)
            payload = json.loads(path.read_text())
            self.assertTrue(payload, name)

    def test_signal_vocabulary_is_preserved(self):
        universe = json.loads((ROOT / "trading" / "scan-universe.json").read_text())
        labels = {row["signal"] for row in universe["rows"]}
        self.assertTrue(labels)
        self.assertTrue(labels <= {"ENTER+", "ENTER", "WATCH", "AVOID", "NO DATA", "SHORT+", "SHORT", "BREAKING"})
        self.assertIn("<b>ENTER+</b> = qualified", self.html)
        self.assertEqual(universe["schema_version"], 2)
        self.assertEqual(universe["risk_regime"]["as_of"], universe["last_bar"])
        self.assertEqual(universe["risk_regime"]["label"], "Disabled")
        self.assertIsNone(universe["risk_regime"]["score"])
        self.assertEqual(universe["risk_decision_counts"]["none"], len(universe["rows"]))
        self.assertEqual(universe["risk_decision_counts"]["annotate_watchful"], 0)
        self.assertEqual(sum(universe["counts_public"].values()), len(universe["rows"]))
        self.assertTrue(all({"raw_signal", "signal", "risk_decision"} <= set(row) for row in universe["rows"]))
        self.assertTrue(all(row["signal"] == row["raw_signal"] for row in universe["rows"]))
        self.assertIn('class="scan-risk-overlay"', self.html)
        self.assertIn("Subjective risk journal only", self.html)
        self.assertIn("no automated risk gate", self.html)

    def test_performance_trade_tape_hover_lists_ticker_type_and_pnl(self):
        script = (ROOT / "js" / "trading-performance.js").read_text()
        styles = (ROOT / "trading" / "performance-tape.css").read_text()
        self.assertIn('data-trade-detail="1"', script)
        self.assertIn('tabindex="0"', script)
        self.assertIn('role="img"', script)
        self.assertIn('aria-label="${esc(tradeLabel)}"', script)
        self.assertIn("<small>Ticker</small>", script)
        self.assertIn("<small>Type</small>", script)
        self.assertIn("<small>P&amp;L</small>", script)
        self.assertIn("pointermove", script)
        self.assertIn("focusin", script)
        self.assertNotIn("const window = dates", script)
        self.assertIn(".pf-trade:focus-visible", styles)

    def test_performance_trade_log_only_shows_pnl_for_sells(self):
        script = (ROOT / "js" / "trading-performance.js").read_text()
        self.assertIn("a.side === 'sell' && a.pct !== null ? pct(a.pct) : '—'", script)
        self.assertIn("pending sells and buys stay listed as unavailable", script)
        self.assertIn(".filter(a => a.date && a.symbol)", script)
        self.assertIn("a.side === 'sell' && a.pct !== null", script)
        self.assertNotIn("a buy row's number keeps moving", script)

    def test_performance_places_recent_win_rates_below_ytd_hero(self):
        page = (ROOT / "trading" / "performance" / "index.html").read_text()
        script = (ROOT / "js" / "trading-performance.js").read_text()
        styles = (ROOT / "trading" / "performance-tape.css").read_text()
        self.assertNotIn('data-results-sharpe', page)
        self.assertNotIn('results-stat-values', page)
        self.assertNotIn('results-sharpe', page)
        self.assertNotIn('Sharpe', page)
        self.assertNotIn('return samples', page)
        self.assertIn('data-pf-winrates', script)
        self.assertIn("statsNodes.forEach(node => statsHost.appendChild(node))", script)
        self.assertLess(script.index("renderHero(points)"), script.index("data-pf-winrates"))
        self.assertIn("grid-template-columns:repeat(3,minmax(0,1fr))", styles)

    def test_performance_daily_pnl_section_is_removed(self):
        script = (ROOT / "js" / "trading-performance.js").read_text()
        self.assertNotIn("P&amp;L % by day", script)
        self.assertNotIn("const renderDays", script)
        self.assertNotIn("renderDays()", script)

    def test_generated_asset_contracts(self):
        vwap = json.loads((ROOT / "trading" / "vwap-charts.json").read_text())
        crypto = json.loads((ROOT / "trading" / "crypto-charts.json").read_text())
        scan_charts = json.loads((ROOT / "trading" / "scan-charts.json").read_text())
        universe = json.loads((ROOT / "trading" / "scan-universe.json").read_text())
        self.assertEqual(scan_charts["schema_version"], 2)
        self.assertEqual(scan_charts["risk_regime"], universe["risk_regime"])
        self.assertEqual(set(scan_charts["charts"]), {row["symbol"] for row in universe["rows"]})
        self.assertIn("RBLX", scan_charts["charts"])
        self.assertTrue(any(row["symbol"] == "RBLX" for row in universe["rows"]))
        self.assertTrue(all(
            scan_charts["charts"][row["symbol"]]["risk_decision"] == row["risk_decision"]
            for row in universe["rows"]
        ))
        self.assertEqual(len(vwap["charts"]), 23)
        self.assertEqual(len(crypto["charts"]), 7)
        self.assertEqual(vwap["default"], "SPY")
        self.assertEqual(len(vwap["groups"]["us"]), 13)
        self.assertEqual(len(vwap["groups"]["countries"]), 10)
        self.assertIn("ESPO", vwap["groups"]["us"])
        self.assertIn("<span>Gaming</span>", vwap["charts"]["ESPO"])
        self.assertTrue(all('"z50"' in chart for chart in vwap["charts"].values()))
        self.assertTrue(all("50D Z SCORE" in chart and "vwap-z-badge" in chart for chart in vwap["charts"].values()))
        us_z = [json.loads(re.findall(r"data-d='([^']+)'", vwap["charts"][symbol])[0])["z50"][-1]
                for symbol in vwap["groups"]["us"]]
        country_z = [json.loads(re.findall(r"data-d='([^']+)'", vwap["charts"][symbol])[0])["z50"][-1]
                     for symbol in vwap["groups"]["countries"]]
        self.assertEqual(us_z, sorted(us_z, reverse=True))
        self.assertEqual(country_z, sorted(country_z, reverse=True))
        self.assertIn(crypto["default"], crypto["charts"])

    def test_vwap_shows_every_chart_without_picker_controls(self):
        self.assertIn('id="vwap-chart-grid"', self.html)
        self.assertIn('id="vwap-country-chart-grid"', self.html)
        self.assertIn('id="vwap-us-heading">US market + sectors + themes', self.html)
        self.assertIn('id="vwap-countries-heading">Country markets', self.html)
        self.assertLess(self.html.index('id="vwap-chart-grid"'), self.html.index('id="vwap-countries-heading"'))
        self.assertIn('data-url="/trading/vwap-charts.json?', self.html)
        self.assertEqual(self.html.count('>50D Z</th>'), 2)
        self.assertEqual(self.html.count('<th>Market</th><th class="scan-num">50D Z</th>'), 1)
        self.assertEqual(self.html.count('<th>Country</th><th class="scan-num">50D Z</th>'), 1)
        self.assertNotIn('id="vwap-selected-chart"', self.html)
        self.assertNotIn('data-vwap-select', self.html)
        self.assertNotIn('data-vwap-scope-button', self.html)
        self.assertNotIn('data-vwap-scope="countries" hidden', self.html)
        self.assertIn("initChartGallery('#vwap-chart-grid'", self.js)
        self.assertIn("initChartGallery('#vwap-country-chart-grid'", self.js)
        self.assertNotIn("initChartPicker('#vwap-selected-chart'", self.js)

    def test_crypto_shows_every_chart_without_picker_controls(self):
        self.assertIn('id="crypto-chart-grid"', self.html)
        self.assertIn('data-url="/trading/crypto-charts.json?', self.html)
        self.assertNotIn('id="crypto-selected-chart"', self.html)
        self.assertNotIn('data-crypto-select', self.html)
        self.assertIn('>Spread Z vs BTC</th>', self.html)
        self.assertIn("initChartGallery('#crypto-chart-grid'", self.js)

    def test_desk_pages_share_one_nav_and_stamp(self):
        """Guard against multi-agent drift: every routed desk page must carry the
        same nav link set (hrefs and labels), stamp format, and current desk assets."""
        import glob
        pages = [p for p in glob.glob(str(ROOT / "trading" / "*" / "index.html"))
                 if "classic" not in p and "charts" not in p and '<nav class="subnav"' in pathlib.Path(p).read_text()] + [str(ROOT / "trading" / "index.html")]
        nav_sets, stamps, chips = set(), set(), set()
        styles = (ROOT / "trading" / "desk.css").read_text()
        css_hash = hashlib.sha256((ROOT / "trading" / "desk.css").read_bytes()).hexdigest()[:12]
        js_hash = hashlib.sha256((ROOT / "trading" / "desk.js").read_bytes()).hexdigest()[:12]
        css_asset = ROOT / "trading" / f"desk.{css_hash}.css"
        js_asset = ROOT / "trading" / f"desk.{js_hash}.js"
        self.assertEqual(css_asset.read_bytes(), (ROOT / "trading" / "desk.css").read_bytes())
        self.assertEqual(js_asset.read_bytes(), (ROOT / "trading" / "desk.js").read_bytes())
        for p in pages:
            s = pathlib.Path(p).read_text()
            nav = s[s.find("subnav"):s.find("</nav>")]
            nav_sets.add(tuple(re.findall(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', nav)))
            m = re.search(r'class="stamp">([^<]+)<', s)
            chip = re.search(r'<span class="chipset">.*?</span>', s)
            chip_markup = chip.group(0) if chip else "missing"
            chips.add(chip_markup)
            self.assertNotEqual(chip_markup, "missing", p)
            self.assertNotIn('<span class="dot">', chip_markup, p)
            for state, score in re.findall(r'class="chip chip-[^ ]+ chip-(on|off|neutral)"[^>]*>[^<]*?([\d.]+)</a>', chip_markup):
                value = float(score)
                expected = "on" if value > 5 else "off" if value < 5 else "neutral"
                self.assertEqual(state, expected, f"risk pill color mismatch at {value}: {p}")
            stamps.add(re.sub(r"[A-Z][a-z]+ \d{1,2}, \d{4}", "<date>", m.group(1)) if m else "missing")
            self.assertIn(f'/trading/desk.{css_hash}.css', s, p)
            self.assertIn(f'/trading/desk.{js_hash}.js', s, p)
            self.assertNotRegex(s, r'/trading/desk\.(?:css|js)\?v=')
        self.assertEqual(len(nav_sets), 1, f"{len(nav_sets)} different nav sets across desk pages")
        if os.environ.get("ZONTED_DESK_MORNING_QUOTES"):
            live_stamps = {stamp for stamp in stamps if stamp.startswith("Live · ")}
            self.assertEqual(len(live_stamps), 1, f"morning stamp drift: {stamps}")
            self.assertEqual(stamps, live_stamps, f"all nav dates must refresh in morning mode: {stamps}")
        else:
            self.assertEqual(len(stamps), 1, f"stamp formats diverge: {stamps}")
        self.assertNotIn("missing", chips)
        hrefs = [h for h, _ in next(iter(nav_sets))]
        self.assertEqual(len(hrefs), len(set(hrefs)), "duplicate nav hrefs")
        self.assertNotIn("/trading/hypotheses/", hrefs)
        for risk_route in ("grok-risk", "gpt-risk", "fable-risk"):
            self.assertNotIn(f"/trading/{risk_route}/", hrefs)
        for model in ("gpt", "grok", "fable"):
            self.assertIn(f".chip-{model}::before", styles)
            self.assertIn(f"/trading/model-icons/{model}.svg", styles)
            self.assertTrue((ROOT / "trading" / "model-icons" / f"{model}.svg").exists())
        # Retired from the desk risk-chip system only. The SVGs themselves stay:
        # the theme ledger masks them for source provenance (.mi-gemini/.mi-meta),
        # and themes sourced by Gemini or Meta AI are still live.
        themes_page = (ROOT / "trading" / "themes" / "index.html").read_text()
        for retired in ("gemini", "meta"):
            self.assertNotIn(f".chip-{retired}::before", styles)
            self.assertIn(f"/trading/model-icons/{retired}.svg", themes_page)
        for model in ("fable", "gpt", "grok", "gemini", "meta"):
            self.assertIn(f"/trading/model-icons/{model}.svg", themes_page)
            self.assertTrue(
                (ROOT / "trading" / "model-icons" / f"{model}.svg").exists(),
                f"theme provenance icon {model}.svg is referenced but missing",
            )
        self.assertNotIn(".chip .dot", styles)
        self.assertIn("value > 5 ? 'chip-on' : value < 5 ? 'chip-off' : 'chip-neutral'", (ROOT / "trading" / "desk.js").read_text())
        self.assertTrue(HYPOTHESES_SOURCE.exists(), "canonical hypothesis source artifact must remain available")
        self.assertFalse((ROOT / "trading" / "hypotheses").exists(), "retired hypotheses route directory remains")
        redirects = (ROOT / "_redirects").read_text()
        self.assertIn("/trading/hypotheses/* /trading/ 301", redirects)
        self.assertIn("/trading/hypotheses /trading/ 301", redirects)



if __name__ == "__main__":
    unittest.main(verbosity=2)
