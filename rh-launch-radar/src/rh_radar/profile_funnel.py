from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from rh_radar.config import DATA, ensure_data_dirs

LAUNCHES = DATA / "launches.jsonl"
LABELS = DATA / "labels" / "outcomes.jsonl"
THRESHOLDS = DATA / "labels" / "thresholds.json"
MEMO = DATA / "scores" / "m0_funnel_memo.json"


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    k = (len(xs) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(xs[int(k)])
    return float(xs[f] * (c - k) + xs[c] * (k - f))


def main() -> None:
    ensure_data_dirs()
    rows = [json.loads(line) for line in LAUNCHES.read_text().splitlines() if line.strip()]
    by_factory = Counter(r["factory_name"] for r in rows)
    by_era = Counter(r["mechanism_era"] for r in rows)
    msg_values = [r.get("msg_value_wei", 0) / 1e18 for r in rows]
    creators = Counter(r["creator"] for r in rows)

    memo = {
        "n_launches": len(rows),
        "by_factory": dict(by_factory),
        "by_era": dict(by_era),
        "unique_creators": len(creators),
        "creators_with_10plus_launches": sum(1 for _, n in creators.items() if n >= 10),
        "msg_value_eth_percentiles": {
            "p10": percentile(msg_values, 0.10),
            "p50": percentile(msg_values, 0.50),
            "p90": percentile(msg_values, 0.90),
            "p99": percentile(msg_values, 0.99),
        },
        "block_range": [min(r["first_liq_block"] for r in rows), max(r["first_liq_block"] for r in rows)],
    }
    if LABELS.exists():
        labels = [json.loads(line) for line in LABELS.read_text().splitlines() if line.strip()]
        memo["labeled_n"] = len(labels)
        memo["high_value_proxy_rate"] = sum(1 for r in labels if r.get("high_value_proxy")) / max(1, len(labels))
        if THRESHOLDS.exists():
            memo["thresholds"] = json.loads(THRESHOLDS.read_text())
    MEMO.parent.mkdir(parents=True, exist_ok=True)
    MEMO.write_text(json.dumps(memo, indent=2, sort_keys=True))
    print(json.dumps(memo, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
