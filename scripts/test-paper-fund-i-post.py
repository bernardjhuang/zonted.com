#!/usr/bin/env python3
"""Regression checks for the Paper Fund I launch post's implementation claims."""

import json
import struct
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POST = ROOT / "posts" / "introducing-autonomous-agent-paper-fund-i-slo" / "index.html"
RECEIPT = POST.parent / "paper-fund-i-receipt.png"


class StructuredDataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_json_ld = False
        self.buffers: list[list[str]] = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "script" and values.get("type") == "application/ld+json":
            self.in_json_ld = True
            self.buffers.append([])

    def handle_endtag(self, tag):
        if tag == "script" and self.in_json_ld:
            self.in_json_ld = False

    def handle_data(self, data):
        if self.in_json_ld:
            self.buffers[-1].append(data)


class PaperFundIPostTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = POST.read_text()

    def test_corrected_methodology_and_current_state_are_explicit(self):
        required = (
            "IMPLEMENTATION AUDIT UPDATE",
            "Four executable-style Tier 1 scanners and one measurement-only module",
            "Each eligible executable-style Tier 1 signal attempts one same-sector matched control when a suitable peer exists",
            "Every registered Tier 1 signal is evaluated through four documentation-only exit policies",
            "remain explicitly <code>not_triggered</code> in registered counts; they do not receive a fabricated R outcome",
            "no learning-ledger verdict has been generated",
            "No family has produced <code>PROMOTE</code>, <code>RETIRE</code>, <code>CONTINUE</code>, or <code>REDESIGN_HORIZON</code>",
            "Automatic scheduling and review application are not wired yet",
            "Applying a review is still manual",
            "Final public learning-export and site wiring behind a strict output allowlist",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.html)

    def test_strategy_review_prompt_contract_is_not_conflated_with_code_verdicts(self):
        required = (
            "current_strategies, new_strategy_hypotheses",
            "autonomous_learning_plan, independent_findings",
            "agreements, accepted_changes, highest_value_change",
            "Each current strategy and new hypothesis must define a frozen experiment",
            "Promotion and retirement rules live in <code>autonomous_learning_plan</code>",
            "is not the deterministic learning-ledger verdict, a publication approval, or permission to trade",
            "review_learning.apply_review()",
        )
        for phrase in required:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.html)

    def test_stale_overstatements_cannot_return(self):
        forbidden = (
            "Five deterministic strategy scanners",
            "Five deterministic scanners form the initial research board",
            "Every signal gets a <strong>1:1 matched-sector control</strong>",
            "5 strategy families",
            "Four things remain unfinished",
            "Accepted changes are hash-bound to the reviewed input and written to a rule-change ledger",
            "adversarially reviewed evidence",
            "five shadow strategies",
        )
        for phrase in forbidden:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, self.html)

    def test_authorship_disclosure_and_sibling_post_survive(self):
        self.assertIn('<meta name="author" content="Slo">', self.html)
        self.assertIn("Autonomous Agent Paper Fund I is a paper-trading research experiment", self.html)
        self.assertIn("/posts/introducing-autonomous-agent-paper-fund-ii-psy/", self.html)

    def test_article_structured_data_has_modified_date_and_slo_author(self):
        parser = StructuredDataParser()
        parser.feed(self.html)
        records = [json.loads("".join(parts)) for parts in parser.buffers]
        article = next(record for record in records if record.get("@type") == "Article")
        self.assertEqual(article["author"]["name"], "Slo")
        self.assertEqual(article["datePublished"], "2026-08-08")
        self.assertEqual(article["dateModified"], "2026-08-08")

    def test_receipt_is_real_1200_by_630_png(self):
        raw = RECEIPT.read_bytes()
        self.assertEqual(raw[:8], b"\x89PNG\r\n\x1a\n")
        width, height = struct.unpack(">II", raw[16:24])
        self.assertEqual((width, height), (1200, 630))
        self.assertGreater(len(raw), 20_000)


if __name__ == "__main__":
    unittest.main()
