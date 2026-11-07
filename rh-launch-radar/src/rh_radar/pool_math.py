from __future__ import annotations

import math
from typing import Any

from rh_radar.rpc import rpc

Q96 = 2**96


def eth_call(to: str, data: str, block: str | int = "latest") -> str:
    block_tag = block if isinstance(block, str) else hex(block)
    return rpc("eth_call", [{"to": to, "data": data}, block_tag])


def erc20_balance(token: str, owner: str, block: str | int = "latest") -> int:
    data = "0x70a08231" + owner.lower().replace("0x", "").rjust(64, "0")
    return int(eth_call(token, data, block), 16)


def quote_side_tvl_wei(pool: str, quote: str, block: str | int = "latest") -> int:
    """Quote-token balance held by the pool (TVL proxy for V7 floor)."""
    if quote == "0x0000000000000000000000000000000000000000":
        # native ETH pools — not used on Pons v3 WETH path
        return 0
    return erc20_balance(quote, pool, block)


def read_v3_pool_state(pool: str, block: str | int = "latest") -> dict[str, Any]:
    slot0 = eth_call(pool, "0x3850c7bd", block)
    liq = eth_call(pool, "0x1a686502", block)
    token0 = "0x" + eth_call(pool, "0x0dfe1681", block)[-40:]
    token1 = "0x" + eth_call(pool, "0xd21220a7", block)[-40:]
    sqrt_price_x96 = int(slot0[2:66], 16) if slot0.startswith("0x") else int(slot0[:64], 16)
    # slot0 ABI: sqrtPriceX96, tick, observationIndex, observationCardinality, observationCardinalityNext, feeProtocol, unlocked
    raw = slot0[2:]
    tick = int(raw[64:128], 16)
    if tick >= 2**255:
        tick -= 2**256
    liquidity = int(liq, 16)
    return {
        "sqrt_price_x96": sqrt_price_x96,
        "tick": tick,
        "liquidity": liquidity,
        "token0": token0.lower(),
        "token1": token1.lower(),
    }


def quote_is_token0(quote: str, token0: str) -> bool:
    return quote.lower() == token0.lower()


def price_token1_per_token0(sqrt_price_x96: int) -> float:
    if sqrt_price_x96 <= 0:
        return 0.0
    return (sqrt_price_x96 / Q96) ** 2


def depth_quote_for_pct(state: dict[str, Any], quote: str, pct: float = 0.005) -> float:
    """Approximate quote-token notional to move price by ±pct using current-tick liquidity."""
    L = state["liquidity"]
    sqrtP = state["sqrt_price_x96"]
    if L <= 0 or sqrtP <= 0:
        return 0.0
    sqrtP_f = sqrtP / Q96
    sqrtP_up = sqrtP_f * math.sqrt(1.0 + pct)
    sqrtP_down = sqrtP_f / math.sqrt(1.0 + pct)
    # amount0 to move up: L * (sqrtP_up - sqrtP) / (sqrtP * sqrtP_up)
    amount0_up = L * (sqrtP_up - sqrtP_f) / (sqrtP_f * sqrtP_up)
    # amount1 to move down: L * (sqrtP - sqrtP_down)
    amount1_down = L * (sqrtP_f - sqrtP_down)
    if quote_is_token0(quote, state["token0"]):
        # quote is token0: buying meme (token1) consumes token0 on the up move
        return max(0.0, amount0_up)
    # quote is token1
    return max(0.0, amount1_down)


def simulate_sell_quote_out(
    state: dict[str, Any],
    quote: str,
    token: str,
    token_in_wei: int,
) -> int:
    """
    Approximate output quote wei for selling `token_in_wei` of the launch token
    against current-tick liquidity only (conservative).
    """
    L = state["liquidity"]
    sqrtP = state["sqrt_price_x96"] / Q96
    if L <= 0 or sqrtP <= 0 or token_in_wei <= 0:
        return 0
    token_is_token1 = token.lower() == state["token1"].lower()
    # Selling launch token into quote.
    if token_is_token1 and quote_is_token0(quote, state["token0"]):
        # sell token1 -> get token0; price decreases
        # Δamount1 = L * (sqrtP - sqrtP_new)  => sqrtP_new = sqrtP - Δamount1/L
        amount1 = token_in_wei
        sqrtP_new = sqrtP - (amount1 / L)
        if sqrtP_new <= 0:
            return 0
        amount0_out = L * (1 / sqrtP_new - 1 / sqrtP)
        return max(0, int(amount0_out))
    if (not token_is_token1) and (not quote_is_token0(quote, state["token0"])):
        # token is token0, quote is token1; sell token0 -> get token1; price increases
        amount0 = token_in_wei
        # Δamount0 = L * (1/sqrtP - 1/sqrtP_new) with sqrtP_new > sqrtP
        # 1/sqrtP_new = 1/sqrtP - amount0/L
        inv_new = (1 / sqrtP) - (amount0 / L)
        if inv_new <= 0:
            return 0
        sqrtP_new = 1 / inv_new
        amount1_out = L * (sqrtP_new - sqrtP)
        return max(0, int(amount1_out))
    # Same-side weirdness / inverted pairs — unsupported in v0.
    return 0


