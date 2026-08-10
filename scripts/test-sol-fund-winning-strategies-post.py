#!/usr/bin/env python3
"""Regression checks for the four Sol Fund winning-strategies comparison post."""

import hashlib
import json
import struct
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG = "sol-fund-winning-strategies-vs-qqq-spy"
POST = ROOT / "posts" / SLUG / "index.html"
RECEIPT = POST.parent / "sol-fund-four-strategies-receipt.png"
COMPARISON = POST.parent / "comparison.json"
COMPARISON_SHA256 = "635a551caee9fc2306aa70b29cb6be827c2636016234e2938d82db873348f698"


class JsonLdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_json_ld = False
        self.buffers: list[list[str]] = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("type") == "application/ld+json":
            self.in_json_ld = True
            self.buffers.append([])

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_json_ld = False

    def handle_data(self, data):
        if self.in_json_ld:
            self.buffers[-1].append(data)


class WinningStrategiesPostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = POST.read_text()
        cls.comparison_raw = COMPARISON.read_bytes()
        cls.comparison = json.loads(cls.comparison_raw)

    def test_strategy_rules_and_honest_boundary_survive(self):
        for phrase in (
            "40% XLK",
            "40% XLE",
            "Permanent 40% XLU core",
            "63-session momentum",
            "skipping the most recent 21 sessions",
            "−0.62%",
            "+28.04%",
            "not financial advice",
            "simulated research performance",
            "Winning a frozen backtest earns the right",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.lower(), self.html.lower())

    def test_hash_bound_comparison_and_rendered_metrics_agree(self):
        self.assertEqual(hashlib.sha256(self.comparison_raw).hexdigest(), COMPARISON_SHA256)
        self.assertEqual(self.comparison["five_year"]["sessions"], 1259)
        self.assertEqual(self.comparison["ytd_2026"]["sessions"], 150)
        for period in ("five_year", "ytd_2026"):
            for group in ("strategies", "benchmarks"):
                for name, results in self.comparison[period][group].items():
                    for cost in ("5bp", "10bp"):
                        expected = f"{results[cost]['total_return'] * 100:+.2f}%"
                        with self.subTest(period=period, name=name, cost=cost):
                            self.assertIn(expected, self.html)

    def test_authorship_and_article_metadata_are_consistent(self):
        self.assertIn('<meta name="author" content="Slo">', self.html)
        self.assertIn('<meta property="article:modified_time" content="2026-08-09">', self.html)
        parser = JsonLdParser()
        parser.feed(self.html)
        records = [json.loads("".join(parts)) for parts in parser.buffers]
        article = next(record for record in records if record.get("@type") == "Article")
        self.assertEqual(article["author"]["name"], "Slo")
        self.assertEqual(article["datePublished"], "2026-08-09")
        self.assertEqual(article["dateModified"], "2026-08-09")
        self.assertEqual(article["url"], f"https://zonted.com/posts/{SLUG}/")

    def test_receipt_is_real_1200_by_630_png(self):
        raw = RECEIPT.read_bytes()
        self.assertEqual(raw[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", raw[16:24]), (1200, 630))
        self.assertGreater(len(raw), 20_000)

    def test_discovery_surfaces_include_the_post(self):
        route = f"/posts/{SLUG}/"
        for path in ("index.html", "posts/index.html", "feed.xml", "sitemap.xml"):
            with self.subTest(path=path):
                self.assertIn(route, (ROOT / path).read_text())
        for path in ("llms.txt", "llms-full.txt"):
            with self.subTest(path=path):
                self.assertIn(
                    "Four ETF Strategies vs. QQQ and SPY: Five-Year and 2026 YTD Results",
                    (ROOT / path).read_text(),
                )


if __name__ == "__main__":
    unittest.main()
