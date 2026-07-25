#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import unittest

import sync_trading_desk as sync

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLASSIC = (ROOT / "trading" / "classic" / "index.html").read_text()


class RoutedTradingSyncTests(unittest.TestCase):
    def test_all_routed_pages_are_idempotent(self) -> None:
        for name, route in sync.ROUTES.items():
            current = route.path.read_text()
            self.assertEqual(sync.render_route(current, CLASSIC, route), current, name)
            self.assertIn('<nav class="subnav"', current, name)
            self.assertGreaterEqual(current.count('<div class="wrap">'), 3, name)

    def test_vwap_route_contains_equity_country_and_crypto_surfaces(self) -> None:
        page = (ROOT / "trading" / "vwap" / "index.html").read_text()
        self.assertIn('id="vwap-panel"', page)
        self.assertIn('id="vwap-country-chart-grid"', page)
        self.assertIn('id="crypto-panel"', page)
        self.assertIn('/trading/vwap-charts.json?v=', page)
        self.assertIn('/trading/crypto-charts.json?v=', page)
        self.assertEqual(page.count('id="vwap-chart-grid"'), 1)
        self.assertEqual(page.count('id="crypto-chart-grid"'), 1)
        for panel_id in ("vwap-panel", "crypto-panel"):
            tag = re.search(rf'<section[^>]+id="{panel_id}"[^>]*>', page)
            if tag is None:
                self.fail(f"missing {panel_id}")
            self.assertNotIn(" hidden", tag.group(0))
        broker_hash = hashlib.sha256((ROOT / "js" / "trading-broker-light.js").read_bytes()).hexdigest()[:12]
        self.assertIn(f'/js/trading-broker-light.js?v={broker_hash}', page)
        vwap = json.loads((ROOT / "trading" / "vwap-charts.json").read_text())
        crypto = json.loads((ROOT / "trading" / "crypto-charts.json").read_text())
        self.assertEqual(len(vwap["groups"]["us"]), 13)
        self.assertEqual(len(vwap["groups"]["countries"]), 10)
        self.assertEqual(len(crypto["charts"]), 7)

    def test_gpt_brief_route_loads_the_current_payload(self) -> None:
        page = (ROOT / "trading" / "gpt-brief" / "index.html").read_text()
        payload = ROOT / "trading" / "gpt-brief.json"
        payload_hash = hashlib.sha256(payload.read_bytes()).hexdigest()[:12]
        script_hash = hashlib.sha256((ROOT / "js" / "trading-gpt-brief.js").read_bytes()).hexdigest()[:12]
        self.assertIn(f'/trading/gpt-brief.json?v={payload_hash}', page)
        self.assertIn(f'/js/trading-gpt-brief.js?v={script_hash}', page)
        self.assertIn('id="gpt-brief-shell"', page)
        panel = re.search(r'<section[^>]+id="gpt-brief-panel"[^>]*>', page)
        if panel is None:
            self.fail("missing gpt-brief-panel")
        self.assertNotIn(" hidden", panel.group(0))

    def test_horizon_route_loads_the_current_payload(self) -> None:
        page = (ROOT / "trading" / "horizon" / "index.html").read_text()
        payload = ROOT / "trading" / "horizon.json"
        payload_hash = hashlib.sha256(payload.read_bytes()).hexdigest()[:12]
        script_hash = hashlib.sha256((ROOT / "js" / "trading-horizon.js").read_bytes()).hexdigest()[:12]
        self.assertIn(f'/trading/horizon.json?v={payload_hash}', page)
        self.assertIn(f'/js/trading-horizon.js?v={script_hash}', page)
        self.assertIn('id="horizon-shell"', page)
        self.assertIn('aria-current="page">Horizon</a>', page)
        panel = re.search(r'<section[^>]+id="horizon-panel"[^>]*>', page)
        if panel is None:
            self.fail("missing horizon-panel")
        self.assertNotIn(" hidden", panel.group(0))

    def test_performance_route_matches_classic_results_and_history(self) -> None:
        page = (ROOT / "trading" / "performance" / "index.html").read_text()
        source = re.search(r'<!-- AUTO:RESULTS:START -->(.*?)<!-- AUTO:RESULTS:END -->', CLASSIC, re.S)
        if source is None:
            self.fail("missing classic RESULTS region")
        source_heading = re.search(r'<h2 id="results-heading">([^<]+)</h2>', source.group(1))
        if source_heading is None:
            self.fail("missing classic results heading")
        self.assertIn(f'<h2 id="results-heading">{source_heading.group(1)}</h2>', page)
        results = json.loads((ROOT / "trading" / "results-ytd.json").read_text())
        self.assertIn(f'data-results-points="{len(results["points"])}"', page)
        self.assertIn('id="results-panel"', page)
        panel = re.search(r'<section[^>]+id="results-panel"[^>]*>', page)
        if panel is None:
            self.fail("missing results-panel")
        self.assertNotIn(" hidden", panel.group(0))


if __name__ == "__main__":
    unittest.main()
