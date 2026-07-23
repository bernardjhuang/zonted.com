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

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=executable)

        desktop = browser.new_page(viewport={"width": 1280, "height": 900})
        errors: list[str] = []
        desktop.on("pageerror", lambda error: errors.append(str(error)))
        desktop.goto(args.url, wait_until="networkidle")
        check(desktop.locator(".trading-tab").count() == 6, "expected six tabs")
        check(desktop.locator("h1").inner_text() == "Trading", "missing Trading h1")

        desktop.evaluate("scrollTo(0, 0)")
        desktop.locator("#scan-tab").click()
        check(desktop.evaluate("scrollY") == 0, "tab switch moved the page vertically")
        check(desktop.locator("#bl-tools").is_hidden(), "portfolio tools leaked into Momentum")
        check(desktop.locator("#scan-panel").is_visible(), "Momentum panel did not activate")

        desktop.locator("#scan-universe > summary").click()
        desktop.wait_for_function("document.querySelectorAll('#scan-universe-shell tr.scan-data-row').length > 0")
        first_symbol = desktop.locator("#scan-universe-shell tr.scan-data-row").first.get_attribute("data-scan-symbol")
        desktop.locator("#scan-universe-q").fill(first_symbol or "")
        check(desktop.locator("#scan-universe-shell tr.scan-data-row").count() >= 1, "universe search did not scope results")
        desktop.locator("#scan-universe-q").fill("")
        setup_toggle = desktop.locator("#scan-panel [data-scan-toggle]").first
        if setup_toggle.count():
            detail_id = setup_toggle.get_attribute("aria-controls")
            setup_toggle.click()
            desktop.wait_for_function("id => document.querySelectorAll(`#${id} svg`).length === 2", arg=detail_id)

        desktop.goto(args.url + "#vwap", wait_until="networkidle")
        check(desktop.locator("#vwap-selected-chart .vwap-chart").count() == 0, "VWAP chart loaded before a user selection")
        desktop.locator('[data-vwap-select="SPY"]').first.click()
        desktop.wait_for_function("document.querySelector('#vwap-selected-chart .vwap-chart')?.dataset.sym === 'SPY'")
        desktop.locator('[data-vwap-scope-button="countries"]').click()
        desktop.wait_for_function("document.querySelector('#vwap-selected-chart .vwap-chart')?.dataset.sym === 'EWY'")
        check("vwap=EWY" in desktop.url, "VWAP selected chart missing from URL")

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

        desktop.goto(args.url + "#crypto", wait_until="networkidle")
        check(desktop.locator("#crypto-selected-chart .crypto-card").count() == 0, "Crypto chart loaded before a user selection")
        desktop.locator('[data-crypto-select="ZEC"]').first.click()
        desktop.wait_for_function("document.querySelector('#crypto-selected-chart .crypto-card')?.dataset.symbol === 'ZEC'")
        desktop.locator('[data-crypto-select="ETH"]').first.click()
        desktop.wait_for_function("document.querySelector('#crypto-selected-chart .crypto-card')?.dataset.symbol === 'ETH'")
        check("crypto=ETH" in desktop.url, "Crypto selected chart missing from URL")

        desktop.goto(args.url + "#log", wait_until="networkidle")
        check(desktop.locator("#positions-tab").get_attribute("aria-selected") == "true", "legacy #log did not land on Portfolio")

        desktop.goto(args.url, wait_until="networkidle")
        desktop.locator("#positions-tab").focus()
        desktop.keyboard.press("ArrowRight")
        check(desktop.locator("#scan-tab").get_attribute("aria-selected") == "true", "keyboard tab navigation failed")
        check(not errors, f"browser JavaScript errors: {errors}")

        for route in ("", "#scan", "#vwap", "#congress", "#whales", "#crypto"):
            mobile = browser.new_page(viewport={"width": 390, "height": 844})
            mobile_errors: list[str] = []
            mobile.on("pageerror", lambda error: mobile_errors.append(str(error)))
            mobile.goto(args.url + route, wait_until="networkidle")
            widths = mobile.evaluate("({body: document.body.scrollWidth, html: document.documentElement.scrollWidth, viewport: document.documentElement.clientWidth})")
            check(widths["body"] <= widths["viewport"] and widths["html"] <= widths["viewport"], f"page-level overflow on {route or 'Portfolio'}: {widths}")
            check(mobile.locator(".trading-tab").first.evaluate("node => node.getBoundingClientRect().height") >= 44, "mobile tab target below 44px")
            if not route:
                check(mobile.locator("#bl-q").evaluate("node => node.getBoundingClientRect().height") >= 44, "mobile search target below 44px")
                check(mobile.locator("#bl-export").evaluate("node => node.getBoundingClientRect().height") >= 44, "mobile download target below 44px")
            check(not mobile_errors, f"mobile JavaScript errors on {route or 'Portfolio'}: {mobile_errors}")
            mobile.close()

        browser.close()
    print("Trading browser smoke: PASS (6 tabs, interactions, deep links, mobile overflow, touch targets)")


if __name__ == "__main__":
    main()
