#!/bin/bash
# Cron: rebase, render all briefs into Brief tab, push.
set -euo pipefail

REPO="/Users/psy/.openclaw/workspace/zonted.com"
cd "$REPO"

# Rebase on origin/main
git fetch origin
git pull --rebase origin main

# Render all briefs (newest-first log)
python3 scripts/update-trading-brief.py

# Commit + push if there are changes
if ! git diff --quiet; then
  git add -A
  git commit -m "Brief tab: auto-update brief log $(date +%Y-%m-%d)"
  git pull --rebase origin main
  git push origin main
fi
