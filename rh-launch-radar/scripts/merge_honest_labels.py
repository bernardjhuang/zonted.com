#!/usr/bin/env python3
"""Merge sharded honest_outcomes*.jsonl and freeze thresholds."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from rh_radar.config import DATA
from rh_radar.honest_labels import (
    ENTRY_OFFSET_SEC,
    EXIT_MIN_RECOVERY,
    EXIT_OFFSET_SEC,
    NOTIONAL_USD,
    RUG_MARK_DRAWDOWN,
    RUG_SELL_RECOVERY,
    RUG_TVL_USD,
    WIN_MULTIPLE,
)

HONEST = DATA / "labels" / "honest_outcomes.jsonl"
THRESHOLDS = DATA / "labels" / "honest_thresholds.json"


def pct(xs: list[float], p: float) -> float | None:
    if not xs:
        return None
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * p
    f, c = int(math.floor(k)), int(math.ceil(k))
    if f == c:
        return xs[f]
    return xs[f] * (c - k) + xs[c] * (k - f)


def main() -> None:
    paths = [Path(p) for p in sys.argv[1:]]
    if not paths:
        paths = sorted((DATA / "labels").glob("honest_outcomes.shard*.jsonl"))
    if not paths:
        raise SystemExit("no shard files found")
    by_id: dict[str, dict] = {}
    for path in paths:
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            by_id[row["launch_id"]] = row
    written = sorted(by_id.values(), key=lambda r: r["first_liq_block"])
    HONEST.parent.mkdir(parents=True, exist_ok=True)
    with HONEST.open("w") as handle:
        for row in written:
            handle.write(json.dumps(row, separators=(",", ":"), sort_keys=True) + "\n")

    split = int(len(written) * 0.7)
    dev = written[:split]
    multiples = [
        float(r["gross_multiple"])
        for r in dev
        if r.get("entry_ok") and isinstance(r.get("gross_multiple"), (int, float))
    ]
    multiples.sort()
    thresholds = {
        "threshold_version": "honest-v1",
        "n_total": len(written),
        "n_dev": len(dev),
        "notional_usd": NOTIONAL_USD,
        "entry_offset_sec": ENTRY_OFFSET_SEC,
        "exit_offset_sec": EXIT_OFFSET_SEC,
        "win_multiple_frozen": WIN_MULTIPLE,
        "exit_min_recovery": EXIT_MIN_RECOVERY,
        "rug_sell_recovery": RUG_SELL_RECOVERY,
        "rug_mark_drawdown": RUG_MARK_DRAWDOWN,
        "rug_tvl_usd": RUG_TVL_USD,
        "dev_gross_multiple": {
            "p50": pct(multiples, 0.50),
            "p80": pct(multiples, 0.80),
            "p90": pct(multiples, 0.90),
            "p95": pct(multiples, 0.95),
        },
        "counts": {
            "executable_winner_250": sum(1 for r in written if r.get("executable_winner_250")),
            "rug": sum(1 for r in written if r.get("rug")),
            "executable_exit": sum(1 for r in written if r.get("executable_exit")),
            "entry_ok": sum(1 for r in written if r.get("entry_ok")),
        },
        "notes": (
            "Binary winner uses frozen 3× band from spec (not a percentile). "
            "Continuous primary label is rt_log_return_250. "
            "Single-tick v3 math capped by quote-side TVL."
        ),
    }
    THRESHOLDS.write_text(json.dumps(thresholds, indent=2, sort_keys=True))
    print(json.dumps(thresholds, indent=2, sort_keys=True))
    print(f"[done] merged={len(written)} from {len(paths)} shards -> {HONEST}")


if __name__ == "__main__":
    main()
