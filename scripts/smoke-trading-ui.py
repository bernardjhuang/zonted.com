#!/usr/bin/env python3
"""Browser smoke for the generated trading decision surface.

Requires Python Playwright. By default it uses the system Chrome on macOS and
expects the repository to be served at http://127.0.0.1:8877/trading/classic/.
"""
from __future__ import annotations

import argparse
import os
import pathlib
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


MAC_CHROME = pathlib.Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8877/trading/classic/")
    parser.add_argument("--chrome", default=os.environ.get("CHROME_BIN"))
    args = parser.parse_args()
    executable = args.chrome or (str(MAC_CHROME) if MAC_CHROME.exists() else None)
    query_separator = '&' if '?' in args.url else '?'
    parsed_url = urlsplit(args.url)
    origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
    gpt_route = f"{origin}/trading/gpt-brief/"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=executable)

        desktop = browser.new_page(viewport={"width": 1280, "height": 900})
        errors: list[str] = []
        desktop.on("pageerror", lambda error: errors.append(str(error)))
        desktop.goto(args.url, wait_until="networkidle")
        check(desktop.locator(".trading-tab").count() == 10, "expected ten tabs")
        tab_ids = desktop.locator(".trading-tab").evaluate_all("tabs => tabs.map(tab => tab.id)")
        check(tab_ids == ["positions-tab", "hypotheses-tab", "brief-tab", "gpt-brief-tab", "grok-brief-tab", "scan-tab", "vwap-tab", "crypto-tab", "risk-tab", "results-tab"], "trading tabs are not grouped correctly or Performance is not rightmost")
        check(desktop.locator("h1").inner_text() == "Trading", "missing Trading h1")
        check(desktop.locator("#bl-tools, #bl-q, #bl-export").count() == 0, "retired portfolio search/export tools remain")
        source_pnl = desktop.evaluate("""() => Object.fromEntries([...document.querySelectorAll('#bl-raw .ticker[data-symbol-pnl]')].map(row => [row.querySelector('.ticker-symbol').textContent.trim(), row.dataset.symbolPnl]))""")
        card_pnl = desktop.evaluate("""() => Object.fromEntries([...document.querySelectorAll('#bl-built [data-position-row]')].map(row => [row.dataset.positionSymbol, row.querySelector('.portfolio-card-head .mono').textContent.trim()]))""")
        check(source_pnl == card_pnl and set(card_pnl) == {"ABT", "HOOD"}, "portfolio cards do not show combined equity + option P&L")
        position_toggles = desktop.locator("#bl-built [data-position-chart-toggle]")
        check(position_toggles.count() >= 1, "expected at least one live position setup")
        check(position_toggles.evaluate_all("nodes => nodes.every(node => node.getAttribute('aria-expanded') === 'false')"), "live position setups are not collapsed by default")
        check(desktop.locator("#bl-built [data-position-chart-detail]").evaluate_all("nodes => nodes.every(node => node.hidden && node.querySelectorAll('svg').length === 0)"), "collapsed position charts rendered eagerly")
        first_position_toggle = position_toggles.first
        first_position_toggle.click()
        first_position_detail = desktop.locator(f"#{first_position_toggle.get_attribute('aria-controls')}")
        desktop.wait_for_function("id => document.querySelectorAll(`#${id} svg`).length === 2", arg=first_position_toggle.get_attribute("aria-controls"))
        check(first_position_toggle.get_attribute("aria-expanded") == "true" and first_position_detail.is_visible(), "position setup did not open on demand")
        check("Hide setup" in first_position_toggle.inner_text(), "open position setup did not expose the hide action")
        first_position_toggle.click()
        check(first_position_toggle.get_attribute("aria-expanded") == "false" and first_position_detail.is_hidden(), "position setup did not collapse")
        check("View setup" in first_position_toggle.inner_text(), "collapsed position setup did not expose the view action")
        hims_card = desktop.locator("#bl-built [data-position-row][data-position-symbol='HIMS']")
        check(hims_card.count() == 0, "HIMS still appears as a live portfolio position")
        activity = desktop.locator("#bl-log-built details.activity-disclosure")
        check(activity.count() == 1 and not activity.evaluate("node => node.open"), "Recent activity is not folded by default")
        activity.locator("summary").click()
        check(activity.evaluate("node => node.open"), "Recent activity did not expand")
        check(activity.locator(".activity-row-compact").count() == 20, "Recent activity does not show the latest 20 trades")
        check(activity.locator(".activity-side").count() == 20 and activity.locator(".activity-pnl-compact").count() == 20, "Recent activity is missing direction/type/P&L")

        desktop.goto(args.url + "#hypotheses", wait_until="networkidle")
        check(desktop.locator("#hypotheses-tab").get_attribute("aria-selected") == "true", "Hypotheses deep link did not activate")
        hims_hypothesis = desktop.locator("#hypotheses-panel [data-hypothesis-symbol='HIMS']")
        check(hims_hypothesis.count() == 1, "HIMS hypothesis is missing")
        check("THESIS ONLY" in hims_hypothesis.inner_text(), "HIMS is not labeled thesis-only")
        check("below $25" in hims_hypothesis.inner_text() and "next PCAC meeting date" in hims_hypothesis.inner_text(), "HIMS thesis monitoring triggers are missing")
        check(desktop.locator("#hypotheses-panel [data-hypothesis-symbol='ABT']").count() == 1, "ABT hypothesis is missing")
        check(desktop.locator("#hypotheses-panel [data-hypothesis-symbol='HOOD']").count() == 1, "HOOD hypothesis is missing")
        check(desktop.locator("#hypotheses-panel [data-hypothesis-symbol='BYDDY']").count() == 1, "BYDDY hypothesis is missing")
        check(desktop.locator("#hypotheses-panel [data-hypothesis-symbol='NTDOY']").count() == 1, "NTDOY hypothesis is missing")
        check(desktop.locator("#hypotheses-panel [data-hypothesis-symbol='RBLX']").count() == 1, "RBLX hypothesis is missing")
        for symbol in ("abt", "hood", "hims", "byddy", "ntdoy", "rblx"):
            check(desktop.locator(f"#hypothesis-{symbol}-setup").is_visible(), f"{symbol.upper()} setup is not unfolded")
            check(desktop.locator(f"#hypothesis-{symbol}-setup .hypothesis-block").count() == 6, f"{symbol.upper()} setup is incomplete")
            check(desktop.locator(f"#hypothesis-{symbol}-setup [data-thesis-scan='benefit']").count() == 1, f"{symbol.upper()} benefit scan is missing")
            check(desktop.locator(f"#hypothesis-{symbol}-setup [data-thesis-scan='threat']").count() == 1, f"{symbol.upper()} threat scan is missing")
        check("below $25" in desktop.locator("#hypotheses-panel").inner_text(), "HIMS price trigger is missing")
        desktop.goto(f"{origin}/trading/hypotheses/", wait_until="networkidle")
        hypothesis_links = desktop.locator(".hypothesis-chart-link")
        check(hypothesis_links.count() == 6, "not every public hypothesis links to its Momentum chart")
        expected_hypothesis_hrefs = [f"/trading/momentum/?chart={symbol}#scan" for symbol in ("ABT", "HOOD", "HIMS", "BYDDY", "NTDOY", "RBLX")]
        check(hypothesis_links.evaluate_all("links => links.map(link => link.getAttribute('href'))") == expected_hypothesis_hrefs, "hypothesis Momentum chart links are incomplete or misordered")
        desktop.goto(f"{origin}/trading/momentum/?chart=RBLX#scan", wait_until="networkidle")
        desktop.wait_for_function("document.querySelectorAll('[data-scan-detail][data-scan-symbol=\"RBLX\"] svg').length === 2")
        check(desktop.locator("[data-scan-detail][data-scan-symbol='RBLX']").is_visible(), "RBLX hypothesis deep link did not unfold its chart")

        desktop.goto(args.url + "#gpt-brief", wait_until="networkidle")
        check(desktop.locator("#gpt-brief-tab").get_attribute("aria-selected") == "true", "GPT brief deep link did not activate")
        gpt_cards = desktop.locator("#gpt-brief-panel details[data-event-id]")
        check(gpt_cards.count() >= 1, "GPT brief has no event cards")
        check("5 sectors" in desktop.locator("#gpt-brief-panel").inner_text(), "GPT brief sector count is wrong")
        check(gpt_cards.evaluate_all("cards => cards.every(card => !card.open)"), "GPT brief cards are not collapsed by default")
        check(desktop.locator("#gpt-brief-panel .gpt-plain-summary").count() == gpt_cards.count(), "GPT brief cards are missing plain-English summaries")
        check(desktop.locator("#gpt-brief-panel .gpt-market-chart").count() == 0, "GPT charts loaded before a card was opened")
        gpt_cards.first.locator(":scope > summary").click()
        check(gpt_cards.first.evaluate("card => card.open"), "GPT brief card did not open")
        check(gpt_cards.first.locator(".gpt-plain-outcome").count() == 3, "GPT brief quick read is incomplete")
        desktop.wait_for_function("card => card.querySelectorAll('.gpt-market-chart').length === 2", arg=gpt_cards.first.element_handle())
        check(gpt_cards.first.locator(".gpt-market-chart").count() == 2, "GPT brief stock and sector charts are incomplete")
        check(gpt_cards.first.locator(".gpt-market-chart svg[aria-label*='z-score']").count() == 2, "GPT brief charts are missing Z-score context")
        check(gpt_cards.first.locator(".gpt-chart-z").count() >= 2, "GPT brief charts did not draw Z-score history")
        check(gpt_cards.first.locator(".gpt-chart-price").count() == 2, "GPT brief charts did not draw both YTD price histories")
        full_research = gpt_cards.first.locator("details.gpt-full-research")
        check(full_research.count() == 1 and not full_research.evaluate("node => node.open"), "full GPT research is not folded by default")
        full_research.locator("summary").click()
        check("White swan" in full_research.inner_text(), "GPT brief is missing white-swan outcomes")
        check("Black swan" in full_research.inner_text(), "GPT brief is missing black-swan outcomes")

        desktop.goto(gpt_route, wait_until="networkidle")
        routed_card = desktop.locator("#gpt-brief-panel details[data-event-id]").first
        summary_geometry = routed_card.locator(":scope > summary").evaluate("node => { const main = node.querySelector('.gpt-summary-main'); const heading = node.querySelector('.gpt-summary-heading'); const plain = node.querySelector('.gpt-plain-summary'); return { layout: getComputedStyle(node).display, mainGap: parseFloat(getComputedStyle(main).rowGap), headingGap: parseFloat(getComputedStyle(heading).columnGap), plainDisplay: getComputedStyle(plain).display }; }")
        check(summary_geometry["layout"] == "grid" and summary_geometry["mainGap"] >= 7 and summary_geometry["headingGap"] >= 8 and summary_geometry["plainDisplay"] == "block", "GPT brief typography hierarchy collapsed")
        routed_card.locator(":scope > summary").click()
        desktop.wait_for_function("card => card.querySelectorAll('.gpt-market-chart').length === 2", arg=routed_card.element_handle())
        check(routed_card.locator(".gpt-chart-grid").evaluate("node => getComputedStyle(node).gridTemplateColumns.split(' ').length") == 2, "GPT stock and sector charts are not paired on desktop")

        desktop.goto(args.url + "#grok-brief", wait_until="networkidle")
        check(desktop.locator("#grok-brief-tab").get_attribute("aria-selected") == "true", "Grok brief deep link did not activate")
        check(desktop.locator("#grok-brief-panel [data-thesis-id]").count() >= 1, "Grok brief has no thesis cards")
        check("Catalyst chain" in desktop.locator("#grok-brief-panel").inner_text(), "Grok brief is missing catalyst chains")
        check("Agencies scanned" in desktop.locator("#grok-brief-panel").inner_text(), "Grok brief is missing agency scan summary")
        check("Transmission:" in desktop.locator("#grok-brief-panel").inner_text(), "Grok brief is missing transmission sections")

        desktop.evaluate("scrollTo(0, 0)")
        desktop.locator("#scan-tab").click()
        check(desktop.evaluate("scrollY") == 0, "tab switch moved the page vertically")
        check(desktop.locator("#scan-panel").is_visible(), "Momentum panel did not activate")
        check(desktop.locator("#scan-panel .sector-summary details").evaluate("node => node.open"), "Momentum sectors are not expanded by default")
        check(desktop.locator("#scan-panel .scan-sector").count() == 11, "expected eleven formatted sector cards")
        check("no automated risk gate" in desktop.locator("#scan-panel .scan-risk-overlay").inner_text(), "subjective risk-journal notice is missing")

        check(desktop.locator("#scan-universe").evaluate("node => node.open"), "momentum universe is not expanded by default")
        desktop.wait_for_function("document.querySelectorAll('#scan-universe-shell tr.scan-data-row').length > 0")
        check(desktop.locator("#scan-universe-shell .scan-risk-note").count() == 0, "retired automated risk annotations remain")
        day_changes = desktop.locator("#scan-universe-shell tr.scan-data-row").evaluate_all("rows => rows.map(row => Number(row.dataset.dayPct))")
        check(day_changes == sorted(day_changes, reverse=True), "momentum universe is not sorted by day change descending")
        desktop.locator("[data-universe-sort-day]").click()
        day_changes = desktop.locator("#scan-universe-shell tr.scan-data-row").evaluate_all("rows => rows.map(row => Number(row.dataset.dayPct))")
        check(day_changes == sorted(day_changes), "momentum universe day-change sort did not toggle ascending")
        desktop.locator("[data-universe-sort-strength]").click()
        relative_strength = desktop.locator("#scan-universe-shell tr.scan-data-row").evaluate_all("rows => rows.map(row => Number.parseFloat(row.dataset.strength)).filter(Number.isFinite)")
        check(relative_strength == sorted(relative_strength, reverse=True), "momentum universe relative-strength sort did not start descending")
        check(desktop.locator("#scan-universe-shell tr.scan-data-row").last.get_attribute("data-strength") == "", "missing relative strength did not sort last")
        check(desktop.locator("[data-universe-sort-strength]").locator("xpath=..").get_attribute("aria-sort") == "descending", "relative-strength sort state is not exposed")
        desktop.locator("[data-universe-sort-strength]").click()
        relative_strength = desktop.locator("#scan-universe-shell tr.scan-data-row").evaluate_all("rows => rows.map(row => Number.parseFloat(row.dataset.strength)).filter(Number.isFinite)")
        check(relative_strength == sorted(relative_strength), "momentum universe relative-strength sort did not toggle ascending")
        check(desktop.locator("#scan-universe-shell tr.scan-data-row").last.get_attribute("data-strength") == "", "missing relative strength did not stay last")
        first_symbol = desktop.locator("#scan-universe-shell tr.scan-data-row").first.get_attribute("data-scan-symbol")
        desktop.locator("#scan-universe-q").fill(first_symbol or "")
        check(desktop.locator("#scan-universe-shell tr.scan-data-row").count() >= 1, "universe search did not scope results")
        desktop.locator("#scan-universe-q").fill("")
        setup_toggle = desktop.locator("#scan-panel [data-scan-toggle]").first
        if setup_toggle.count():
            detail_id = setup_toggle.get_attribute("aria-controls")
            setup_toggle.click()
            desktop.wait_for_function("id => document.querySelectorAll(`#${id} svg`).length === 2", arg=detail_id)

        desktop.goto(f"{args.url}{query_separator}vwap=EWY#vwap", wait_until="networkidle")
        check(desktop.locator("#vwap-chart-grid .vwap-chart").count() == 13, "expected SPY, eleven US sector charts, and ESPO Gaming")
        check(desktop.locator("#vwap-country-chart-grid .vwap-chart").count() == 10, "expected ten separate country charts")
        check(desktop.locator("#vwap-chart-grid .vwap-chart[data-sym='ESPO']").count() == 1, "ESPO Gaming chart is missing")
        check(desktop.locator("#vwap-panel table").nth(0).locator("tbody tr", has_text="ESPO").count() == 1, "ESPO Gaming summary row is missing")
        us_first = desktop.locator("#vwap-panel table").nth(0).locator("tbody tr").first.locator("td").first.inner_text()
        check(desktop.locator("#vwap-chart-grid .vwap-chart").first.get_attribute("data-sym") == us_first, "US chart order does not match the 50D Z table ranking")
        us_z = desktop.locator("#vwap-panel table").nth(0).locator("tbody tr td:nth-child(3)").evaluate_all("cells => cells.map(cell => Number.parseFloat(cell.textContent))")
        country_z = desktop.locator("#vwap-panel table").nth(1).locator("tbody tr td:nth-child(3)").evaluate_all("cells => cells.map(cell => Number.parseFloat(cell.textContent))")
        check(us_z == sorted(us_z, reverse=True) and country_z == sorted(country_z, reverse=True), "VWAP tables are not sorted by 50D Z descending")
        check(desktop.locator("#vwap-country-chart-grid .vwap-chart").first.get_attribute("data-sym") == "EWY", "country deep-linked chart was not promoted first")
        check(desktop.locator("#vwap-panel table").count() == 2, "expected separate US and country VWAP tables")
        check(desktop.locator("#vwap-panel th", has_text="50D Z").count() == 2, "VWAP tables are missing 50D Z columns")
        check(desktop.locator("#vwap-panel table").evaluate_all("tables => tables.every(table => table.tHead.rows[0].cells[2].textContent.trim() === '50D Z')"), "50D Z is not centered in both VWAP tables")
        check(desktop.locator("#vwap-panel .vwap-chart svg[aria-label*='z-score']").count() == 23, "not every VWAP chart has a Z-score panel")
        check(desktop.locator("#vwap-panel .vwap-z-badge").count() == 23, "not every VWAP chart has a visible 50D Z value")
        check(desktop.locator("[data-vwap-select], [data-vwap-scope-button]").count() == 0, "retired VWAP picker controls remain")

        desktop.goto(f"{args.url}{query_separator}crypto=ETH#crypto", wait_until="networkidle")
        check(desktop.locator("#crypto-chart-grid .crypto-card").count() == 7, "expected all seven crypto charts")
        check(desktop.locator("#crypto-chart-grid .crypto-card").first.get_attribute("data-symbol") == "ETH", "Crypto deep-linked chart was not promoted first")
        check(desktop.locator("#crypto-panel th", has_text="Spread Z vs BTC").count() == 1, "Crypto table is missing the explicit Z-score column")
        check(desktop.locator("[data-crypto-select]").count() == 0, "retired Crypto picker controls remain")

        desktop.goto(args.url + "#risk", wait_until="networkidle")
        check(desktop.locator("#risk-tab").get_attribute("aria-selected") == "true", "Risk deep link did not activate")
        desktop.wait_for_function("document.querySelectorAll('#risk-panel .risk-chart-svg').length === 13")
        check(desktop.locator("#risk-panel .risk-card").count() == 6, "Risk dashboard card set is incomplete")
        check(desktop.locator("#risk-panel .risk-metric").count() == 6, "Risk current-value strip is incomplete")
        risk_score = int(desktop.locator("#risk-panel .risk-score-number").inner_text())
        check(0 <= risk_score <= 100, "Risk score is outside its 0–100 contract")
        check(desktop.locator("#risk-panel .risk-component").count() == 5, "Risk score components are incomplete")
        check(desktop.locator("#risk-panel .risk-component--inactive").count() >= 1, "stale Risk input did not receive zero weight")
        check(desktop.locator("#risk-panel .risk-frequency tbody tr").count() == 4, "Risk conditional frequency table is incomplete")
        check(desktop.locator("#risk-panel .risk-regime").inner_text() in {"Contained", "Watchful", "Elevated"}, "Risk regime is missing")
        check("Conditions Score" in desktop.locator("#risk-panel").inner_text(), "Risk score is mislabeled")
        check("constant-maturity" in desktop.locator("#risk-panel").inner_text(), "Risk curve definition is missing")
        check(desktop.locator("#risk-panel svg[role='img']").count() == 13, "Risk charts lack accessible SVG roles")
        interactive_risk_charts = desktop.locator("#risk-panel .risk-chart-svg[tabindex='0']")
        check(interactive_risk_charts.count() == 13, "Risk charts are not pointer and keyboard interactive")
        check("S&P 500 (SPY)" in desktop.locator("#risk-panel .risk-line-name").nth(0).inner_text(), "SPY context chart is not above Conditions Score")
        check("Conditions Score" in desktop.locator("#risk-panel .risk-line-name").nth(1).inner_text(), "Conditions Score is not aligned below SPY")
        first_risk_chart = interactive_risk_charts.nth(0)
        first_risk_chart.hover(position={"x": 400, "y": 35})
        first_tooltip = first_risk_chart.locator("xpath=..//div[contains(@class,'risk-chart-tooltip')]")
        check(first_tooltip.is_visible(), "Risk chart hover tooltip did not open")
        tooltip_text = first_tooltip.inner_text()
        check("S&P 500 (SPY)" in tooltip_text and "Conditions Score" in tooltip_text and any(month in tooltip_text for month in ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")), "Risk tooltip is missing aligned SPY/Score context")
        first_risk_chart.focus()
        first_risk_chart.press("ArrowLeft")
        check(first_tooltip.is_visible(), "Risk chart keyboard tooltip did not remain open")
        check(desktop.locator("#risk-panel .risk-curve-chart[tabindex='0']").count() == 1, "VIX curve chart is not interactive")
        check(desktop.locator("#risk-panel .risk-commentary li").count() >= 3, "Risk interpretation is incomplete")
        check(desktop.locator("#risk-panel .risk-model-status").count() == 1, "Risk model ship/withhold status is missing")
        check("WITHHELD" in desktop.locator("#risk-panel .risk-model-status").inner_text(), "Failed Risk model was not withheld")
        check("0/4 endpoints passed" in desktop.locator("#risk-panel .risk-model-status").inner_text(), "Risk persistence receipt summary is missing")
        check(desktop.locator("#risk-panel .risk-model-status a[href*='risk-evaluation.json']").count() == 1, "Risk persistence receipt link is missing")

        desktop.goto(args.url + "#results", wait_until="networkidle")
        check(desktop.locator("#results-tab").get_attribute("aria-selected") == "true", "Performance deep link did not activate")
        results_stats = desktop.locator("#results-panel .results-stats")
        check(results_stats.count() == 1 and results_stats.locator(".results-stat").count() == 4, "quantity-free result statistics are incomplete")
        wins = int(results_stats.get_attribute("data-results-wins") or 0)
        losses = int(results_stats.get_attribute("data-results-losses") or 0)
        decided = int(results_stats.get_attribute("data-results-decided") or 0)
        win_rate = float(results_stats.get_attribute("data-results-win-rate") or 0)
        check(decided == wins + losses and round(wins / decided * 100, 1) == win_rate, "win-rate arithmetic is inconsistent")
        check("Quantities and dollar amounts are ignored" in desktop.locator("#results-panel .results-method").inner_text(), "quantity-free method disclosure is missing")

        desktop.goto(args.url + "#log", wait_until="networkidle")
        check(desktop.locator("#positions-tab").get_attribute("aria-selected") == "true", "legacy #log did not land on Portfolio")

        desktop.goto(args.url, wait_until="networkidle")
        desktop.locator("#positions-tab").focus()
        desktop.keyboard.press("ArrowRight")
        check(desktop.locator("#hypotheses-tab").get_attribute("aria-selected") == "true", "keyboard tab navigation skipped Hypotheses")
        desktop.keyboard.press("ArrowRight")
        check(desktop.locator("#brief-tab").get_attribute("aria-selected") == "true", "keyboard tab navigation skipped Brief")
        desktop.keyboard.press("ArrowRight")
        check(desktop.locator("#gpt-brief-tab").get_attribute("aria-selected") == "true", "keyboard tab navigation skipped GPT brief")
        desktop.keyboard.press("ArrowRight")
        check(desktop.locator("#grok-brief-tab").get_attribute("aria-selected") == "true", "keyboard tab navigation skipped Grok brief")
        desktop.keyboard.press("ArrowRight")
        check(desktop.locator("#scan-tab").get_attribute("aria-selected") == "true", "keyboard tab navigation failed")
        check(not errors, f"browser JavaScript errors: {errors}")

        for route in ("", "#hypotheses", "#brief", "#gpt-brief", "#grok-brief", "#scan", "#vwap", "#crypto", "#risk", "#results"):
            mobile = browser.new_page(viewport={"width": 390, "height": 844})
            mobile_errors: list[str] = []
            mobile.on("pageerror", lambda error: mobile_errors.append(str(error)))
            target_url = gpt_route if route == "#gpt-brief" else args.url + route
            mobile.goto(target_url, wait_until="networkidle")
            if route == "#gpt-brief":
                mobile_card = mobile.locator("#gpt-brief-panel details[data-event-id]").first
                mobile_card.locator(":scope > summary").click()
                mobile.wait_for_function("card => card.querySelectorAll('.gpt-market-chart').length === 2", arg=mobile_card.element_handle())
                check(mobile_card.locator(".gpt-chart-grid").evaluate("node => getComputedStyle(node).gridTemplateColumns.split(' ').length") == 1, "GPT stock and sector charts do not stack on mobile")
            widths = mobile.evaluate("({body: document.body.scrollWidth, html: document.documentElement.scrollWidth, viewport: document.documentElement.clientWidth})")
            check(widths["body"] <= widths["viewport"] and widths["html"] <= widths["viewport"], f"page-level overflow on {route or 'Portfolio'}: {widths}")
            if route != "#gpt-brief":
                check(mobile.locator(".trading-tab").first.evaluate("node => node.getBoundingClientRect().height") >= 44, "mobile tab target below 44px")
            check(not mobile_errors, f"mobile JavaScript errors on {route or 'Portfolio'}: {mobile_errors}")
            mobile.close()

        browser.close()
    print("Trading browser smoke: PASS (9 tabs, interactions, deep links, mobile overflow, touch targets)")


if __name__ == "__main__":
    main()
