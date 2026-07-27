#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
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

    def test_gpt_brief_web_surface_is_retired(self) -> None:
        retired = [
            ROOT / "trading" / "gpt-brief" / "index.html",
            ROOT / "trading" / "gpt-brief.json",
            ROOT / "trading" / "gpt-brief-charts.json",
            ROOT / "js" / "trading-gpt-brief.js",
            ROOT / "scripts" / "update-trading-gpt-brief.py",
            ROOT / "scripts" / "build-trading-gpt-brief-charts.py",
        ]
        self.assertTrue(all(not path.exists() for path in retired))
        self.assertNotIn("gpt-brief", sync.ROUTES)
        self.assertNotIn("AUTO:GPT_BRIEF", CLASSIC)
        self.assertNotIn('id="gpt-brief-tab"', CLASSIC)
        redirects = (ROOT / "_redirects").read_text()
        for retired_url in (
            "/trading/gpt-brief/*",
            "/trading/gpt-brief",
            "/trading/gpt-brief.json",
            "/trading/gpt-brief-charts.json",
            "/js/trading-gpt-brief.js",
        ):
            self.assertIn(f"{retired_url} /trading/ 301", redirects)

    def test_public_brief_route_is_restored_and_old_model_routes_stay_retired(self) -> None:
        self.assertNotIn("brief", sync.ROUTES)
        self.assertNotIn("grok-brief", sync.ROUTES)
        self.assertTrue((ROOT / "trading" / "brief" / "index.html").exists())
        self.assertFalse((ROOT / "trading" / "grok-brief" / "index.html").exists())
        redirects = (ROOT / "_redirects").read_text()
        for retired_url in ("/trading/grok-brief", "/trading/horizon"):
            self.assertIn(f"{retired_url} /trading/ 301", redirects)

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

    def test_meta_risk_route_preserves_the_search_grounded_model_output(self) -> None:
        page = (ROOT / "trading" / "meta-risk" / "index.html").read_text()
        payload = json.loads((ROOT / "trading" / "meta-risk.json").read_text())
        entry = payload["entries"][0]
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["model"], "Meta AI muse-spark-1.1")
        self.assertEqual(
            payload["prompt"],
            "Use all data sources that make sense to you. How would you rate the current stock market: risk on, risk off, or neutral? Why?",
        )
        self.assertEqual(entry["as_of"], "2026-07-27")
        self.assertEqual(entry["stance"], "Neutral, leaning Risk-Off")
        self.assertGreaterEqual(len(entry["search_queries"]), 10)
        self.assertGreaterEqual(len(entry["sources"]), 3)
        self.assertIn("<title>Meta Risk", page)
        self.assertIn("<h1>Meta Risk</h1>", page)
        self.assertIn('aria-current="page">Meta Risk</a>', page)
        self.assertIn('data-model="Meta AI muse-spark-1.1"', page)
        self.assertIn("Exact model response", page)
        self.assertIn('class="meta-risk-response"', page)
        self.assertNotIn("### Why", page)
        self.assertIn("Integrity note", page)
        self.assertIn("/trading/meta-risk.json", page)

    def test_position_heat_bars_are_replaced_by_price_charts(self) -> None:
        page = (ROOT / "trading" / "index.html").read_text()
        script = (ROOT / "trading" / "desk.js").read_text()
        styles = (ROOT / "trading" / "desk.css").read_text()
        self.assertNotIn('class="track-bar"', page)
        self.assertEqual(page.count('class="position-risk-chart"'), 6)
        self.assertEqual(page.count('data-position-symbol='), 6)
        self.assertEqual(
            set(re.findall(r'data-position-symbol="([A-Z]+)"', page)),
            {"ABT", "CEG", "FIGR", "HOOD", "HPQ", "RDDT"},
        )
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

    def test_dual_vwap_setup_window_persists_for_three_trading_sessions(self) -> None:
        def chart(closes: list[float], earnings: list[float], ytd: list[float]) -> dict:
            dates = [f"2026-07-{day:02d}" for day in range(13, 13 + len(closes))]
            return {"series": {"dates": dates, "c": closes, "ev": earnings, "yv": ytd}}

        charts = {
            "LONG": chart([9, 11, 9, 9], [10, 10, 10, 10], [8, 8, 8, 8]),
            "SHORT": chart([9, 7, 9], [10, 10, 10], [8, 8, 8]),
            "EXPIRED": chart([9, 11, 9, 9, 9], [10, 10, 10, 10, 10], [8, 8, 8, 8, 8]),
        }
        setups = sync.dual_vwap_setups(charts)
        self.assertEqual([row["symbol"] for row in setups["long"]], ["LONG"])
        self.assertEqual(setups["long"][0]["day"], 3)
        self.assertIsNone(setups["long"][0]["current_side"])
        self.assertEqual([row["symbol"] for row in setups["short"]], ["SHORT"])
        self.assertEqual(setups["short"][0]["day"], 2)
        self.assertNotIn("EXPIRED", {row["symbol"] for side in setups.values() for row in side})

    def test_first_available_bar_is_not_a_crossover(self) -> None:
        charts = {
            "FIRST_LONG": {"series": {"dates": ["2026-07-20"], "c": [11], "ev": [10], "yv": [10]}},
            "FIRST_SHORT": {"series": {"dates": ["2026-07-20"], "c": [9], "ev": [10], "yv": [10]}},
        }
        setups = sync.dual_vwap_setups(charts)
        self.assertEqual(setups, {"long": [], "short": []})

    def test_fast_reversal_can_be_active_on_both_sides(self) -> None:
        charts = {"FLIP": {"series": {
            "dates": ["2026-07-20", "2026-07-21", "2026-07-22"],
            "c": [9, 11, 9], "ev": [10, 10, 10], "yv": [10, 10, 10],
        }}}
        setups = sync.dual_vwap_setups(charts)
        self.assertEqual(setups["long"][0]["symbol"], "FLIP")
        self.assertEqual(setups["long"][0]["trigger_date"], "2026-07-21")
        self.assertEqual(setups["short"][0]["symbol"], "FLIP")
        self.assertEqual(setups["short"][0]["trigger_date"], "2026-07-22")

    def test_dual_vwap_ticker_cards_launch_reused_chart_modal(self) -> None:
        page = (ROOT / "trading" / "vwap-setups" / "index.html").read_text()
        payload = json.loads((ROOT / "trading" / "scan-charts.json").read_text())
        self.assertFalse([symbol for symbol, record in payload["charts"].items() if not record.get("company_name")])
        setups = sync.dual_vwap_setups(payload["charts"])
        active_symbols = [row["symbol"] for rows in setups.values() for row in rows]
        self.assertTrue(active_symbols)
        self.assertEqual(page.count('class="dual-vwap-chart-launch"'), len(active_symbols))
        for symbol in active_symbols:
            record = payload["charts"][symbol]
            company_name = record.get("company_name")
            self.assertTrue(company_name, symbol)
            self.assertIn(f'data-hypothesis-chart-open="{symbol}"', page)
            self.assertIn(f'<em>{html.escape(company_name)}</em>', page)
            sector_z = sync.sector_z_scores()[record["sector_etf"]]
            direction = "up" if sector_z > 0 else "down" if sector_z < 0 else "flat"
            self.assertIn(f'data-hypothesis-chart-open="{symbol}" data-sector-direction="{direction}"', page)
            self.assertIn(f'{record["sector_etf"]} {sector_z:+.2f}', page)
        self.assertEqual(page.count('id="hypothesis-chart-dialog"'), 1)
        self.assertEqual(page.count('id="scan-chart-config"'), 1)
        self.assertIn('/trading/hypothesis-summary.6e6f3b19.css', page)
        self.assertIn('/js/hypothesis-chart-modal.1b5e1178.js?v=', page)
        match = re.search(r'<script type="application/json" id="scan-chart-config">(.*?)</script>', page)
        self.assertIsNotNone(match)
        chart_config = json.loads(match.group(1) if match else "{}")
        self.assertEqual(chart_config["vwap_url"], f'/trading/vwap-charts.json?v={sync.digest(sync.VWAP_CHARTS)}')

    def test_public_route_names_match_their_new_jobs(self) -> None:
        watchlist = (ROOT / "trading" / "watchlist" / "index.html").read_text()
        setups = (ROOT / "trading" / "vwap-setups" / "index.html").read_text()
        momentum = (ROOT / "trading" / "momentum" / "index.html").read_text()
        self.assertIn("<title>Watchlist", watchlist)
        self.assertIn('id="desk-route-heading">Watchlist</h1>', watchlist)
        self.assertIn("<title>VWAP Setups", setups)
        self.assertIn('id="desk-route-heading">VWAP Setups</h1>', setups)
        self.assertIn("Breaks above or below both earnings VWAP and YTD VWAP stay active for three trading sessions.", setups)
        updater = (ROOT / "scripts" / "update-trading-scan.py").read_text()
        self.assertIn('sync_sections(["momentum", "setups"])', updater)
        self.assertIn("<title>Momentum", momentum)
        self.assertIn('id="desk-route-heading">Momentum</h1>', momentum)

    def test_trading_nav_has_home_logo_and_vwap_uses_three_columns(self) -> None:
        styles = (ROOT / "trading" / "desk.css").read_text()
        candidates = [ROOT / "trading" / "index.html", *(ROOT / "trading").glob("*/index.html")]
        pages = sorted({path for path in candidates if '<nav class="subnav"' in path.read_text()})
        self.assertEqual(len(pages), 12)
        for path in pages:
            page = path.read_text()
            self.assertEqual(page.count('class="trade-z-logo" href="/"'), 1, path.as_posix())
            self.assertIn('aria-label="Zonted homepage"', page, path.as_posix())
            self.assertRegex(page, r'href="/trading/watchlist/"[^>]*>Watchlist</a>')
            self.assertRegex(page, r'href="/trading/vwap-setups/"[^>]*>VWAP Setups</a>')
            self.assertRegex(page, r'href="/trading/momentum/"[^>]*>Momentum</a>')
            self.assertRegex(page, r'href="/trading/gpt-risk/"[^>]*>GPT Risk</a>')
            self.assertRegex(page, r'href="/trading/gemini-risk/"[^>]*>Gemini Risk</a>')
            self.assertRegex(page, r'href="/trading/meta-risk/"[^>]*>Meta Risk</a>')
            self.assertEqual(page.count('class="chip chip-gemini '), 1, path.as_posix())
            self.assertIn('/trading/desk.css?v=19', page, path.as_posix())
            self.assertIn('/trading/desk.js?v=20', page, path.as_posix())
        self.assertIn(".trade-z-logo", styles)
        self.assertIn(".vwap-chart-grid,.crypto-chart-grid{grid-template-columns:repeat(3,minmax(0,1fr))}", styles)


if __name__ == "__main__":
    unittest.main()
