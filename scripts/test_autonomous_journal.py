#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "update_autonomous_journal", ROOT / "scripts" / "update-autonomous-journal.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
PUBLISH_SPEC = importlib.util.spec_from_file_location(
    "publish_autonomous_entry", ROOT / "scripts" / "publish-autonomous-entry.py"
)
assert PUBLISH_SPEC is not None and PUBLISH_SPEC.loader is not None
PUBLISHER = importlib.util.module_from_spec(PUBLISH_SPEC)
PUBLISH_SPEC.loader.exec_module(PUBLISHER)


class AutonomousJournalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = json.loads((ROOT / "trading" / "autonomous.json").read_text())
        cls.page = (ROOT / "trading" / "autonomous" / "index.html").read_text()

    def test_current_payload_is_dual_reviewed_and_paper_only(self):
        entries = MODULE.validate(copy.deepcopy(self.payload))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["mode"], "paper")
        self.assertEqual(entries[0]["review_summary"]["public_entry_status"], "PASS")
        reviews = entries[0]["review_summary"]["public_entry_reviews"]
        self.assertTrue(any("Fable" in row["model"] and row["verdict"] == "PASS" for row in reviews))
        self.assertTrue(any("Grok 4.5" in row["model"] and row["verdict"] == "PASS" for row in reviews))

    def test_public_schema_rejects_quantity_price_and_dollars(self):
        for key, value in (
            ("quantity", 10),
            ("entry_price", 100.0),
            ("position_return_pct", 12.1),
            ("open_r_multiple", 2.1),
        ):
            payload = copy.deepcopy(self.payload)
            payload["entries"][0]["positions"][0][key] = value
            with self.assertRaises(ValueError):
                MODULE.validate(payload)
        payload = copy.deepcopy(self.payload)
        payload["entries"][0]["thoughts"].append("Profit was $100")
        with self.assertRaises(ValueError):
            MODULE.validate(payload)

    def test_public_pnl_is_percentage_only(self):
        entry = self.payload["entries"][0]
        self.assertEqual(set(entry["pnl"]), MODULE.PNL_KEYS)
        flattened = json.dumps(self.payload)
        self.assertNotIn("$", flattened)
        for forbidden in MODULE.FORBIDDEN_KEYS:
            self.assertNotIn(f'"{forbidden}"', flattened)

    def test_page_is_rendered_from_source(self):
        entries = MODULE.validate(copy.deepcopy(self.payload))
        block = MODULE.render(entries)
        self.assertIn(block, self.page)
        self.assertIn('<h1>🦥 Autonomous</h1>', self.page)
        self.assertIn('aria-current="page">🦥 Autonomous</a>', self.page)
        self.assertIn('data-entry-count="1"', self.page)
        self.assertIn('2026-08-07 · NO_TRADE', self.page)
        self.assertIn('PLTR', self.page)
        self.assertIn('Position return since entry <b>+12.10%</b>', self.page)
        self.assertIn('Contribution to virtual basis <b>+1.84%</b>', self.page)
        self.assertIn('Realized', self.page)
        self.assertIn('Publication review', self.page)
        self.assertNotIn("position_return_pct", self.page)
        self.assertNotIn("open_r_multiple", self.page)

    def test_nav_and_public_operating_manual_are_exposed(self):
        nav = self.page.split('<nav class="subnav"', 1)[1].split("</nav>", 1)[0]
        self.assertLess(nav.index('href="/trading/">Desk</a>'), nav.index('href="/trading/autonomous/"'))
        self.assertIn('Desk</a><a href="/trading/autonomous/"', nav)
        self.assertIn('>🦥 Autonomous</a>', nav)
        self.assertIn('href="/trading/autonomous-psy/">🦆 Autonomous</a>', nav)
        self.assertLess(self.page.index('id="learning-board"'), self.page.index('class="autonomous-journal"'))
        for required in (
            'id="learning-board"',
            'First code-owned verdict pending',
            '<strong>150</strong><span>frozen equities</span>',
            '<strong>≤1:1</strong><span>matched controls</span>',
            '<strong>4</strong><span>exit arms</span>',
            'level_vwap_reclaim',
            'sector_pair_reversion',
            'quality_meanrev_3lower',
            'gap_fill_reversion',
            'overnight_decomp',
            'id="stack"',
            'How the entire trading stack works',
            'Hard gates that opinions cannot override',
            'Reviewer A · Fable · evidence only',
            'Reviewer B · Grok · quarantined diagnosis',
            'ten newly terminal observations',
            'review_learning.py',
            'public_export.py',
        ):
            self.assertIn(required, self.page)

    def test_publication_review_is_not_presented_as_a_strategy_verdict(self):
        self.assertIn('Publication review', self.page)
        self.assertIn('Publication PASS is not evidence of edge', self.page)
        self.assertNotIn('Every entry requires final PASS reviews from both Fable and Grok 4.5.', self.page)
        self.assertNotIn('Compatible feedback is folded into the next session automatically.', self.page)
        self.assertNotIn('Each reviewer receives the current config, accepted strategy rules', self.page)

    def test_learning_board_discloses_launch_state_and_thresholds(self):
        for required in (
            'No current learning-ledger verdict has been generated yet',
            '<code>PROMOTE</code>, <code>RETIRE</code>, <code>CONTINUE</code>, or <code>REDESIGN_HORIZON</code>',
            'Production replay, reviewer scheduling, forward sample collection, and the final public allowlist wiring remain unfinished.',
            'Effective N ≥ 20',
            'Conservative R &gt; 0',
            'Control lift &gt; 0',
            'Concentration ≤ 30%',
            'Research cannot authorize orders',
        ):
            self.assertIn(required, self.page)

    def test_post_deploy_factual_corrections_are_explicit(self):
        for required in (
            'Core research modules are partially built and unit-tested',
            'Executable-style Tier 1 signals attempt one same-sector matched control when an eligible peer exists',
            'measurement-only and emits no matched-control row',
            'four executable-style Tier 1 scanners plus one measurement-only overnight decomposition scanner',
            'current code records gap direction and ATR, not catalyst class',
            '<code>review_learning.apply_review()</code> can manually validate',
            'Automatic review application is not wired yet',
            'scheduled for the 2026-08-10 paper pilot at standard size',
            'Public erratum',
            'current_strategies, new_strategy_hypotheses, autonomous_learning_plan',
            'Promotion and retirement rules live in autonomous_learning_plan',
        ):
            self.assertIn(required, self.page)
        for overstated in (
            'No strategy has earned <code>PROMOTE</code> or <code>RETIRE</code> yet.',
            'Each scanner emits a frozen signal plus one same-session matched-sector control.',
            'The five implemented scanners above are Tier 1 evidence collectors.',
            'while keeping catalyst class and direction attributable.',
            'The orchestrator validates the reviewer-specific input hash',
            '<span>executable at standard size</span>',
            'The research machinery is built and tested.',
        ):
            self.assertNotIn(overstated, self.page)

    def test_append_only_order_and_unique_ids(self):
        duplicate = copy.deepcopy(self.payload)
        duplicate["entries"].append(copy.deepcopy(duplicate["entries"][0]))
        with self.assertRaises(ValueError):
            MODULE.validate(duplicate)
        out_of_order = copy.deepcopy(self.payload)
        older = copy.deepcopy(out_of_order["entries"][0])
        older["id"] = "older"
        older["published_at"] = "2026-08-06T21:00:00Z"
        out_of_order["entries"].insert(0, older)
        with self.assertRaises(ValueError):
            MODULE.validate(out_of_order)

    def test_publisher_is_idempotent_and_rejects_divergent_duplicate(self):
        same, changed = PUBLISHER.append_entry(
            copy.deepcopy(self.payload), copy.deepcopy(self.payload), MODULE
        )
        self.assertFalse(changed)
        self.assertEqual(same, self.payload)
        divergent = copy.deepcopy(self.payload)
        divergent["entries"][0]["headline"] = "different"
        with self.assertRaises(ValueError):
            PUBLISHER.append_entry(copy.deepcopy(self.payload), divergent, MODULE)

    def test_publisher_prepends_one_newer_reviewed_entry(self):
        incoming = copy.deepcopy(self.payload)
        incoming["entries"][0]["id"] = "20260808-morning-paper-cycle"
        incoming["entries"][0]["published_at"] = "2026-08-08T15:00:00Z"
        combined, changed = PUBLISHER.append_entry(copy.deepcopy(self.payload), incoming, MODULE)
        self.assertTrue(changed)
        self.assertEqual(
            [row["id"] for row in combined["entries"]],
            ["20260808-morning-paper-cycle", "20260807-afternoon-paper-cycle"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
