#!/usr/bin/env python3
"""Browser smoke for the generated trading decision surface.

Requires Python Playwright. By default it uses the system Chrome on macOS and
expects the repository to be served at http://127.0.0.1:8877/trading/.
"""
from __future__ import annotations

import argparse
import os
import pathlib

from playwright.sync_api import sync_playwright


MAC_CHROME = pathlib.Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8877/trading/")
    parser.add_argument("--chrome", default=os.environ.get("CHROME_BIN"))
    args = parser.parse_args()
    executable = args.chrome or (str(MAC_CHROME) if MAC_CHROME.exists() else None)
    query_separator = '&' if '?' in args.url else '?'

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=executable)

        desktop = browser.new_page(viewport={"width": 1280, "height": 900})
        errors: list[str] = []
        desktop.on("pageerror", lambda error: errors.append(str(error)))
        desktop.goto(args.url, wait_until="networkidle")
        check(desktop.locator(".trading-tab").count() == 10, "expected ten tabs")
        tab_ids = desktop.locator(".trading-tab").evaluate_all("tabs => tabs.map(tab => tab.id)")
        check(tab_ids == ["positions-tab", "hypotheses-tab", "brief-tab", "scan-tab", "vwap-tab", "congress-tab", "whales-tab", "youtube-tab", "crypto-tab", "results-tab"], "trading tabs are not grouped correctly or Performance is not rightmost")
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

        desktop.evaluate("scrollTo(0, 0)")
        desktop.locator("#scan-tab").click()
        check(desktop.evaluate("scrollY") == 0, "tab switch moved the page vertically")
        check(desktop.locator("#scan-panel").is_visible(), "Momentum panel did not activate")
        check(desktop.locator("#scan-panel .sector-summary details").evaluate("node => node.open"), "Momentum sectors are not expanded by default")
        check(desktop.locator("#scan-panel .scan-sector").count() == 11, "expected eleven formatted sector cards")

        check(desktop.locator("#scan-universe").evaluate("node => node.open"), "momentum universe is not expanded by default")
        desktop.wait_for_function("document.querySelectorAll('#scan-universe-shell tr.scan-data-row').length > 0")
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

        desktop.goto(args.url + "#congress", wait_until="networkidle")
        congress_cards = desktop.locator("#congress-panel details.whale-card")
        check(congress_cards.count() >= 2, "expected at least two Congress member disclosures")
        congress_cards.nth(0).locator("summary").click()
        congress_cards.nth(1).locator("summary").click()
        check(not congress_cards.nth(0).evaluate("node => node.open") and congress_cards.nth(1).evaluate("node => node.open"), "Congress accordion allows multiple open cards")

        desktop.goto(args.url + "#whales", wait_until="networkidle")
        cards = desktop.locator("#whales-panel details.whale-card")
        check(cards.count() >= 2, "expected at least two manager disclosures")
        cards.nth(0).locator("summary").click()
        cards.nth(1).locator("summary").click()
        check(not cards.nth(0).evaluate("node => node.open") and cards.nth(1).evaluate("node => node.open"), "manager accordion allows multiple open cards")

        desktop.goto(f"{args.url}{query_separator}crypto=ETH#crypto", wait_until="networkidle")
        check(desktop.locator("#crypto-chart-grid .crypto-card").count() == 7, "expected all seven crypto charts")
        check(desktop.locator("#crypto-chart-grid .crypto-card").first.get_attribute("data-symbol") == "ETH", "Crypto deep-linked chart was not promoted first")
        check(desktop.locator("#crypto-panel th", has_text="Spread Z vs BTC").count() == 1, "Crypto table is missing the explicit Z-score column")
        check(desktop.locator("[data-crypto-select]").count() == 0, "retired Crypto picker controls remain")

        desktop.goto(args.url + "#youtube", wait_until="networkidle")
        check(desktop.locator("#youtube-tab").get_attribute("aria-selected") == "true", "YouTube deep link did not activate")
        check(desktop.locator("#youtube-tickers-shell tbody tr").count() == 141, "YouTube ticker table is incomplete")
        check(desktop.locator("#youtube-creators-shell tbody tr").count() == 25, "YouTube creator table is incomplete")
        check(desktop.locator("#youtube-videos-shell tbody tr").count() == 125, "YouTube source-video table is incomplete")
        check(desktop.locator("#youtube-videos-shell a[href*='youtube.com/watch']").count() == 125, "YouTube source links are incomplete")

        desktop.goto(args.url + "#log", wait_until="networkidle")
        check(desktop.locator("#positions-tab").get_attribute("aria-selected") == "true", "legacy #log did not land on Portfolio")

        desktop.goto(args.url, wait_until="networkidle")
        desktop.locator("#positions-tab").focus()
        desktop.keyboard.press("ArrowRight")
        check(desktop.locator("#hypotheses-tab").get_attribute("aria-selected") == "true", "keyboard tab navigation skipped Hypotheses")
        desktop.keyboard.press("ArrowRight")
        check(desktop.locator("#brief-tab").get_attribute("aria-selected") == "true", "keyboard tab navigation skipped Brief")
        desktop.keyboard.press("ArrowRight")
        check(desktop.locator("#scan-tab").get_attribute("aria-selected") == "true", "keyboard tab navigation failed")
        check(not errors, f"browser JavaScript errors: {errors}")

        for route in ("", "#hypotheses", "#brief", "#scan", "#vwap", "#congress", "#whales", "#crypto", "#results", "#youtube"):
            mobile = browser.new_page(viewport={"width": 390, "height": 844})
            mobile_errors: list[str] = []
            mobile.on("pageerror", lambda error: mobile_errors.append(str(error)))
            mobile.goto(args.url + route, wait_until="networkidle")
            widths = mobile.evaluate("({body: document.body.scrollWidth, html: document.documentElement.scrollWidth, viewport: document.documentElement.clientWidth})")
            check(widths["body"] <= widths["viewport"] and widths["html"] <= widths["viewport"], f"page-level overflow on {route or 'Portfolio'}: {widths}")
            check(mobile.locator(".trading-tab").first.evaluate("node => node.getBoundingClientRect().height") >= 44, "mobile tab target below 44px")
            check(not mobile_errors, f"mobile JavaScript errors on {route or 'Portfolio'}: {mobile_errors}")
            mobile.close()

        browser.close()
    print("Trading browser smoke: PASS (10 tabs, interactions, deep links, mobile overflow, touch targets)")


if __name__ == "__main__":
    main()
