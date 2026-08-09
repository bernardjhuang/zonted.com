from __future__ import annotations

from typing import Any

from eth_hash.auto import keccak


def launch_id(token: str, pool: str) -> str:
    raw = bytes.fromhex(token[2:].lower() + pool[2:].lower())
    return "0x" + keccak(raw).hex()[:16]


def topic_address(topic: str) -> str:
    return "0x" + topic[-40:].lower()


def word_address(data_hex: str, index: int) -> str:
    raw = data_hex[2:] if data_hex.startswith("0x") else data_hex
    word = raw[index * 64 : (index + 1) * 64]
    if len(word) < 64:
        raise ValueError("data too short")
    return "0x" + word[-40:].lower()


def word_uint(data_hex: str, index: int) -> int:
    raw = data_hex[2:] if data_hex.startswith("0x") else data_hex
    word = raw[index * 64 : (index + 1) * 64]
    if len(word) < 64:
        raise ValueError("data too short")
    return int(word, 16)


def decode_pons_launch_log(log: dict[str, Any], *, factory_name: str, mechanism_era: str) -> dict[str, Any]:
    topics = log["topics"]
    data = log["data"]
    token = topic_address(topics[1])
    creator = topic_address(topics[2])
    dex_factory = topic_address(topics[3])
    quote = word_address(data, 0)
    pool = word_address(data, 1)
    # Trailing words observed on 2026-08-09 receipts: …, tokenId-ish, …, msg.value
    n_words = len(data[2:]) // 64
    msg_value = word_uint(data, n_words - 1) if n_words >= 1 else 0
    block = int(log["blockNumber"], 16)
    tx = log["transactionHash"]
    return {
        "launch_id": launch_id(token, pool),
        "token": token,
        "pool": pool,
        "creator": creator,
        "quote": quote,
        "dex_factory": dex_factory,
        "factory": log["address"].lower(),
        "factory_name": factory_name,
        "mechanism_era": mechanism_era,
        "first_liq_block": block,
        "tx_hash": tx,
        "log_index": int(log["logIndex"], 16),
        "msg_value_wei": msg_value,
        "source_topic0": topics[0],
    }


def decode_swap_amounts(data_hex: str) -> tuple[int, int]:
    """Return (amount0, amount1) as signed ints from Uniswap v3 Swap data."""
    raw = data_hex[2:] if data_hex.startswith("0x") else data_hex

    def as_int256(word: str) -> int:
        value = int(word, 16)
        if value >= 2**255:
            value -= 2**256
        return value

    amount0 = as_int256(raw[0:64])
    amount1 = as_int256(raw[64:128])
    return amount0, amount1
