#!/usr/bin/env bash
# Expand honest labels without wiping existing outcomes.jsonl.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a
# shellcheck disable=SC1090
source ~/.config/trading/blockscout.env
set +a
SHARDS="${1:-8}"
LIMIT="${2:-6516}"
OFFSET="${3:-0}"
FAST_1H="${4:-1}"  # 1 = --fast-1h (entry + T+1h only)
mkdir -p data/labels data/raw
KEEP="${TMPDIR:-/tmp}/honest_outcomes.keep.$$.jsonl"
if [[ -f data/labels/honest_outcomes.keep.jsonl ]]; then
  cp data/labels/honest_outcomes.keep.jsonl "$KEEP"
elif [[ -f data/labels/honest_outcomes.jsonl ]]; then
  cp data/labels/honest_outcomes.jsonl "$KEEP"
else
  : >"$KEEP"
fi
# Seed shards from prior labels so --resume skips already-labeled launch_ids.
for i in $(seq 0 $((SHARDS - 1))); do
  cp "$KEEP" "data/labels/honest_outcomes.shard${i}.jsonl"
done
rm -f data/labels/honest_outcomes.shard*.jsonl.tmp
EXTRA=()
if [[ "$FAST_1H" == "1" ]]; then
  EXTRA+=(--fast-1h)
fi
pids=()
for i in $(seq 0 $((SHARDS - 1))); do
  PYTHONPATH=src python3 -u -m rh_radar.honest_labels \
    --limit "$LIMIT" --offset "$OFFSET" --era-prefix pons \
    --shard-index "$i" --shard-count "$SHARDS" \
    --resume \
    "${EXTRA[@]}" \
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
  rm -f "$KEEP"
  exit "$ec"
fi
# Union prior + shard outputs (dedupe by launch_id).
PYTHONPATH=src python3 -u scripts/merge_honest_labels.py "$KEEP" data/labels/honest_outcomes.shard*.jsonl
PYTHONPATH=src python3 -u -m rh_radar.honest_labels --derive-short-exits-only
rm -f "$KEEP"
echo "[done] expanded honest labels"
