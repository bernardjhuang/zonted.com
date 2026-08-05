#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import json
import datetime as dt
import os
import pathlib
import re
import subprocess
import sys
import unittest

import sync_trading_desk as sync
import trading_shell

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLASSIC = (ROOT / "trading" / "pipeline.html").read_text()
DESK_HOME = ROOT / "trading" / "index.html"
RETIRED_HYPOTHESES = {"HPQ", "JBS", "NTDOY"}


def _desk_rows(page: str, kind: str) -> list[str]:
    pattern = rf'<tr\b(?=[^>]*data-desk-kind="{kind}")[^>]*>.*?</tr>'
    return re.findall(pattern, page, re.S)


def _row_symbol(row: str) -> str:
    match = re.search(r'data-desk-symbol="([A-Z]+)"', row)
    if match is None:
        raise AssertionError(f"desk row has no data-desk-symbol: {row[:160]}")
    return match.group(1)


def _row_attr(row: str, name: str) -> str:
    match = re.search(rf'{re.escape(name)}="([^"]+)"', row)
    if match is None:
        raise AssertionError(f"desk row has no {name}: {row[:160]}")
    return match.group(1)


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

    def test_unlinked_brief_routes_stay_retired(self) -> None:
        self.assertNotIn("brief", sync.ROUTES)
        self.assertNotIn("grok-brief", sync.ROUTES)
        self.assertFalse((ROOT / "trading" / "brief" / "index.html").exists())
        self.assertFalse((ROOT / "trading" / "grok-brief" / "index.html").exists())
        redirects = (ROOT / "_redirects").read_text()
        for retired_url in ("/trading/brief", "/trading/grok-brief", "/trading/horizon"):
            self.assertIn(f"{retired_url} /trading/ 301", redirects)

    def test_performance_route_matches_classic_results_and_history(self) -> None:
        page = (ROOT / "trading" / "performance" / "index.html").read_text()
        source = re.search(r'<!-- AUTO:RESULTS:START -->(.*?)<!-- AUTO:RESULTS:END -->', CLASSIC, re.S)
        if source is None:
            self.fail("missing pipeline RESULTS region")
        source_heading = re.search(r'<h2 id="results-heading">([^<]+)</h2>', source.group(1))
        if source_heading is None:
            self.fail("missing pipeline results heading")
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
        self.assertIn(journal["entries"][0]["stance"], {"Risk-on", "Neutral", "Risk-off"})
        self.assertEqual(
            journal["entries"][0]["date"],
            json.loads((ROOT / "trading" / "market-ytd.json").read_text())["as_of"],
        )
        self.assertTrue(all(entry["author"] == "GPT-5.6" for entry in journal["entries"]))
        for junk in ("Metrics over time", "VVIX", "SKEW", "HY OAS", "VIX futures curve", "risk-evaluation.json"):
            self.assertNotIn(junk, page)
            self.assertNotIn(junk, script)

    def test_retired_meta_and_gemini_risk_surfaces_stay_removed(self) -> None:
        script = (ROOT / "trading" / "desk.js").read_text()
        redirects = (ROOT / "_redirects").read_text()
        for model in ("gemini", "meta"):
            self.assertFalse((ROOT / "trading" / f"{model}-risk").exists())
            self.assertFalse((ROOT / "trading" / f"{model}-risk.json").exists())
            self.assertFalse((ROOT / "scripts" / f"update-{model}-risk.py").exists())
            self.assertNotIn(f"/trading/{model}-risk", script)
            self.assertIn(f"/trading/{model}-risk/* /trading/ 301", redirects)
            self.assertIn(f"/trading/{model}-risk.json /trading/ 301", redirects)
        self.assertIn("const sessionRank = { 'pre-market': 0, intraday: 1, 'post-close': 2 }", script)
        self.assertIn("[...(d.entries || []), ...(d.model_entries || [])]", script)
        self.assertNotIn("((d.model_entries && d.model_entries[0]) ||", script)

    def test_trading_desk_v3_generator_is_network_free_and_idempotent(self) -> None:
        script = ROOT / "scripts" / "build-trading-desk.py"
        self.assertTrue(script.exists(), "desk must be generated from source, not hand-edited HTML")
        check_args = [sys.executable, str(script)]
        morning_quotes = os.environ.get("ZONTED_DESK_MORNING_QUOTES")
        if morning_quotes:
            check_args.extend(["--mode", "morning", "--quotes", morning_quotes])
        check_args.append("--check")
        result = subprocess.run(
            check_args,
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("network-free", result.stdout)

    def test_trading_desk_v3_uses_two_aligned_blotter_tables(self) -> None:
        page = (ROOT / "trading" / "index.html").read_text()
        script = (ROOT / "trading" / "desk.js").read_text()
        styles = (ROOT / "trading" / "desk.css").read_text()
        self.assertTrue(page.startswith("<!DOCTYPE html>"))
        self.assertIn("<!-- AUTO:DESK_POSITIONS:START -->", page)
        self.assertIn("<!-- AUTO:DESK_POSITIONS:END -->", page)
        self.assertIn("<!-- AUTO:DESK_HYPOTHESES:START -->", page)
        self.assertIn("<!-- AUTO:DESK_HYPOTHESES:END -->", page)
        self.assertNotIn('class="pos"', page)
        self.assertNotIn('class="portfolio-card', page)

        colgroups = re.findall(r'<table\b[^>]*class="[^"]*desk-blotter-table[^"]*"[^>]*>\s*(<colgroup>.*?</colgroup>)', page, re.S)
        self.assertEqual(len(colgroups), 2)
        self.assertEqual(colgroups[0], colgroups[1], "positions and hypotheses tables must share one literal colgroup")
        self.assertEqual(
            re.findall(r'<col style="width:([^\"]+)">', colgroups[0]),
            ["18%", "7%", "6%", "10%", "5%", "6%", "6%", "23%", "13%", "6%"],
        )
        self.assertIn(".desk-blotter-table{table-layout:fixed", styles.replace(" ", ""))

        position_rows = _desk_rows(page, "position")
        thesis_rows = _desk_rows(page, "hypothesis")
        positions_artifact = json.loads((ROOT / "trading" / "desk-positions.json").read_text())
        self.assertEqual(positions_artifact["schema_version"], 3)
        positions_payload = positions_artifact["positions"]
        risk_summary = positions_artifact["risk_summary"]
        self.assertIn('<div class="desk-risk-strip" aria-label="Portfolio risk summary">', page)
        self.assertIn(f'Gross Δ$ <b>{risk_summary["gross_delta_leverage"]:.1f}×</b>', page)
        self.assertIn(f'Net Δ$ <b>{risk_summary["net_delta_exposure_percent"]:.1f}%</b>', page)
        self.assertIn(f'Premium risk <b>{risk_summary["premium_at_risk_percent"]:.1f}%</b>', page)
        self.assertIn(f'Θ/day <b>{risk_summary["theta_percent_per_day"]:+.2f}%</b>', page)
        cash_label = "Margin debit" if risk_summary["cash_percent"] < 0 else "Cash liquidity"
        self.assertIn(f'{cash_label} <b>{risk_summary["cash_percent"]:.1f}%</b>', page)
        self.assertIn(risk_summary["quantity_basis"], page)
        sleeves = positions_artifact["sleeves"]
        self.assertEqual(set(sleeves), {"thesis", "momentum"})
        self.assertIn('<div class="desk-sleeve-strip" aria-label="Sleeve risk summary">', page)
        for name, values in sleeves.items():
            self.assertIn(
                f'<b>{name.title()}</b> · Δ$ {values["exposure_percent"]:.1f}% · capital {values["capital_percent"]:.1f}% · premium {values["premium_at_risk_percent"]:.1f}%',
                page,
            )
        self.assertIn(f'<span>{len(positions_payload)} open · sorted by Δ$ exposure</span>', page)
        self.assertIn("--bl-exposure:var(--bl-accent)", styles.replace(" ", ""))
        self.assertIn(".desk-position-exposure{grid-column:2;color:var(--bl-exposure)", styles.replace(" ", ""))
        self.assertEqual(page.count("<th>Beta</th>"), 2)
        self.assertNotIn("<th>IV</th>", page)
        self.assertNotIn('data-label="IV"', page)
        self.assertNotIn("allocation_percent", json.dumps(positions_artifact))
        self.assertNotIn("% allocation", page)
        expected_positions = {row["symbol"] for row in positions_payload}
        expected_hypotheses = set(json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"]) - expected_positions
        total_symbols = expected_positions | expected_hypotheses
        source_charts = json.loads((ROOT / "trading" / "hypothesis-charts.json").read_text())["charts"]
        feed_count = sum(
            'data-feed-state="live"' in row
            for row in (*position_rows, *thesis_rows)
        )
        self.assertEqual({_row_symbol(row) for row in position_rows}, expected_positions)
        self.assertEqual({_row_symbol(row) for row in thesis_rows}, expected_hypotheses)
        self.assertFalse({_row_symbol(row) for row in position_rows} & {_row_symbol(row) for row in thesis_rows})
        exposures = [float(_row_attr(row, "data-exposure-percent")) for row in position_rows]
        self.assertEqual(exposures, sorted(exposures, reverse=True))
        self.assertGreater(max(exposures), 100)
        catalysts = [_row_attr(row, "data-catalyst-date") for row in thesis_rows]
        self.assertEqual(catalysts, sorted(catalysts), catalysts)
        for rows in (position_rows, thesis_rows):
            for row in rows:
                self.assertRegex(row, r'data-edge="(up|down|flat|soon|no-feed)"')
                self.assertIn('class="desk-edge-word"', row)
                symbol = _row_symbol(row)
                self.assertIn(f'data-label="Beta">{source_charts[symbol]["beta_2y_weekly_vs_spy"]:.2f}<', row)

        self.assertFalse(total_symbols & RETIRED_HYPOTHESES)
        net_row = next(row for row in thesis_rows if _row_symbol(row) == "NET")
        self.assertNotIn('data-feed-state="no-feed"', net_row)
        byddy_row = next(row for row in (*position_rows, *thesis_rows) if _row_symbol(row) == "BYDDY")
        self.assertIn('data-feed-state="live" data-feed-source="robinhood"', byddy_row)
        morning_quotes = os.environ.get("ZONTED_DESK_MORNING_QUOTES")
        if morning_quotes:
            fallback = json.loads(pathlib.Path(morning_quotes).read_text())
        else:
            fallback = json.loads((ROOT / "trading" / "desk-close-quotes.json").read_text())
        chart_date = json.loads((ROOT / "trading" / "hypothesis-charts.json").read_text())["as_of"]
        self.assertEqual(fallback["generated_at"][:10], chart_date)
        self.assertIn("BYDDY", fallback["quotes"])
        self.assertIn(f'>${float(fallback["quotes"]["BYDDY"]["price"]):,.2f}<', byddy_row)

        toggles = re.findall(r'<button[^>]+class="desk-row-toggle"[^>]+aria-expanded="false"[^>]+aria-controls="(desk-detail-[^"]+)"', page)
        self.assertEqual(len(toggles), len(total_symbols))
        for detail_id in toggles:
            match = re.search(rf'<tr[^>]+id="{detail_id}"[^>]+hidden[^>]*>(.*?)</tr>', page, re.S)
            self.assertIsNotNone(match, detail_id)
            detail = match.group(1) if match else ""
            self.assertIn('data-desk-one-year-chart', detail)
            self.assertIn('data-desk-valuation', detail)
            self.assertIn('data-desk-entry-tiles', detail)
            self.assertNotIn('data-hypothesis-chart-open=', detail)
            self.assertNotIn('desk-detail-actions', detail)
            self.assertNotIn('data-thesis-open=', detail)

        self.assertEqual(page.count('class="desk-thesis-cell-button"'), len(total_symbols))
        self.assertEqual(page.count('<th>Chart</th>'), 2)
        self.assertEqual(page.count('class="desk-chart-cell-button"'), len(total_symbols))
        self.assertEqual(page.count('<td colspan="10">'), len(total_symbols))
        for symbol in total_symbols:
            launcher = re.search(
                rf'<tr class="desk-main-row"[^>]+data-desk-symbol="{symbol}".*?<button[^>]+class="desk-chart-cell-button"[^>]+data-hypothesis-chart-open="{symbol}"[^>]*>',
                page,
                re.S,
            )
            self.assertIsNotNone(launcher, symbol)
            self.assertIn(f'aria-label="Open {symbol} setup chart"', launcher.group(0) if launcher else "")
            self.assertIn('aria-haspopup="dialog"', launcher.group(0) if launcher else "")
            self.assertIn('aria-controls="hypothesis-chart-dialog"', launcher.group(0) if launcher else "")
        self.assertNotIn("Room to kill", page)
        self.assertNotIn("What would move it", page)
        self.assertNotIn("Canonical thesis", page)

        self.assertIn("initDeskBlotter", script)
        self.assertIn("toggleDeskRow", script)
        self.assertIn("ArrowDown", script)
        self.assertIn("pointermove", script)
        self.assertIn("initDeskHistoryCharts", script)
        self.assertIn("initDeskYtdCharts", script)
        self.assertIn("data-desk-chart-tooltip", page)
        self.assertEqual(page.count("data-desk-ytd-tooltip"), feed_count)
        self.assertEqual(page.count('viewBox="0 0 236 88"'), feed_count)
        self.assertEqual(page.count('class="desk-ytd-axis-label"'), feed_count * 6)
        self.assertEqual(page.count('class="desk-ytd-grid"'), feed_count * 3)
        self.assertEqual(page.count("trailing one-year return"), feed_count)
        chart_ranges = re.findall(r'data-desk-one-year-chart="([A-Z]+)" data-desk-chart-dates="([^"]+)"', page)
        self.assertEqual(len(chart_ranges), feed_count)
        for symbol, encoded_dates in chart_ranges:
            dates = [dt.date.fromisoformat(value) for value in encoded_dates.split(",")]
            source_start = dt.date.fromisoformat(source_charts[symbol]["dates"][0])
            expected_start = max(source_start, dates[-1] - dt.timedelta(days=365))
            self.assertGreaterEqual(dates[0], expected_start, symbol)
            self.assertLessEqual((dates[0] - expected_start).days, 7, f"{symbol} chart omits available trailing-one-year history")
        self.assertIn("Trailing 1Y", script)
        self.assertIn("grid-template-columns:236px", styles.replace(" ", ""))
        self.assertEqual(page.count('class="desk-detail-axis-label"'), feed_count * 7)
        self.assertEqual(page.count('class="desk-detail-grid"'), feed_count * 4)
        self.assertIn("price and date axes", page)
        self.assertIn(".desk-ytd-tooltip{position:fixed", styles.replace(" ", ""))
        self.assertIn(
            ".desk-ytd-hover-line[hidden],.desk-ytd-hover-dot[hidden]{display:none}",
            styles.replace(" ", ""),
        )
        self.assertNotIn("Up to 2 years", page)
        self.assertNotIn('<th>P&amp;L</th>', page)
        for label, date in (
            ("Est. August deliveries", "Sep 2"),
            ("Est. Q3 earnings", "Oct 29"),
            ("Est. Q3 earnings", "Nov 3"),
            ("Est. Q3 earnings", "Nov 4"),
        ):
            self.assertIn(f'<b>{label}</b><small>{date}</small>', page)
        for position in positions_payload:
            symbol = position["symbol"]
            row = next(row for row in position_rows if _row_symbol(row) == symbol)
            flair = position["flair"]
            self.assertIn(f'desk-position-flair--{flair}', row)
            self.assertIn(f'>{flair.title()}<', row)
            self.assertIn(f'data-exposure-percent="{position["exposure_percent"]:.1f}"', row)
            self.assertIn(f'>{position["exposure_percent"]:.1f}% Δ$ exposure<', row)
            self.assertIn(f'>capital {position["capital_percent"]:.1f}%<', row)
            if position["premium_at_risk_percent"] > 0:
                self.assertIn(f'>premium {position["premium_at_risk_percent"]:.1f}%<', row)
                self.assertIn(f'>θ/day {position["theta_percent_per_day"]:+.2f}%<', row)
            self.assertIn(f'data-label="Beta">{source_charts[symbol]["beta_2y_weekly_vs_spy"]:.2f}<', row)
            if position["unstable_delta"]:
                self.assertIn(f'⚠ {position["min_dte"]}-DTE delta', row)
            if position.get("kill") is not None:
                kill = float(position["kill"])
                kill_label = f"${kill:,.2f}" if abs(kill) < 100 else f"${kill:,.0f}"
                self.assertIn(f'data-desk-ytd-kill="{position["kill"]}"', row)
                self.assertIn(f'<title>Kill {kill_label}</title>', row)
        self.assertIn("--desk-chart-bear", styles)
        self.assertIn("--desk-chart-base", styles)
        self.assertIn("--desk-chart-bull", styles)

    def test_trading_reference_levels_are_not_presented_as_intrinsic_scenarios(self) -> None:
        page = DESK_HOME.read_text()
        expected = {
            "lth": ("52W low", "Cost basis", "52W high", "cost basis"),
        }
        self.assertNotIn('id="desk-detail-pg"', page)
        for symbol, display in expected.items():
            labels, comparison = display[:3], display[3]
            match = re.search(rf'<tr class="desk-detail-row" id="desk-detail-{symbol}".*?</tr>', page, re.S)
            self.assertIsNotNone(match, symbol)
            detail = match.group(0) if match else ""
            self.assertIn("Trading reference levels", detail)
            self.assertNotIn("Intrinsic entry levels", detail)
            for label in labels:
                self.assertIn(f'<span>{label}</span>', detail)
            self.assertIn(f"versus {comparison}", detail)
        intrinsic = re.search(r'<tr class="desk-detail-row" id="desk-detail-hood".*?</tr>', page, re.S)
        self.assertIsNotNone(intrinsic)
        self.assertIn("Intrinsic entry levels", intrinsic.group(0) if intrinsic else "")

    def test_trading_desk_v3_reuses_chart_modal_and_fetches_full_thesis(self) -> None:
        page = DESK_HOME.read_text()
        script = (ROOT / "trading" / "desk.js").read_text()
        styles = (ROOT / "trading" / "desk.css").read_text()
        chart_script_hash = hashlib.sha256((ROOT / "js" / "hypothesis-chart-modal.b42a9700.js").read_bytes()).hexdigest()[:12]
        total_symbols = len(json.loads((ROOT / "trading" / "hypothesis-valuations.json").read_text())["rows"])
        self.assertEqual(page.count('id="hypothesis-chart-dialog"'), 1)
        self.assertEqual(page.count('id="scan-chart-config"'), 1)
        self.assertIn(f'/js/hypothesis-chart-modal.b42a9700.js?v={chart_script_hash}', page)
        self.assertEqual(page.count('data-hypothesis-chart-open='), total_symbols)
        for launcher in re.findall(r'<button[^>]+data-hypothesis-chart-open="[A-Z]+"[^>]*>', page):
            self.assertIn('aria-haspopup="dialog"', launcher)
            self.assertIn('aria-controls="hypothesis-chart-dialog"', launcher)
        config_match = re.search(r'<script type="application/json" id="scan-chart-config">(.*?)</script>', page)
        self.assertIsNotNone(config_match)
        config = json.loads(config_match.group(1) if config_match else "{}")
        self.assertEqual(config["url"], f'/trading/scan-charts.json?v={sync.digest(sync.SCAN_CHARTS)}')
        self.assertEqual(config["vwap_url"], f'/trading/vwap-charts.json?v={sync.digest(sync.VWAP_CHARTS)}')

        self.assertEqual(page.count('id="desk-thesis-dialog"'), 1)
        source_hash = hashlib.sha256((ROOT / "trading" / "hypothesis-source.txt").read_bytes()).hexdigest()[:12]
        self.assertIn(f'data-thesis-source="/trading/hypothesis-source.txt?v={source_hash}"', page)
        self.assertIn('data-thesis-summary', page)
        self.assertIn('data-thesis-body', page)
        self.assertIn("fetch(thesisSource", script)
        self.assertIn("article.hypothesis-detail", script)
        self.assertIn("details", script)
        self.assertIn("removeAttribute('open'", script)
        self.assertNotIn("setAttribute('open'", script)
        self.assertIn("data-thesis-open", script)
        self.assertIn("cancel", script)
        self.assertIn("focus", script)
        self.assertIn(".desk-thesis-dialog", styles)
        self.assertIn(".hyp-chart-dialog", styles)
        self.assertRegex(styles, r'\.desk-thesis-dialog[^{}]*\{[^}]*color:var\(--bl-ink\)')
        self.assertRegex(styles, r'\.hyp-chart-dialog[^{}]*\{[^}]*color:var\(--bl-ink\)')
        self.assertIn(".hypothesis-simple-thesis", styles)
        source = (ROOT / "trading" / "hypothesis-source.txt").read_text()
        simple_theses = {
            "BMNR": ["ETH treasury with staking yield", "Weekly ETH accumulation", "50-day average"],
            "FIGR": ["previously founded SoFi", "Real-world assets", "$25 is the working floor"],
            "MDB": ["AI tailwinds support Atlas", "earnings and yearly VWAPs", "Strong hiring numbers"],
            "FRMI": ["Energy demand from SpaceX", "deep industry knowledge remains bullish"],
        }
        for symbol, expected_lines in simple_theses.items():
            match = re.search(rf'<article class="hypothesis-detail" id="hypothesis-{symbol.lower()}-setup".*?</article>', source, re.S)
            self.assertIsNotNone(match, f"Missing {symbol} thesis")
            article = match.group(0) if match else ""
            self.assertIn('class="hypothesis-bottom-line hypothesis-simple-thesis"', article)
            self.assertNotRegex(article, r'<details[^>]*\sopen(?:\s|=|>)')
            for expected in expected_lines:
                self.assertIn(expected, article)
        self.assertNotIn('height="auto"', page + script)
        self.assertIn('.desk{display:grid;grid-template-columns:minmax(0,1fr)', styles.replace(" ", ""))

    def test_desk_home_is_full_width_and_mentality_has_its_own_route(self) -> None:
        page = (ROOT / "trading" / "index.html").read_text()
        script = (ROOT / "trading" / "desk.js").read_text()
        styles = (ROOT / "trading" / "desk.css").read_text()
        mentality = (ROOT / "trading" / "mentality" / "index.html").read_text()
        self.assertNotIn('class="desk-rail"', page)
        self.assertNotIn('id="market-overview-live"', page)
        self.assertNotIn('aria-label="Trading mentality reminders"', page)
        self.assertNotIn("market rail", script)
        self.assertNotIn("market-ytd-chart", script + styles)
        self.assertIn(".desk{display:grid;grid-template-columns:minmax(0,1fr)", styles.replace(" ", ""))
        self.assertIn("Know the difference between a momentum play, a narrative play, and gambling.", mentality)
        self.assertIn("Always do your own research.", mentality)
        self.assertIn("How much is your thinking already priced in?", mentality)
        self.assertIn("You will not buy the bottom or sell the top.", mentality)
        self.assertIn("momentum does not reward patience", mentality)

    def test_status_bar_sector_pills_match_vwap_leaders_and_laggards(self) -> None:
        scores = trading_shell.sector_z_scores()
        expected = trading_shell.rank_sector_pills(scores)
        page = (ROOT / "trading" / "index.html").read_text()
        pills = re.findall(
            r'<a class="sector-chip sector-chip--(leader|laggard)"[^>]+data-sector-symbol="([A-Z]+)"[^>]+data-sector-z="([+-]?\d+\.\d+)"',
            page,
        )
        self.assertEqual(len(pills), 4)
        self.assertEqual(
            [(kind, symbol, float(value)) for kind, symbol, value in pills],
            [(row["kind"], row["symbol"], round(row["z"], 2)) for row in expected],
        )
        updater = (ROOT / "scripts" / "update-trading-vwap.py").read_text()
        self.assertIn("refresh_sector_status_pills", updater)

    def test_status_bar_matches_market_snapshot_and_open_positions_across_routes(self) -> None:
        page = (ROOT / "trading" / "index.html").read_text()
        positions = json.loads((ROOT / "trading" / "desk-positions.json").read_text())["positions"]
        stamp = re.search(r'<span class="stamp">([^<]+)</span>', page)
        self.assertIsNotNone(stamp)
        if stamp and stamp.group(1).startswith("Live ·"):
            status = json.loads((ROOT / "trading" / "desk-morning-quotes.json").read_text())["status_market"]
        else:
            points = json.loads((ROOT / "trading" / "market-ytd.json").read_text())["points"]
            latest, previous = points[-1], points[-2]
            status = {
                "spy": latest["spy"],
                "spy_day_pct": (latest["spy"] / previous["spy"] - 1) * 100,
                "vix": latest["vix"],
            }
        expected = (
            f'data-status-spy="{float(status["spy"]):.2f}" data-status-spy-day="{float(status["spy_day_pct"]):.4f}"',
            f'data-status-vix="{float(status["vix"]):.2f}"',
            f'data-status-open="{len(positions)}"',
        )
        status_pages = [
            path for path in (ROOT / "trading").glob("**/index.html")
            if path != ROOT / "trading" / "hypothesis-source" / "index.html"
            and '<div class="status-metrics">' in path.read_text()
        ]
        self.assertEqual(len(status_pages), 9)
        for path in status_pages:
            source = path.read_text()
            for marker in expected:
                self.assertIn(marker, source, path)

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
        self.assertIn('/js/hypothesis-chart-modal.b42a9700.js?v=', page)
        match = re.search(r'<script type="application/json" id="scan-chart-config">(.*?)</script>', page)
        self.assertIsNotNone(match)
        chart_config = json.loads(match.group(1) if match else "{}")
        self.assertEqual(chart_config["vwap_url"], f'/trading/vwap-charts.json?v={sync.digest(sync.VWAP_CHARTS)}')

    def test_public_route_names_match_their_new_jobs(self) -> None:
        setups = (ROOT / "trading" / "vwap-setups" / "index.html").read_text()
        momentum = (ROOT / "trading" / "momentum" / "index.html").read_text()
        self.assertFalse((ROOT / "trading" / "watchlist" / "index.html").exists())
        redirects = (ROOT / "_redirects").read_text()
        self.assertIn("/trading/watchlist/* /trading/vwap-setups/:splat 301", redirects)
        self.assertIn("<title>VWAP Setups", setups)
        self.assertIn('id="desk-route-heading">VWAP Setups</h1>', setups)
        self.assertIn("Breaks above or below both earnings VWAP and YTD VWAP stay active for three trading sessions.", setups)
        self.assertIn("Sector-qualified momentum", setups)
        self.assertLess(setups.index('id="scan-method"'), setups.index("Sector-qualified momentum"))
        self.assertLess(setups.index("Sector-qualified momentum"), setups.index('id="scan-universe"'))
        setup_launchers = setups.count('class="sector-setup-chart-launch"')
        if setup_launchers == 0:
            self.assertIn("Sector-qualified long setups</b> · None active", setups)
            self.assertIn("Sector-qualified short setups</b> · None active", setups)
        else:
            self.assertGreater(setup_launchers, 0)
        updater = (ROOT / "scripts" / "update-trading-scan.py").read_text()
        self.assertIn('sync_sections(["setups"])', updater)
        self.assertIn("<title>Momentum", momentum)
        self.assertIn('id="desk-route-heading">Momentum</h1>', momentum)

    def test_trading_nav_has_home_logo_and_vwap_uses_three_columns(self) -> None:
        styles = (ROOT / "trading" / "desk.css").read_text()
        css_hash = hashlib.sha256((ROOT / "trading" / "desk.css").read_bytes()).hexdigest()[:12]
        js_hash = hashlib.sha256((ROOT / "trading" / "desk.js").read_bytes()).hexdigest()[:12]
        self.assertEqual(
            (ROOT / "trading" / f"desk.{css_hash}.css").read_bytes(),
            (ROOT / "trading" / "desk.css").read_bytes(),
        )
        self.assertEqual(
            (ROOT / "trading" / f"desk.{js_hash}.js").read_bytes(),
            (ROOT / "trading" / "desk.js").read_bytes(),
        )
        candidates = [ROOT / "trading" / "index.html", *(ROOT / "trading").glob("*/index.html")]
        pages = sorted({
            path for path in candidates
            if path != ROOT / "trading" / "hypothesis-source" / "index.html"
            and '<nav class="subnav"' in path.read_text()
        })
        self.assertEqual(len(pages), 9)
        stamp_match = re.search(r'<span class="stamp">(.*?)</span>', DESK_HOME.read_text())
        self.assertIsNotNone(stamp_match)
        desk_stamp = stamp_match.group(1) if stamp_match else ""
        model_chips = {}
        for model, label in (("gpt", "GPT"), ("grok", "Grok"), ("fable", "Fable")):
            match = re.search(
                rf'<a class="chip chip-{model} [^"]+" href="/trading/{model}-risk/"[^>]*>{label} [\d.]+</a>',
                DESK_HOME.read_text(),
            )
            self.assertIsNotNone(match)
            model_chips[model] = match.group(0) if match else ""
        for path in pages:
            page = path.read_text()
            self.assertEqual(page.count('class="trade-z-logo" href="/"'), 1, path.as_posix())
            self.assertIn('aria-label="Zonted homepage"', page, path.as_posix())
            self.assertNotRegex(page, r'href="/trading/hypotheses/"[^>]*>Hypotheses</a>')
            self.assertNotRegex(page, r'href="/trading/watchlist/"[^>]*>Watchlist</a>')
            self.assertRegex(page, r'href="/trading/vwap-setups/"[^>]*>VWAP Setups</a>')
            self.assertRegex(page, r'href="/trading/momentum/"[^>]*>Momentum</a>')
            self.assertRegex(page, r'href="/trading/mentality/"[^>]*>Mentality</a>')
            self.assertLess(page.index('href="/trading/mentality/"'), page.index('href="/trading/performance/"'))
            for chip in model_chips.values():
                self.assertIn(chip, page, path.as_posix())
            self.assertNotIn('class="chip chip-gemini ', page, path.as_posix())
            self.assertNotIn('class="chip chip-meta ', page, path.as_posix())
            self.assertIn(f'<span class="stamp">{desk_stamp}</span>', page, path.as_posix())
            self.assertIn(f'/trading/desk.{css_hash}.css', page, path.as_posix())
            self.assertIn(f'/trading/desk.{js_hash}.js', page, path.as_posix())
            self.assertNotRegex(page, r'/trading/desk\.(?:css|js)\?v=')
        self.assertIn(".trade-z-logo", styles)
        self.assertIn(".vwap-chart-grid,.crypto-chart-grid{grid-template-columns:repeat(3,minmax(0,1fr))}", styles)


if __name__ == "__main__":
    unittest.main()
