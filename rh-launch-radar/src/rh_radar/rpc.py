from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.request
from typing import Any

from rh_radar.config import load_api_key, load_config

_CFG = load_config()
_UA = _CFG["user_agent"]
_BASE = _CFG["pro_api_base"].rstrip("/")
_CHAIN = int(_CFG["chain_id"])
_CREDITS_REMAINING: int | None = None


def credits_remaining() -> int | None:
    return _CREDITS_REMAINING


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {load_api_key()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": _UA,
    }


def rpc(method: str, params: list[Any], *, retries: int = 6) -> Any:
    global _CREDITS_REMAINING
    url = f"{_BASE}/{_CHAIN}/json-rpc"
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    last_err: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, data=payload, headers=_headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                rem = response.headers.get("x-credits-remaining")
                if rem is not None:
                    try:
                        _CREDITS_REMAINING = int(rem)
                    except ValueError:
                        pass
                body = json.load(response)
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code in {429, 500, 502, 503, 504} and attempt + 1 < retries:
                time.sleep((2**attempt) * 0.4 + random.random() * 0.3)
                continue
            raise
        if "error" in body and body["error"]:
            last_err = RuntimeError(body["error"])
            message = json.dumps(body["error"])
            if any(x in message.lower() for x in ("timeout", "server", "limit", "500")) and attempt + 1 < retries:
                time.sleep((2**attempt) * 0.4 + random.random() * 0.3)
                continue
            raise RuntimeError(body["error"])
        return body["result"]
    raise RuntimeError(f"RPC {method} failed after retries: {last_err}")


def rest_get(path: str, *, retries: int = 5) -> Any:
    global _CREDITS_REMAINING
    url = f"{_BASE}/{_CHAIN}{path}"
    last_err: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={k: v for k, v in _headers().items() if k != "Content-Type"})
        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                rem = response.headers.get("x-credits-remaining")
                if rem is not None:
                    try:
                        _CREDITS_REMAINING = int(rem)
                    except ValueError:
                        pass
                return json.load(response)
        except urllib.error.HTTPError as exc:
            last_err = exc
            if exc.code in {429, 500, 502, 503, 504} and attempt + 1 < retries:
                time.sleep((2**attempt) * 0.4 + random.random() * 0.3)
                continue
            raise
    raise RuntimeError(f"REST GET {path} failed: {last_err}")


def block_number() -> int:
    return int(rpc("eth_blockNumber", []), 16)


def get_logs(address: str, topic0: str, from_block: int, to_block: int) -> list[dict[str, Any]]:
    result = rpc(
        "eth_getLogs",
        [
            {
                "address": address,
                "fromBlock": hex(from_block),
                "toBlock": hex(to_block),
                "topics": [topic0],
            }
        ],
    )
    if result is None:
        return []
    if not isinstance(result, list):
        raise RuntimeError(f"unexpected eth_getLogs result type: {type(result)}")
    return result


def get_block_timestamp(block: int) -> int:
    result = rpc("eth_getBlockByNumber", [hex(block), False])
    return int(result["timestamp"], 16)


_BLOCK_TS_CACHE: dict[int, int] = {}


def cached_block_timestamp(block: int) -> int:
    if block not in _BLOCK_TS_CACHE:
        _BLOCK_TS_CACHE[block] = get_block_timestamp(block)
    return _BLOCK_TS_CACHE[block]
