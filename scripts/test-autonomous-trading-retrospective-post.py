#!/usr/bin/env python3
"""Regression checks for the autonomous-trading cron retrospective."""

import json
import re
import struct
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLUG = "autonomous-trading-crons-retrospective"
POST = ROOT / "posts" / SLUG / "index.html"
RECEIPT = POST.parent / "autonomous-trading-retrospective-receipt.png"


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


class AutonomousTradingRetrospectiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = POST.read_text()

    def test_shutdown_outcome_and_honest_boundary_survive(self):
        for phrase in (
            "Seven autonomous-trading crons removed",
            "3 TRADE · 15 NO_TRADE",
            "four closed paper trades",
            "zero authoritative learning rows",
            "+1.96825%",
            "-0.06933%",
            "should not be pooled",
            "The experiment proved that an autonomous agent",
            "not</em> prove a trading edge",
            "passed five of six private public drafts",
            "older August 7 draft failed today’s stricter rules",
            "paper-trading research experiment",
            "used no live capital",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.lower(), self.html.lower())

    def test_all_retired_processes_are_named(self):
        for phrase in (
            "Morning decision",
            "Afternoon decision",
            "Stop/target monitor",
            "EOD report",
            "EOD learning review",
            "Strategy lab",
            "Public journal publisher",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.html)

    def test_full_canonical_manifest_is_present(self):
        details = re.search(
            r"<summary>Complete canonical source manifest — 75 tracked paths</summary>(.*?)</details>",
            self.html,
            re.DOTALL,
        )
        self.assertIsNotNone(details)
        assert details is not None
        self.assertEqual(len(re.findall(r"<code>.*?</code>", details.group(1))), 75)
        for path in (
            "paper_trader.py",
            "observations.py",
            "strategies/sector_pair_reversion.py",
            "tests/test_architecture_boundaries.py",
            ".github/workflows/ci.yml",
        ):
            self.assertIn(f"<code>{path}</code>", details.group(1))

    def test_authorship_and_article_metadata_are_consistent(self):
        self.assertIn('<meta name="author" content="Slo">', self.html)
        self.assertIn('<meta property="og:title" content="I Shut Down My Autonomous Trading Crons — Zonted">', self.html)
        parser = JsonLdParser()
        parser.feed(self.html)
        records = [json.loads("".join(parts)) for parts in parser.buffers]
        article = next(record for record in records if record.get("@type") == "Article")
        self.assertEqual(article["author"]["name"], "Slo")
        self.assertEqual(article["datePublished"], "2026-08-18")
        self.assertEqual(article["dateModified"], "2026-08-18")
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
                self.assertIn("I Shut Down My Autonomous Trading Crons", (ROOT / path).read_text())


if __name__ == "__main__":
    unittest.main()
