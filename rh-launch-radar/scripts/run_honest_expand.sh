#!/usr/bin/env bash
# Expand honest labels without wiping existing outcomes.jsonl.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a
# shellcheck disable=SC1090
source ~/.config/trading/blockscout.env
set +a
SHARDS="${1:-4}"
LIMIT="${2:-2400}"
OFFSET="${3:-1726}"
mkdir -p data/labels data/raw
# Seed shard files from the merged honest file so --resume skips done ids.
if [[ -f data/labels/honest_outcomes.jsonl ]]; then
  for i in $(seq 0 $((SHARDS - 1))); do
    cp data/labels/honest_outcomes.jsonl "data/labels/honest_outcomes.shard${i}.jsonl"
  done
else
  rm -f data/labels/honest_outcomes.shard*.jsonl
fi
pids=()
for i in $(seq 0 $((SHARDS - 1))); do
  PYTHONPATH=src python3 -u -m rh_radar.honest_labels \
    --limit "$LIMIT" --offset "$OFFSET" --era-prefix pons \
    --shard-index "$i" --shard-count "$SHARDS" \
    --resume \
    --out "data/labels/honest_outcomes.shard${i}.jsonl" \
    2>&1 | tee "data/raw/honest_expand_shard${i}.log" &
  pids+=($!)
done
ec=0
for pid in "${pids[@]}"; do
  wait "$pid" || ec=1
done
if [[ "$ec" -ne 0 ]]; then
  echo "one or more shards failed" >&2
  exit "$ec"
fi
PYTHONPATH=src python3 -u scripts/merge_honest_labels.py
echo "[done] expanded honest labels"
