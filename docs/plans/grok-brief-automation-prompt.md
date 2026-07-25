# Cursor Automation — Grok brief daily refresh

Create at: https://cursor.com/automations/new

## Settings

| Field | Value |
|---|---|
| **Name** | Grok brief — trading-day catalyst scan |
| **Trigger** | Scheduled |
| **Cron** | `CRON_TZ=America/Chicago 30 6 * * 1-5` |
| **Fallback if TZ prefix rejected** | `30 11 * * 1-5` (CDT) / `30 12 * * 1-5` (CST) — UTC, not DST-safe |
| **Repository** | `bernardjhuang/zonted.com` on `main` (required — cron defaults to no repo) |
| **Model** | Grok 4.5 (or current Grok high) |
| **Tools** | Pull request creation (on). Optional: Memories |
| **Permissions** | Private (or Team Owned if you want team billing) |

Cron is Mon–Fri only. There is no NYSE holiday calendar in Cursor schedules — the prompt below skips observed holidays.

## Prompt (paste into the automation)

```markdown
## Goal
Refresh the public Grok brief on zonted.com — deep, early-stage, cross-agency catalyst theses — every NYSE trading day at 6:30 AM America/Chicago.

## Skip rules (do these first)
1. If today is Saturday/Sunday in America/Chicago → stop. No changes.
2. If today is an observed NYSE full closure (common 2026 set: New Year's Day, MLK, Presidents Day, Good Friday, Memorial Day, Juneteenth, Independence Day observed, Labor Day, Thanksgiving, Christmas) → stop. No changes.
3. If you cannot reach the network / primary sources → open no PR; report the failure.

## Product boundary
- Grok brief (`/trading/grok-brief/`, `trading/grok-brief.json`) = longer-dated announcement-day asymmetry across agencies (the HIMS-April pattern).
- Do NOT dump six-week PDUFA/AdCom binaries here — that is GPT brief (`trading/gpt-brief.json`).
- Prefer niches outside FDA muscle memory when real dated catalysts exist (DEA, CFTC, SEC, DOD, WHO, USDA, NRC, FCC, Federal Register).

## Steps
1. Read `docs/plans/2026-07-25-grok-brief-scanner.md` and the current `trading/grok-brief.json`.
2. Scan primary sources for the shape: a public body committed to a material decision on a future date, and named/mappable public companies have leverage.
3. Rewrite `trading/grok-brief.json`:
   - `as_of` = now in America/Chicago ISO offset
   - `scope` = `cross-agency-grok-brief-theses`
   - `cadence` must include `06:30`
   - at most 10 theses; ≥4 agencies represented; ≤4 FDA theses; ≥1 `early` stage
   - every thesis needs: what_happened, transmission, company_exposure, asymmetry, catalyst_chain (≥3), second_order, invalidation, watch, sources with working https URLs, narrative_stage, priority, confidence (source quality only)
4. Run: `python3 scripts/update-trading-grok-brief.py`
5. Run: `python3 scripts/test-trading-ui.py` and `python3 scripts/test_trading_desk_sync.py` from `scripts/` (or repo patterns already used). Fix validation failures before shipping.
6. If anything changed:
   - branch `cursor/grok-brief-YYYYMMDD-b9bc` (lowercase)
   - commit with message like `Grok brief: trading-day catalyst scan YYYY-MM-DD`
   - `git pull origin main --rebase` then push
   - open a PR into `main`, mark ready, and merge when checks are green (or ask for merge if you lack permission)
7. If nothing material changed → do not open an empty PR. Summarize "no material catalyst updates".

## Quality bar
- Honesty: do not invent Federal Register notices, meeting dates, or company facts. Prefer primary sources already cited or newly verified URLs.
- Creative niches welcome; fabricated events are defects.
- Confidence scores source/date quality, not expected return.
- Keep the HIMS reasoning path on every thesis.

## Output
- PR title: `Grok brief: trading-day catalyst scan YYYY-MM-DD`
- PR body: 3–6 bullets of what changed (new/removed/updated theses + agencies).
- If skipped (weekend/holiday/no changes): one-line reason, no PR.
```

## After you save
1. Toggle the automation **enabled**.
2. Optionally run it once manually to verify PR + deploy path.
3. Paste the automation URL / UUID back here if you want it verified via `get-automation`.

## Openclaw alternative
If you prefer the existing box instead of Cursor Automations:

```cron
30 6 * * 1-5 /Users/psy/.openclaw/workspace/zonted.com/scripts/cron-publish-grok-brief.sh
```

That wrapper only validates/injects/pushes — the agent must rewrite `trading/grok-brief.json` first (same prompt body as above).
