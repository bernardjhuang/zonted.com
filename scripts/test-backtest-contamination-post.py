#!/usr/bin/env python3
"""Regression checks for the Sol Fund Revision C contamination post."""

import json
import struct
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG = "sol-fund-revision-c-contamination-lesson"
POST = ROOT / "posts" / SLUG / "index.html"
RECEIPT = POST.parent / "backtest-learned-to-cheat-receipt.png"


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


class BacktestContaminationPostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = POST.read_text()

    def test_receipts_and_non_deployment_boundary_survive(self):
        for phrase in (
            "525 same-window attempts",
            "497 tests passed",
            "178.27%",
            "257.90%",
            "B008 is not deployable",
            "floating-point dust",
            "five sealed historical walk-forward windows",
            "not investment advice",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.lower(), self.html.lower())

    def test_authorship_and_article_metadata_are_consistent(self):
        self.assertIn('<meta name="author" content="Slo">', self.html)
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
                self.assertIn("The Backtest Learned to Cheat", (ROOT / path).read_text())


if __name__ == "__main__":
    unittest.main()
