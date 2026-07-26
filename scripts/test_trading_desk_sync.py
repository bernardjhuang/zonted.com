#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import unittest

import sync_trading_desk as sync

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLASSIC = (ROOT / "trading" / "classic" / "index.html").read_text()


class RoutedTradingSyncTests(unittest.TestCase):
    def test_all_routed_pages_are_idempotent(self) -> None:
        for name, route in sync.ROUTES.items():
            current = route.path.read_text()
            self.assertEqual(sync.render_route(current, CLASSIC, route), current, name)
            self.assertIn('<nav class="subnav"', current, name)
            self.assertGreaterEqual(current.count('<div class="wrap">'), 3, name)

    def test_vwap_route_contains_equity_country_and_crypto_surfaces(self) -> None:
        page = (ROOT / "trading" / "momentum" / "index.html").read_text()
        self.assertIn('id="vwap-panel"', page)
        self.assertIn('id="vwap-country-chart-grid"', page)
        self.assertIn('id="crypto-panel"', page)
        self.assertIn('/trading/vwap-charts.json?v=', page)
        self.assertIn('/trading/crypto-charts.json?v=', page)
        self.assertEqual(page.count('id="vwap-chart-grid"'), 1)
        self.assertEqual(page.count('id="crypto-chart-grid"'), 1)
        for panel_id in ("vwap-panel", "crypto-panel"):
            tag = re.search(rf'<section[^>]+id="{panel_id}"[^>]*>', page)
            if tag is None:
                self.fail(f"missing {panel_id}")
            self.assertNotIn(" hidden", tag.group(0))
        broker_hash = hashlib.sha256((ROOT / "js" / "trading-broker-light.js").read_bytes()).hexdigest()[:12]
        self.assertIn(f'/js/trading-broker-light.js?v={broker_hash}', page)
        vwap = json.loads((ROOT / "trading" / "vwap-charts.json").read_text())
        crypto = json.loads((ROOT / "trading" / "crypto-charts.json").read_text())
        self.assertEqual(len(vwap["groups"]["us"]), 13)
        self.assertEqual(len(vwap["groups"]["countries"]), 10)
        self.assertEqual(len(crypto["charts"]), 7)

    def test_gpt_brief_route_loads_the_current_payload(self) -> None:
        page = (ROOT / "trading" / "gpt-brief" / "index.html").read_text()
        payload = ROOT / "trading" / "gpt-brief.json"
        chart_payload = ROOT / "trading" / "gpt-brief-charts.json"
        payload_hash = hashlib.sha256(payload.read_bytes()).hexdigest()[:12]
        chart_hash = hashlib.sha256(chart_payload.read_bytes()).hexdigest()[:12]
        script_hash = hashlib.sha256((ROOT / "js" / "trading-gpt-brief.js").read_bytes()).hexdigest()[:12]
        self.assertIn(f'/trading/gpt-brief.json?v={payload_hash}', page)
        self.assertIn(f'/trading/gpt-brief-charts.json?v={chart_hash}', page)
        self.assertIn(f'/js/trading-gpt-brief.js?v={script_hash}', page)
        self.assertIn('id="gpt-brief-shell"', page)
        self.assertIn('Big stock-moving events, explained in plain English.', page)
        self.assertIn('Updated automatically on weekdays at 6:30 AM CT.', page)
        self.assertNotIn('source of truth: /trading/classic/', page)
        panel = re.search(r'<section[^>]+id="gpt-brief-panel"[^>]*>', page)
        if panel is None:
            self.fail("missing gpt-brief-panel")
        self.assertNotIn(" hidden", panel.group(0))

    def test_grok_brief_route_loads_the_current_payload(self) -> None:
        page = (ROOT / "trading" / "grok-brief" / "index.html").read_text()
        payload = ROOT / "trading" / "grok-brief.json"
        payload_hash = hashlib.sha256(payload.read_bytes()).hexdigest()[:12]
        script_hash = hashlib.sha256((ROOT / "js" / "trading-grok-brief.js").read_bytes()).hexdigest()[:12]
        self.assertIn(f'/trading/grok-brief.json?v={payload_hash}', page)
        self.assertIn(f'/js/trading-grok-brief.js?v={script_hash}', page)
        self.assertIn('id="grok-brief-shell"', page)
        self.assertIn('aria-current="page">Grok brief</a>', page)
        panel = re.search(r'<section[^>]+id="grok-brief-panel"[^>]*>', page)
        if panel is None:
            self.fail("missing grok-brief-panel")
        self.assertNotIn(" hidden", panel.group(0))

    def test_performance_route_matches_classic_results_and_history(self) -> None:
        page = (ROOT / "trading" / "performance" / "index.html").read_text()
        source = re.search(r'<!-- AUTO:RESULTS:START -->(.*?)<!-- AUTO:RESULTS:END -->', CLASSIC, re.S)
        if source is None:
            self.fail("missing classic RESULTS region")
        source_heading = re.search(r'<h2 id="results-heading">([^<]+)</h2>', source.group(1))
        if source_heading is None:
            self.fail("missing classic results heading")
        self.assertIn(f'<h2 id="results-heading">{source_heading.group(1)}</h2>', page)
        results = json.loads((ROOT / "trading" / "results-ytd.json").read_text())
        self.assertIn(f'data-results-points="{len(results["points"])}"', page)
        self.assertIn('id="results-panel"', page)
        panel = re.search(r'<section[^>]+id="results-panel"[^>]*>', page)
        if panel is None:
            self.fail("missing results-panel")
        self.assertNotIn(" hidden", panel.group(0))

    def test_risk_route_is_a_subjective_running_journal_without_metric_dashboard(self) -> None:
        page = (ROOT / "trading" / "gpt-risk" / "index.html").read_text()
        script = (ROOT / "trading" / "desk.js").read_text()
        styles = (ROOT / "trading" / "desk.css").read_text()
        journal = json.loads((ROOT / "trading" / "risk-journal.json").read_text())
        self.assertIn('id="risk-live"', page)
        self.assertIn("<title>GPT Risk", page)
        self.assertIn("<h1>GPT Risk</h1>", page)
        self.assertIn("risk-journal.json", script)
        self.assertIn("risk-journal-entry", script)
        self.assertIn("risk-journal-author", script)
        self.assertIn(".risk-journal-entry", styles)
        self.assertEqual(journal["author"], "GPT-5.6")
        self.assertGreaterEqual(len(journal["entries"]), 1)
        self.assertEqual(journal["entries"][0]["stance"], "Neutral")
        self.assertTrue(all(entry["author"] == "GPT-5.6" for entry in journal["entries"]))
        for junk in ("Metrics over time", "VVIX", "SKEW", "HY OAS", "VIX futures curve", "risk-evaluation.json"):
            self.assertNotIn(junk, page)
            self.assertNotIn(junk, script)

    def test_gemini_risk_route_matches_structured_model_output(self) -> None:
        page = (ROOT / "trading" / "gemini-risk" / "index.html").read_text()
        payload = json.loads((ROOT / "trading" / "gemini-risk.json").read_text())
        script = (ROOT / "trading" / "desk.js").read_text()
        entry = payload["entries"][0]
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["model"], "Gemini 3.1 Pro")
        self.assertEqual(entry["stance"], "Neutral to Risk-Off")
        self.assertEqual(entry["rating"], 4)
        self.assertEqual(entry["market_data_through"], "2026-07-24")
        self.assertEqual(len(entry["sections"]), 5)
        self.assertIn("<title>Gemini Risk", page)
        self.assertIn("<h1>Gemini Risk</h1>", page)
        self.assertIn('aria-current="page">Gemini Risk</a>', page)
        self.assertIn('data-model="Gemini 3.1 Pro"', page)
        self.assertIn('data-rating="4"', page)
        self.assertEqual(page.count('class="gemini-risk-card"'), 5)
        self.assertEqual(page.count("The stock market has been mixed"), 1)
        self.assertIn("Attribution and citation note", page)
        self.assertIn("/trading/gemini-risk.json", script)
        self.assertIn("setChip('gemini', 'Gemini'", script)

    def test_position_heat_bars_are_replaced_by_price_charts(self) -> None:
        page = (ROOT / "trading" / "index.html").read_text()
        script = (ROOT / "trading" / "desk.js").read_text()
        styles = (ROOT / "trading" / "desk.css").read_text()
        self.assertNotIn('class="track-bar"', page)
        self.assertEqual(page.count('class="position-risk-chart"'), 2)
        self.assertIn("prc-invalidation", script)
        self.assertIn("prc-entry-level", script)
        self.assertNotIn('class="prc-entry"', script)
        self.assertNotIn("vertical entry reference", script)
        self.assertIn("prc-tooltip", script)
        self.assertIn("room to invalidation", script)
        self.assertIn("ArrowLeft", script)
        self.assertIn("pointermove", script)
        self.assertIn(".position-risk-chart", styles)
        self.assertIn(".prc-entry-level", styles)
        self.assertNotIn(".prc-entry{", styles)
        self.assertIn(".prc-tooltip", styles)

    def test_market_rail_uses_ytd_chart_and_live_leadership_groups(self) -> None:
        page = (ROOT / "trading" / "index.html").read_text()
        script = (ROOT / "trading" / "desk.js").read_text()
        styles = (ROOT / "trading" / "desk.css").read_text()
        payload = json.loads((ROOT / "trading" / "market-ytd.json").read_text())
        self.assertIn('id="market-overview-live"', page)
        self.assertNotIn("Risk regime", page)
        self.assertNotIn("MOVE · HY OAS", page)
        for asset in ("market-ytd.json", "vwap-charts.json", "crypto-charts.json"):
            self.assertIn(asset, script)
        for marker in ("market-ytd-chart", "market-leadership", "Sectors", "Crypto", "Countries"):
            self.assertIn(marker, script + styles)
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["period"], "YTD")
        self.assertGreaterEqual(len(payload["points"]), 50)
        self.assertEqual(payload["points"][-1]["date"], payload["as_of"])

    def test_momentum_deep_link_filters_opens_and_scrolls_to_requested_ticker(self) -> None:
        script = (ROOT / "js" / "trading-broker-light.js").read_text()
        self.assertIn("universeInput.value = requested", script)
        self.assertIn("toggle.click()", script)
        self.assertIn("scrollIntoView({ block: 'start', behavior: 'smooth' })", script)
        self.assertIn("toggle.focus({ preventScroll: true })", script)

    def test_public_route_names_match_their_new_jobs(self) -> None:
        watchlist = (ROOT / "trading" / "watchlist" / "index.html").read_text()
        momentum = (ROOT / "trading" / "momentum" / "index.html").read_text()
        self.assertIn("<title>Watchlist", watchlist)
        self.assertIn('id="desk-route-heading">Watchlist</h1>', watchlist)
        self.assertIn("<title>Momentum", momentum)
        self.assertIn('id="desk-route-heading">Momentum</h1>', momentum)

    def test_trading_nav_has_home_logo_and_vwap_uses_three_columns(self) -> None:
        styles = (ROOT / "trading" / "desk.css").read_text()
        candidates = [ROOT / "trading" / "index.html", *(ROOT / "trading").glob("*/index.html")]
        pages = sorted({path for path in candidates if '<nav class="subnav"' in path.read_text()})
        self.assertEqual(len(pages), 13)
        for path in pages:
            page = path.read_text()
            self.assertEqual(page.count('class="trade-z-logo" href="/"'), 1, path.as_posix())
            self.assertIn('aria-label="Zonted homepage"', page, path.as_posix())
            self.assertRegex(page, r'href="/trading/watchlist/"[^>]*>Watchlist</a>')
            self.assertRegex(page, r'href="/trading/momentum/"[^>]*>Momentum</a>')
            self.assertRegex(page, r'href="/trading/gpt-risk/"[^>]*>GPT Risk</a>')
            self.assertRegex(page, r'href="/trading/gemini-risk/"[^>]*>Gemini Risk</a>')
            self.assertEqual(page.count('class="chip chip-gemini '), 1, path.as_posix())
            self.assertIn('/trading/desk.css?v=19', page, path.as_posix())
            self.assertIn('/trading/desk.js?v=19', page, path.as_posix())
        self.assertIn(".trade-z-logo", styles)
        self.assertIn(".vwap-chart-grid,.crypto-chart-grid{grid-template-columns:repeat(3,minmax(0,1fr))}", styles)


if __name__ == "__main__":
    unittest.main()
