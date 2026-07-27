#!/usr/bin/env python3
"""Browser smoke test for the merged Trading Desk v3."""
from __future__ import annotations

import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def exercise(page, url: str, screenshot: Path) -> None:
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(url, wait_until="networkidle")
    check(page.locator(".desk-blotter-table").count() == 2, "expected two blotter tables")
    check(page.locator('[data-desk-kind="position"]').count() == 6, "expected six positions")
    check(page.locator('[data-desk-kind="hypothesis"]').count() == 5, "expected five hypotheses")
    check(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "page has horizontal overflow")

    opener = page.locator('[data-desk-kind="position"] .desk-row-toggle').first
    opener.click()
    check(opener.get_attribute("aria-expanded") == "true", "fold-out did not expand")
    check(page.locator(".desk-detail-row:not([hidden])").count() == 1, "fold-out detail not visible")

    chart_opener = page.locator(".desk-detail-row:not([hidden]) [data-hypothesis-chart-open]")
    chart_opener.click()
    page.locator("#hypothesis-chart-dialog[open] .scan-comparison-grid").wait_for()
    check(page.locator("#hypothesis-chart-dialog[open] svg").count() >= 2, "setup dialog did not render both charts")
    page.keyboard.press("Escape")
    check(chart_opener.evaluate("el => document.activeElement === el"), "chart opener did not regain focus")

    thesis_opener = page.locator(".desk-detail-row:not([hidden]) [data-thesis-open]")
    thesis_opener.click()
    page.locator("#desk-thesis-dialog[open] article.hypothesis-detail").wait_for()
    check(page.locator("#desk-thesis-dialog[open] article.hypothesis-detail details[open]").count() >= 1, "full thesis work is not expanded")
    page.locator("[data-thesis-close]").click()
    check(thesis_opener.evaluate("el => document.activeElement === el"), "thesis opener did not regain focus")
    check(not errors, "JavaScript errors: " + "; ".join(errors))
    page.screenshot(path=str(screenshot), full_page=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8107/trading/")
    parser.add_argument("--desktop-shot", default="/tmp/zonted-desk-v3-desktop.png")
    parser.add_argument("--mobile-shot", default="/tmp/zonted-desk-v3-mobile.png")
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        desktop = browser.new_page(viewport={"width": 1440, "height": 1000})
        exercise(desktop, args.url, Path(args.desktop_shot))
        mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        exercise(mobile, args.url, Path(args.mobile_shot))
        browser.close()
    print(f"[smoke] desktop 1440x1000: {args.desktop_shot}")
    print(f"[smoke] mobile 390x844: {args.mobile_shot}")
    print("[smoke] two tables, fold-out, two-chart modal, thesis fetch, focus return, overflow, JS: OK")


if __name__ == "__main__":
    main()
