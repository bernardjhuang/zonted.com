#!/usr/bin/env python3
"""Browser smoke test for the merged Trading Desk v3."""
from __future__ import annotations

import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright


LINKED_ROUTES = (
    ("themes/", "Themes"),
    ("vwap-setups/", "VWAP Setups"),
    ("momentum/", "Momentum"),
    ("mentality/", "Mentality"),
    ("performance/", "Performance"),
    ("gpt-risk/", "GPT Risk"),
    ("grok-risk/", "Grok Risk"),
    ("fable-risk/", "Fable Risk"),
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def exercise(page, url: str, screenshot: Path) -> None:
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(url, wait_until="networkidle")
    check(page.locator(".desk-rail").count() == 0, "retired Desk rail remains")
    check(page.locator(".sector-chip--leader").count() == 2, "expected two leading-sector pills")
    check(page.locator(".sector-chip--laggard").count() == 2, "expected two lagging-sector pills")
    check(page.locator(".desk-blotter-table").count() == 2, "expected two blotter tables")
    position_count = page.locator('[data-desk-kind="position"]').count()
    hypothesis_count = page.locator('[data-desk-kind="hypothesis"]').count()
    source_count = int(page.locator('.desk-main').get_attribute('data-desk-source-articles') or 0)
    check(position_count > 0 and position_count + hypothesis_count == source_count, "live positions and tracked hypotheses do not partition the source universe")
    risk_text = page.locator('.desk-risk-strip').inner_text()
    check(all(label in risk_text for label in ("Gross Δ$", "Net Δ$", "Premium risk", "Θ/day")), "Positions risk strip is incomplete")
    check("Cash liquidity" in risk_text or "Margin debit" in risk_text, "Positions risk strip has no signed cash/debit metric")
    check(page.locator('.desk-sleeve-strip').count() == 1, "sleeve risk rollup is missing")
    exposures = page.locator('[data-desk-kind="position"]').evaluate_all("rows => rows.map(row => Number(row.dataset.exposurePercent))")
    check(exposures == sorted(exposures, reverse=True), "positions are not sorted by delta-dollar exposure descending")
    check(page.locator('.desk-position-exposure').count() == position_count, "position exposures are missing")
    check(page.locator("th", has_text="Beta").count() == 2, "Beta is missing from one or both tables")
    check(page.locator("th", has_text="IV").count() == 0, "legacy IV column remains")
    check(page.locator("th", has_text="P&L").count() == 0, "P&L column should be removed")
    flair_count = page.locator(".desk-position-flair--momentum, .desk-position-flair--thesis").count()
    check(flair_count == position_count, "each live position needs exactly one authored flair")
    if page.locator('[data-desk-kind="position"][data-desk-symbol="FRMI"]').count():
        check(page.locator('[data-desk-symbol="FRMI"] .desk-position-flair--thesis').count() == 1, "FRMI thesis flair is missing")
    check(page.locator(".desk-catalyst b").first.inner_text().strip() != "", "catalyst name is missing")
    check(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), "page has horizontal overflow")

    spark = page.locator('[data-desk-kind="position"] .desk-ytd').first
    spark_svg = spark.locator("svg")
    spark_box = spark_svg.bounding_box()
    if spark_box is None:
        raise AssertionError("one-year spark chart has no rendered bounds")
    check(spark_box["width"] >= 230 and spark_box["height"] >= 84, "one-year spark chart was not doubled in size")
    spark_axes = spark.locator(".desk-ytd-axis-label")
    check(spark_axes.count() == 6, "spark chart needs three price ticks and three date ticks")
    check((spark_axes.first.text_content() or "").startswith("$"), "spark chart Y axis is missing price labels")
    if (page.viewport_size or {}).get("width", 0) <= 500:
        spark_svg.focus()
        spark_svg.press("ArrowLeft")
    else:
        spark_svg.hover(position={"x": spark_box["width"] * .58, "y": spark_box["height"] * .5})
    spark_tooltip = spark.locator("[data-desk-ytd-tooltip]:not([hidden])")
    spark_tooltip.wait_for()
    spark_text = spark_tooltip.inner_text()
    check("Day" in spark_text and "Trailing 1Y" in spark_text, "spark chart hover metrics are incomplete")
    check("vs entry" not in spark_text, "private execution-entry metric leaked into the public chart")

    opener = page.locator('[data-desk-kind="position"] .desk-row-toggle').first
    opener.click()
    check(opener.get_attribute("aria-expanded") == "true", "fold-out did not expand")
    check(page.locator(".desk-detail-row:not([hidden])").count() == 1, "fold-out detail not visible")
    history_chart = page.locator(".desk-detail-row:not([hidden]) .desk-detail-chart")
    check(history_chart.locator("figcaption").inner_text().startswith("1 year"), "detail chart is not one-year")
    axis_labels = history_chart.locator(".desk-detail-axis-label")
    check(axis_labels.count() == 7, "detail chart needs four price ticks and three date ticks")
    check((axis_labels.first.text_content() or "").startswith("$"), "detail Y axis is missing price labels")
    svg_box = history_chart.locator("svg").bounding_box()
    if svg_box is None:
        raise AssertionError("detail chart has no rendered bounds")
    check(svg_box["height"] >= 200, "detail chart is too small")
    if (page.viewport_size or {}).get("width", 0) <= 500:
        history_chart.locator("svg").focus()
        history_chart.locator("svg").press("ArrowLeft")
    else:
        history_chart.locator("svg").hover(position={"x": max(12, svg_box["width"] * .65), "y": svg_box["height"] * .5})
    tooltip = history_chart.locator("[data-desk-chart-tooltip]:not([hidden])")
    tooltip.wait_for()
    tooltip_text = tooltip.inner_text()
    check("Day" in tooltip_text and "1Y path" in tooltip_text, "hover metrics are incomplete")

    check(page.locator(".desk-detail-row:not([hidden]) [data-hypothesis-chart-open]").count() == 0, "setup chart action still lives in the fold-out")
    for selector in ('[data-desk-kind="position"] .desk-chart-cell-button', '[data-desk-kind="hypothesis"] .desk-chart-cell-button'):
        chart_opener = page.locator(selector).first
        chart_opener.click()
        page.locator("#hypothesis-chart-dialog[open] svg").nth(1).wait_for()
        check(page.locator("#hypothesis-chart-dialog[open] svg").count() >= 2, "setup dialog did not render both charts")
        page.keyboard.press("Escape")
        check(chart_opener.evaluate("el => document.activeElement === el"), "chart opener did not regain focus")

    thesis_opener = page.locator(".desk-main-row [data-thesis-open]").first
    thesis_opener.click()
    page.locator("#desk-thesis-dialog[open] article.hypothesis-detail").wait_for()
    thesis_details = page.locator("#desk-thesis-dialog[open] article.hypothesis-detail details")
    check(thesis_details.count() >= 1, "full thesis work disclosure is missing")
    check(page.locator("#desk-thesis-dialog[open] article.hypothesis-detail details[open]").count() == 0, "full thesis work should be folded by default")
    thesis_details.first.locator("summary").click()
    check(thesis_details.first.get_attribute("open") is not None, "full thesis work disclosure did not open")
    page.locator("[data-thesis-close]").click()
    check(thesis_opener.evaluate("el => document.activeElement === el"), "thesis opener did not regain focus")
    check(not errors, "JavaScript errors: " + "; ".join(errors))
    page.screenshot(path=str(screenshot), full_page=True)


