from __future__ import annotations

import unittest

from rh_radar.pool_math import (
    depth_quote_for_pct,
    round_trip_quote,
    simulate_buy_token_out,
    simulate_sell_quote_out,
    token_amount_for_quote_notional,
)


class PoolMathTests(unittest.TestCase):
    def test_depth_positive_for_live_shaped_state(self):
        # Shape taken from a live RH v3 pool read (WETH token0).
        state = {
            "sqrt_price_x96": 0x6A17B2ADCA290C545C654100A4FA,
            "tick": 0,
            "liquidity": 0x7CBF9D9985F0629C56E,
            "token0": "0x0bd7d308f8e1639fab988df18a8011f41eacad73",
            "token1": "0x1f6510ff5a12c915470bc5f4c8465fe8ef1cae4f",
        }
        depth = depth_quote_for_pct(state, state["token0"], 0.005)
        self.assertGreater(depth, 0)

    def test_sell_sim_returns_nonzero_for_small_input(self):
        state = {
            "sqrt_price_x96": 2**96,  # price = 1
            "tick": 0,
            "liquidity": 10**18,
            "token0": "0xaaaa000000000000000000000000000000000001",
            "token1": "0xbbbb000000000000000000000000000000000002",
        }
        token_in = token_amount_for_quote_notional(state, state["token0"], state["token1"], 10**16)
        out = simulate_sell_quote_out(state, state["token0"], state["token1"], token_in)
        self.assertGreater(out, 0)

    def test_same_block_round_trip_near_par_on_deep_pool(self):
        state = {
            "sqrt_price_x96": 2**96,
            "tick": 0,
            "liquidity": 10**22,
            "token0": "0xaaaa000000000000000000000000000000000001",
            "token1": "0xbbbb000000000000000000000000000000000002",
        }
        quote_in = 10**16
        bought = simulate_buy_token_out(state, state["token0"], state["token1"], quote_in)
        self.assertGreater(bought, 0)
        rt = round_trip_quote(state, state, state["token0"], state["token1"], quote_in)
        # Deep pool + tiny notional → near-par recovery under single-tick model.
        self.assertGreater(rt["gross_multiple"], 0.98)
        self.assertLess(rt["gross_multiple"], 1.02)


if __name__ == "__main__":
    unittest.main()