def token_amount_for_quote_notional(state: dict[str, Any], quote: str, token: str, quote_wei: int) -> int:
    """Convert a quote notional into an approximate token amount at spot."""
    sqrtP = state["sqrt_price_x96"] / Q96
    if sqrtP <= 0 or quote_wei <= 0:
        return 0
    price_t1_per_t0 = sqrtP ** 2
    token_is_token1 = token.lower() == state["token1"].lower()
    if quote_is_token0(quote, state["token0"]) and token_is_token1:
        # quote_wei token0 buys token1 ≈ quote_wei * price
        return int(quote_wei * price_t1_per_t0)
    if (not quote_is_token0(quote, state["token0"])) and (not token_is_token1):
        # quote is token1, token is token0; token0 ≈ quote_wei / price
        return int(quote_wei / price_t1_per_t0) if price_t1_per_t0 else 0
    return 0


def mark_quote_per_token(state: dict[str, Any], quote: str, token: str) -> float:
    """Spot mark: quote wei per 1e18 token wei (human units cancel in ratios)."""
    sqrtP = state["sqrt_price_x96"] / Q96
    if sqrtP <= 0:
        return 0.0
    price_t1_per_t0 = sqrtP ** 2
    token_is_token1 = token.lower() == state["token1"].lower()
    quote_is_t0 = quote_is_token0(quote, state["token0"])
    if quote_is_t0 and token_is_token1:
        # quote/token = token0/token1 = 1/price
        return (1.0 / price_t1_per_t0) if price_t1_per_t0 else 0.0
    if (not quote_is_t0) and (not token_is_token1):
        # quote is token1, token is token0 → quote/token = price
        return float(price_t1_per_t0)
    return 0.0


def simulate_buy_token_out(
    state: dict[str, Any],
    quote: str,
    token: str,
    quote_in_wei: int,
) -> int:
    """
    Approximate token out for spending `quote_in_wei` against current-tick liquidity.
    Mirrors simulate_sell_quote_out (conservative, single-tick).
    """
    L = state["liquidity"]
    sqrtP = state["sqrt_price_x96"] / Q96
    if L <= 0 or sqrtP <= 0 or quote_in_wei <= 0:
        return 0
    token_is_token1 = token.lower() == state["token1"].lower()
    if quote_is_token0(quote, state["token0"]) and token_is_token1:
        # spend token0 -> receive token1; price increases
        amount0 = quote_in_wei
        inv_new = (1 / sqrtP) - (amount0 / L)
        if inv_new <= 0:
            return 0
        sqrtP_new = 1 / inv_new
        amount1_out = L * (sqrtP_new - sqrtP)
        return max(0, int(amount1_out))
    if (not quote_is_token0(quote, state["token0"])) and (not token_is_token1):
        # spend token1 -> receive token0; price decreases
        amount1 = quote_in_wei
        sqrtP_new = sqrtP - (amount1 / L)
        if sqrtP_new <= 0:
            return 0
        amount0_out = L * (1 / sqrtP_new - 1 / sqrtP)
        return max(0, int(amount0_out))
    return 0


def round_trip_quote(
    entry_state: dict[str, Any],
    exit_state: dict[str, Any],
    quote: str,
    token: str,
    quote_in_wei: int,
    *,
    entry_quote_tvl_wei: int | None = None,
    exit_quote_tvl_wei: int | None = None,
) -> dict[str, Any]:
    """Buy at entry state, sell full token inventory at exit state.

    Single-tick math can invent liquidity; cap spend/proceeds by quote-side TVL.
    """
    spend = int(quote_in_wei)
    if entry_quote_tvl_wei is not None:
        # Cannot deploy more quote than the pool holds (conservative).
        spend = min(spend, max(0, int(entry_quote_tvl_wei)))
    token_bought = simulate_buy_token_out(entry_state, quote, token, spend) if spend else 0
    quote_out = simulate_sell_quote_out(exit_state, quote, token, token_bought) if token_bought else 0
    if exit_quote_tvl_wei is not None:
        quote_out = min(int(quote_out), max(0, int(exit_quote_tvl_wei)))
    recovery = (quote_out / quote_in_wei) if quote_in_wei else 0.0
    return {
        "quote_in_wei": int(quote_in_wei),
        "quote_spent_wei": int(spend),
        "token_bought_wei": int(token_bought),
        "quote_out_wei": int(quote_out),
        "gross_multiple": recovery,
        "exit_recovery_vs_entry_notional": recovery,
    }
