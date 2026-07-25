#!/bin/bash
# Cron: 6:30 AM America/Chicago on NYSE trading days — horizon catalyst scan sync.
#
# Example crontab (America/Chicago):
#   30 6 * * 1-5 /Users/psy/.openclaw/workspace/zonted.com/scripts/cron-publish-horizon.sh
#
# The openclaw agent should refresh trading/horizon.json before this runs.
# This script validates, injects classic + routed Horizon surfaces, and pushes.
set -euo pipefail

REPO="${ZONTED_REPO:-/Users/psy/.openclaw/workspace/zonted.com}"
cd "$REPO"

export TZ="${TZ:-America/Chicago}"

# Weekends are never trading days.
dow="$(date +%u)" # 1=Mon … 7=Sun
if [[ "$dow" -gt 5 ]]; then
  echo "[horizon-cron] weekend — skip"
  exit 0
fi

# Common NYSE full closures (month-day). Extend on the openclaw box as needed.
today_md="$(date +%m-%d)"
case "$today_md" in
  01-01|01-19|02-16|04-03|05-25|06-19|07-03|09-07|11-26|12-25)
    echo "[horizon-cron] observed holiday $today_md — skip"
    exit 0
    ;;
esac

git fetch origin
git pull --rebase origin main

python3 scripts/update-trading-horizon.py

if git diff --quiet; then
  echo "[horizon-cron] no changes"
  exit 0
fi

git add \
  trading/horizon.json \
  trading/horizon/index.html \
  trading/classic/index.html \
  js/trading-horizon.js

git commit -m "Horizon tab: trading-day catalyst scan $(date +%Y-%m-%d)"
git pull --rebase origin main
git push origin main
