from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from rh_radar.config import DATA, RAW, ensure_data_dirs, load_config
from rh_radar.decode import decode_pons_launch_log
from rh_radar.rpc import block_number, credits_remaining, get_logs

CHECKPOINT = RAW / "harvest_checkpoint.json"
LAUNCHES = DATA / "launches.jsonl"


def _load_checkpoint() -> dict[str, Any]:
    if CHECKPOINT.exists():
        return json.loads(CHECKPOINT.read_text())
    return {"factories": {}}


def _save_checkpoint(cp: dict[str, Any]) -> None:
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    tmp = CHECKPOINT.with_suffix(".tmp")
    tmp.write_text(json.dumps(cp, indent=2, sort_keys=True))
    tmp.replace(CHECKPOINT)


def _append_launches(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    LAUNCHES.parent.mkdir(parents=True, exist_ok=True)
    with LAUNCHES.open("a") as handle:
        for row in rows:
            handle.write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")


def _existing_launch_ids() -> set[str]:
    seen: set[str] = set()
    if not LAUNCHES.exists():
        return seen
    with LAUNCHES.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            seen.add(json.loads(line)["launch_id"])
    return seen


def harvest_factory(
    *,
    name: str,
    address: str,
    start_block: int,
    mechanism_era: str,
    topic0: str,
    end_block: int,
    chunk: int,
) -> int:
    cp = _load_checkpoint()
    factories = cp.setdefault("factories", {})
    state = factories.setdefault(name, {"next_block": start_block, "launches": 0})
    cursor = max(int(state["next_block"]), start_block)
    seen = _existing_launch_ids()
    written = 0
    while cursor <= end_block:
        to_block = min(cursor + chunk - 1, end_block)
        t0 = time.time()
        try:
            logs = get_logs(address, topic0, cursor, to_block)
        except Exception as exc:
            # Adaptive shrink on provider range errors.
            if chunk > 2_000:
                chunk = max(2_000, chunk // 2)
                print(f"[{name}] shrink chunk -> {chunk} after error: {exc}")
                continue
            raise
        rows: list[dict[str, Any]] = []
        for log in logs:
            row = decode_pons_launch_log(log, factory_name=name, mechanism_era=mechanism_era)
            if row["pool"] == "0x0000000000000000000000000000000000000000":
                continue
            if row["launch_id"] in seen:
                continue
            # Timestamps filled by stamp_launches (anchor interpolation or exact).
            row["first_liq_ts"] = None
            row["available_at"] = None
            rows.append(row)
            seen.add(row["launch_id"])
        _append_launches(rows)
        written += len(rows)
        state["next_block"] = to_block + 1
        state["launches"] = int(state.get("launches", 0)) + len(rows)
        state["last_range"] = [cursor, to_block]
        state["updated_unix"] = int(time.time())
        cp["credits_remaining"] = credits_remaining()
        _save_checkpoint(cp)
        print(
            f"[{name}] {cursor}-{to_block} logs={len(logs)} new={len(rows)} "
            f"dt={time.time()-t0:.2f}s credits={credits_remaining()}"
        )
        cursor = to_block + 1
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Harvest Pons factory launch events (M0 corpus spine)")
    parser.add_argument("--chunk", type=int, default=40_000)
    parser.add_argument("--max-blocks", type=int, default=0, help="Optional cap from each factory cursor")
    parser.add_argument("--to-latest", action="store_true", default=True)
    parser.add_argument("--end-block", type=int, default=0)
    args = parser.parse_args()

    ensure_data_dirs()
    cfg = load_config()
    topic0 = cfg["events"]["pons_launch_final"]["topic0"]
    latest = block_number() if not args.end_block else args.end_block
    total = 0
    for name, meta in cfg["factories"].items():
        start = int(meta["start_block"])
        end = latest
        if args.max_blocks:
            cp = _load_checkpoint()
            cursor = int(cp.get("factories", {}).get(name, {}).get("next_block", start))
            end = min(latest, cursor + args.max_blocks - 1)
        n = harvest_factory(
            name=name,
            address=meta["address"],
            start_block=start,
            mechanism_era=meta["mechanism_era"],
            topic0=topic0,
            end_block=end,
            chunk=args.chunk,
        )
        total += n
    print(f"[done] wrote {total} new launches -> {LAUNCHES}")


if __name__ == "__main__":
    main()