def exercise_linked_routes(page, origin: str) -> None:
    for route, heading in LINKED_ROUTES:
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(f"{origin}/trading/{route}", wait_until="networkidle")
        check(page.locator("h1").inner_text() == heading, f"{route} heading is wrong")
        check(page.locator('.subnav a[aria-current="page"]').count() <= 1, f"{route} has ambiguous navigation state")
        if route == "mentality/":
            check(page.locator(".mentality-rule").count() == 8, "Mentality needs all eight current lessons")
            check(page.locator(".mentality-tactical-card").count() == 1, "Mentality needs one tactical learning")
            check(page.locator('.mentality-tactical-card[href="/posts/mdb-option-expiry-date-risk/"]').count() == 1, "Tactical learning must link to the MDB trade post")
        if route == "autonomous/":
            check(page.locator(".autonomous-entry").count() >= 1, "Autonomous needs at least one journal entry")
            check(page.locator(".autonomous-reviews article").count() >= 2, "Autonomous needs dual-review receipts")
            check("PAPER ONLY" in page.locator(".autonomous-entry").first.inner_text(), "Autonomous must disclose paper mode")
        check(page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), f"{route} has horizontal overflow")
        check(not errors, f"{route} JavaScript errors: " + "; ".join(errors))


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
        origin = args.url.split("/trading/", 1)[0]
        exercise_linked_routes(desktop, origin)
        mobile = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True)
        exercise(mobile, args.url, Path(args.mobile_shot))
        exercise_linked_routes(mobile, origin)
        browser.close()
    print(f"[smoke] desktop 1440x1000: {args.desktop_shot}")
    print(f"[smoke] mobile 390x844: {args.mobile_shot}")
    print(f"[smoke] Desk interactions + {len(LINKED_ROUTES)} linked routes, desktop/mobile overflow and JS: OK")


if __name__ == "__main__":
    main()
