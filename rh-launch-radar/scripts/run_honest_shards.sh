#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
set -a
# shellcheck disable=SC1090
source ~/.config/trading/blockscout.env
set +a
SHARDS="${1:-4}"
LIMIT="${2:-800}"
OFFSET="${3:-1726}"
mkdir -p data/labels data/raw
rm -f data/labels/honest_outcomes.shard*.jsonl data/labels/honest_outcomes.jsonl
pids=()
for i in $(seq 0 $((SHARDS - 1))); do
  PYTHONPATH=src python3 -u -m rh_radar.honest_labels \
    --limit "$LIMIT" --offset "$OFFSET" --era-prefix pons \
    --shard-index "$i" --shard-count "$SHARDS" \
    --out "data/labels/honest_outcomes.shard${i}.jsonl" \
    2>&1 | tee "data/raw/honest_shard${i}.log" &
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
PYTHONPATH=src python3 -u -m rh_radar.phase0 --label-field executable_winner_250 2>&1 | tee data/raw/phase0_honest.log
cp data/scores/phase0_report.json data/scores/phase0_report_honest.json
PYTHONPATH=src python3 -u -m rh_radar.backtest --decision-offset 600 --label-field executable_winner_250 --require-veto-survivor 2>&1 | tee data/raw/backtest_honest_surv.log
cp data/scores/backtest_report.json data/scores/backtest_report_honest_surv.json
PYTHONPATH=src python3 -u -m rh_radar.backtest --decision-offset 600 --label-field executable_winner_250 --no-require-veto-survivor 2>&1 | tee data/raw/backtest_honest_all.log
cp data/scores/backtest_report.json data/scores/backtest_report_honest_all.json
python3 -u - <<'PY'
import json
t=json.load(open("data/labels/honest_thresholds.json"))
print("THRESH", t["counts"])
p=json.load(open("data/scores/phase0_report_honest.json"))
print("PHASE0", p["finding_preview"])
print("gate_all", p["all"]["phase0_gate"])
print("gate_surv", (p.get("survivors") or {}).get("phase0_gate"))
print("BT_SURV", json.load(open("data/scores/backtest_report_honest_surv.json"))["promotion"])
print("BT_ALL", json.load(open("data/scores/backtest_report_honest_all.json"))["promotion"])
PY
