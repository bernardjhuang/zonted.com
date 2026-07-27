#!/usr/bin/env python3
"""Regression checks for the generated /trading decision surface."""
from __future__ import annotations

import json
import hashlib
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "trading" / "classic" / "index.html"
DESK_HOME = ROOT / "trading" / "index.html"
HYPOTHESES_ROUTE = ROOT / "trading" / "hypotheses" / "index.html"
JS = ROOT / "js" / "trading-broker-light.js"
RESULTS = ROOT / "trading" / "results-ytd.json"
RISK = ROOT / "trading" / "risk-ytd.json"
RISK_JS = ROOT / "js" / "trading-risk.js"
RISK_CSS = ROOT / "css" / "trading-risk.css"
GROK_BRIEF = ROOT / "trading" / "grok-brief.json"


class TradingUiContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = PAGE.read_text()
        cls.js = JS.read_text()
        cls.results = json.loads(RESULTS.read_text())
        cls.risk = json.loads(RISK.read_text())
        cls.grok_brief = json.loads(GROK_BRIEF.read_text())

    def test_answer_first_tabs(self):
        tabs = re.findall(r'<button class="trading-tab" id="([^"]+)-tab"[^>]*>(.*?)</button>', self.html, re.S)
        self.assertEqual([name for name, _ in tabs], ["positions", "hypotheses", "brief", "grok-brief", "scan", "vwap", "crypto", "risk", "results"])
        labels = [" ".join(re.sub(r"<[^>]+>", "", body).split()) for _, body in tabs]
        self.assertEqual(labels[0], "Portfolio")
        self.assertRegex(labels[1], r"^Hypotheses \d+$")
        self.assertEqual(labels[2], "Brief")
        self.assertEqual(labels[3], "Grok brief")
        self.assertRegex(labels[4], r"^Momentum \d+$")
        self.assertEqual(labels[5:], ["VWAP", "Crypto", "Risk", "Performance"])
        self.assertNotIn('id="log-tab"', self.html)

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
        self.assertIn('aria-label="Trading mentality reminders"', home)

    def test_grok_brief_is_cross_agency_and_matches_json(self):
        block_match = re.search(r'<!-- AUTO:GROK_BRIEF:START -->(.*?)<!-- AUTO:GROK_BRIEF:END -->', self.html, re.S)
        self.assertIsNotNone(block_match)
        block = block_match.group(1) if block_match else ""
        theses = self.grok_brief["theses"]
        self.assertIn('id="grok-brief-shell"', block)
        self.assertIn('/trading/grok-brief.json?v=', block)
        script_version = hashlib.sha256((ROOT / "js" / "trading-grok-brief.js").read_bytes()).hexdigest()[:12]
        data_version = hashlib.sha256(GROK_BRIEF.read_bytes()).hexdigest()[:12]
        self.assertIn(f'/js/trading-grok-brief.js?v={script_version}', self.html)
        self.assertIn(f'/trading/grok-brief.json?v={data_version}', block)
        self.assertEqual(self.grok_brief["scope"], "cross-agency-grok-brief-theses")
        self.assertIn("06:30", self.grok_brief["cadence"])
        self.assertLessEqual(len(theses), 10)
        self.assertGreaterEqual(len(self.grok_brief["agencies_scanned"]), 5)
        agencies = {row["agency"] for row in theses}
        self.assertGreaterEqual(len(agencies), 4)
        self.assertLessEqual(sum(row["agency"] == "FDA" for row in theses), 4)
        self.assertGreaterEqual(sum(row["narrative_stage"] == "early" for row in theses), 1)
        self.assertEqual(len({row["id"] for row in theses}), len(theses))
        self.assertTrue(all(row["primary_tickers"] for row in theses))
        self.assertTrue(all(len(row["catalyst_chain"]) >= 3 for row in theses))
        self.assertTrue(all(row["what_happened"] and row["transmission"] and row["asymmetry"] for row in theses))
        self.assertTrue(all(row["sources"] for row in theses))
        grok_brief_js = (ROOT / "js" / "trading-grok-brief.js").read_text()
        self.assertIn('6:30 AM CT trading days', grok_brief_js)
        self.assertIn('Catalyst chain', grok_brief_js)
        self.assertIn('Transmission:', grok_brief_js)
        self.assertIn('Asymmetry:', grok_brief_js)

    def test_hypotheses_are_explicit_and_scannable(self):
        hypotheses_html = HYPOTHESES_ROUTE.read_text()
        self.assertEqual(hypotheses_html.count('class="hypothesis-detail"'), 11)
        details = {
            symbol.upper(): block
            for symbol, block in re.findall(
                r'<article class="hypothesis-detail" id="hypothesis-([a-z]+)-setup"(.*?)</article>',
                hypotheses_html,
                re.S,
            )
        }
        self.assertEqual(set(details), {"ABT", "BYDDY", "CEG", "FIGR", "HIMS", "HOOD", "HPQ", "NTDOY", "RDDT", "RBLX", "TMO"})
        self.assertEqual(hypotheses_html.count('class="hypothesis-status"'), 11)
        self.assertIn('<span class="hypothesis-status">Unfolded · thesis only</span>', details["HIMS"])
        self.assertIn('<strong>No position.</strong>', details["HIMS"])
        self.assertIn('<h4>Watch plan</h4>', details["HIMS"])
        for symbol, block in details.items():
            self.assertIn(f'id="hypothesis-{symbol.lower()}-setup"', hypotheses_html)
            self.assertIn(f'href="/trading/watchlist/?chart={symbol}#scan"', block)
            self.assertEqual(block.count('data-thesis-scan="benefit"'), 1, symbol)
            self.assertEqual(block.count('data-thesis-scan="threat"'), 1, symbol)
        hypotheses_route = HYPOTHESES_ROUTE.read_text()
        for symbol in details:
            self.assertIn(f'href="/trading/watchlist/?chart={symbol}#scan"', hypotheses_route)
        route_details = re.findall(r'class="hypothesis-detail"\s+id="hypothesis-[a-z0-9-]+-setup"', hypotheses_route)
        self.assertEqual(hypotheses_route.count('class="hypothesis-chart-link"'), len(route_details))
        self.assertIn('Exact Sciences', details["ABT"])
        self.assertIn('Libre Assist', details["ABT"])
        self.assertIn('Slightly underpriced', details["HOOD"])
        self.assertIn('$940–980B', details["HOOD"])
        self.assertIn('$69.1B', details["HOOD"])
        self.assertIn('Monthly operating metrics', details["HOOD"])
        self.assertIn('June 2026 month-to-date trading update', details["HOOD"])
        self.assertIn('403,472 June NEV sales', details["BYDDY"])
        self.assertIn('175,349 exports', details["BYDDY"])
        self.assertIn('humanoid development', details["BYDDY"])
        self.assertIn('July production and sales volume', details["BYDDY"])
        self.assertIn('19.86M Switch 2 units', details["NTDOY"])
        self.assertIn('16.50M units', details["NTDOY"])
        self.assertIn('August 6, 2026', details["NTDOY"])
        self.assertIn('$449.99 to $499.99', details["NTDOY"])
        self.assertIn('35% to 132M', details["RBLX"])
        self.assertIn('monetized over 50% better', details["RBLX"])
        self.assertIn('July 30, 2026', details["RBLX"])
        self.assertIn('$596M', details["RBLX"])
        self.assertIn('55 GW', details["CEG"])
        self.assertIn('1,121 MW', details["CEG"])
        self.assertIn('August 6, 2026', details["CEG"])
        self.assertIn('$11.00–$12.00', details["CEG"])
        self.assertIn('69% to $663M', details["RDDT"])
        self.assertIn('126.8M', details["RDDT"])
        self.assertIn('July 30, 2026', details["RDDT"])
        self.assertIn('$715–725M', details["RDDT"])
        self.assertIn('Open position · profitable fintech', details["FIGR"])
        self.assertIn('record loan volume', details["FIGR"])
        self.assertIn('Open position · cash-yield value', details["HPQ"])
        self.assertIn('AI-PC refresh', details["HPQ"])
        self.assertIn('5% organic growth', details["TMO"])
        self.assertIn('$1.68B', details["TMO"])
        self.assertIn('October 21, 2026', details["TMO"])
        self.assertIn('$193 bear / $275 base / $378 bull', details["TMO"])

    def test_hypothesis_source_metadata_feeds_the_merged_desk(self):
        hypotheses_route = HYPOTHESES_ROUTE.read_text()
        articles = re.findall(r'<article class="hypothesis-detail" id="hypothesis-([a-z0-9.-]+)-setup"([^>]*)>', hypotheses_route)
        self.assertEqual(len(articles), 11)
        self.assertEqual(
            {symbol.upper() for symbol, _attrs in articles},
            {"ABT", "BYDDY", "CEG", "FIGR", "HIMS", "HOOD", "HPQ", "NTDOY", "RDDT", "RBLX", "TMO"},
        )
        for symbol, attrs in articles:
            self.assertRegex(attrs, r'data-desk-catalyst="\d{4}-\d{2}-\d{2}"', symbol)
            self.assertRegex(attrs, r'data-desk-trigger="[^"]+"', symbol)
            self.assertRegex(attrs, r'data-desk-stance="(constructive|speculative|research-only|open-position)"', symbol)

        desk = DESK_HOME.read_text()
        self.assertEqual(desk.count('data-desk-kind="position"'), 6)
        self.assertEqual(desk.count('data-desk-kind="hypothesis"'), 5)
        self.assertIn('data-desk-source-articles="11"', desk)
        self.assertIn('/trading/hypotheses/#hypothesis-hood-setup', desk)
        self.assertIn('data-thesis-source="/trading/hypotheses/"', desk)

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
        self.assertIn('Positive outcomes', block)
        self.assertIn('Last 30 days', block)
        self.assertRegex(block, r'Current (wins|losses|none) streak')
        self.assertIn('Quantities and dollar amounts are ignored', block)
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
        for forbidden in ('$', 'balance', 'buying power', 'position', 'trade'):
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

    def test_forward_risk_dashboard_contract(self):
        block = re.search(r'<!-- AUTO:RISK:START -->(.*?)<!-- AUTO:RISK:END -->', self.html, re.S)
        self.assertIsNotNone(block)
        self.assertIn('id="risk-panel"', block.group(1) if block else "")
        self.assertIn('/css/trading-risk.css?', self.html)
        self.assertIn('/js/trading-risk.js?', self.html)
        digest = hashlib.sha256(RISK.read_bytes()).hexdigest()[:12]
        self.assertEqual(self.html.count(f'/trading/risk-ytd.json?v={digest}'), 2)
        self.assertIn(f'/js/trading-risk.js?v={hashlib.sha256(RISK_JS.read_bytes()).hexdigest()[:12]}', self.html)
        self.assertIn(f'/css/trading-risk.css?v={hashlib.sha256(RISK_CSS.read_bytes()).hexdigest()[:12]}', self.html)
        self.assertIn('bindChartInteractions', RISK_JS.read_text())
        self.assertIn('risk-chart-tooltip', RISK_JS.read_text())
        self.assertIn('.risk-chart-tooltip', RISK_CSS.read_text())
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
        self.assertIn("Full Brier receipt", RISK_JS.read_text())
        self.assertIn("S&P 500 (SPY)", RISK_JS.read_text())
        self.assertIn("comparison_start", RISK_JS.read_text())
        self.assertIn("Conditions Score", RISK_JS.read_text())
        self.assertIn("Historical outcome frequencies", RISK_JS.read_text())
        self.assertIn("constant-maturity", RISK_JS.read_text())
        self.assertIn("VIX9D / VIX", RISK_JS.read_text())
        self.assertIn("stale · zero weight", RISK_JS.read_text())
        self.assertGreaterEqual(len(self.risk["commentary"]), 3)
        self.assertLessEqual(len(self.risk["commentary"]), 5)

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
        # Thesis copy stays server-rendered for no-JS access; charts remain external.
        self.assertLess(PAGE.stat().st_size, 300_000)
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
        self.assertIn("ENTER+", labels)
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

    def test_live_setups_collapsed_and_recent_activity_folded(self):
        combined_pnl_rows = re.findall(r'<li class="ticker" data-symbol-pnl="([^"]+)"><span class="ticker-symbol">([^<]+)</span>', self.html)
        self.assertGreaterEqual(len(combined_pnl_rows), 6)
        self.assertGreaterEqual(len({symbol for _, symbol in combined_pnl_rows}), 3)
        for symbol in {symbol for _, symbol in combined_pnl_rows}:
            values = {value for value, row_symbol in combined_pnl_rows if row_symbol == symbol}
            self.assertEqual(len(values), 1, symbol)
            self.assertRegex(next(iter(values)), r"^[+−]\d+\.\d%$")
        self.assertIn('aria-expanded="false" aria-controls="${detailId}"', self.js)
        self.assertIn('>View setup</button>', self.js)
        self.assertIn('data-position-symbol="${symbol}" hidden>', self.js)
        self.assertIn("renderSetupChartForSymbol($('[data-position-chart-shell]', detail)", self.js)
        self.assertIn("const combinedPnl = t.dataset.symbolPnl || '—';", self.js)
        self.assertIn('Monitor FDA’s formal peptide-action schedule and the next PCAC meeting date', self.js)
        self.assertIn('Wait for HIMS to sink below $25 before adding.', self.js)
        self.assertIn('#positions-panel .portfolio-grid { grid-template-columns: 1fr; }', self.html)
        self.assertRegex(self.js, r'<article class="portfolio-card[\s\S]*?<div class="bl-position-chart-detail[\s\S]*?</article>')
        self.assertNotIn('class="portfolio-details"', self.js)
        self.assertIn('.slice(0, 20)', self.js)
        self.assertIn('<details class="bl-card activity-disclosure">', self.js)
        self.assertIn('direction / type / P&amp;L', self.js)
        self.assertEqual(self.html.count('class="activity-row"'), 40)

    def test_desk_pages_share_one_nav_and_stamp(self):
        """Guard against multi-agent drift: every routed desk page must carry the
        same nav link set (hrefs and labels), stamp format, and current desk assets."""
        import glob
        pages = [p for p in glob.glob(str(ROOT / "trading" / "*" / "index.html"))
                 if "classic" not in p and "charts" not in p and '<nav class="subnav"' in pathlib.Path(p).read_text()] + [str(ROOT / "trading" / "index.html")]
        nav_sets, stamps, chips = set(), set(), set()
        css_hash = hashlib.sha256((ROOT / "trading" / "desk.css").read_bytes()).hexdigest()[:12]
        js_hash = hashlib.sha256((ROOT / "trading" / "desk.js").read_bytes()).hexdigest()[:12]
        for p in pages:
            s = pathlib.Path(p).read_text()
            nav = s[s.find("subnav"):s.find("</nav>")]
            nav_sets.add(tuple(re.findall(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', nav)))
            m = re.search(r'class="stamp">([^<]+)<', s)
            chip = re.search(r'<span class="chipset">.*?</span></a></span>', s)
            chips.add(chip.group(0) if chip else "missing")
            stamps.add(re.sub(r"[A-Z][a-z]+ \d{1,2}, \d{4}", "<date>", m.group(1)) if m else "missing")
            self.assertIn(f'/trading/desk.css?v={css_hash}', s, p)
            self.assertIn(f'/trading/desk.js?v={js_hash}', s, p)
        self.assertEqual(len(nav_sets), 1, f"{len(nav_sets)} different nav sets across desk pages")
        self.assertEqual(len(stamps), 1, f"stamp formats diverge: {stamps}")
        self.assertEqual(len(chips), 1, "status chipset diverges across desk pages")
        hrefs = [h for h, _ in next(iter(nav_sets))]
        self.assertEqual(len(hrefs), len(set(hrefs)), "duplicate nav hrefs")
        self.assertNotIn("/trading/hypotheses/", hrefs)
        self.assertTrue(HYPOTHESES_ROUTE.exists(), "canonical hypotheses source route must remain available")



if __name__ == "__main__":
    unittest.main(verbosity=2)
