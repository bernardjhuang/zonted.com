# Trading Desk operations

The Trading Desk is a generated static product. This file defines route and artifact ownership so scheduled publishers do not resurrect retired pages.

## Public routes

Only these checked-in page routes may exist under `trading/*/index.html`:

- `/trading/`
- `/trading/themes/`
- `/trading/vwap-setups/`
- `/trading/momentum/`
- `/trading/mentality/`
- `/trading/performance/`
- `/trading/gpt-risk/`
- `/trading/grok-risk/`
- `/trading/fable-risk/`

`trading/hypothesis-source.txt` is a noindex data asset used by the Desk Full thesis dialog. It is not a standalone interface route.

Legacy URLs are handled by `_redirects`. Do not recreate their directories.

## Build graph

`trading/pipeline.html` is a build-only buffer. It may contain exactly four generated regions:

- `AUTO:SCAN`
- `AUTO:VWAP`
- `AUTO:CRYPTO`
- `AUTO:RESULTS`

`.github/workflows/deploy.yml` deletes the pipeline buffer before publishing.

Producer ownership:

- `scripts/update-trading-scan.py` → `AUTO:SCAN` → `trading/vwap-setups/index.html`
- `scripts/update-trading-vwap.py` → `AUTO:VWAP` → `trading/momentum/index.html`
- `scripts/update-trading-crypto.py` → `AUTO:CRYPTO` → `trading/momentum/index.html`
- external `zonted_trading_refresh.py` → `AUTO:RESULTS`, `trading/results-ytd.json`, and `trading/performance/index.html`
- external `zonted_desk_close_quotes.py` → privacy-safe `trading/desk-close-quotes.json` Robinhood fallback for OTC/no-feed Desk symbols
- `scripts/build-hypothesis-summary.py` → `trading/hypothesis-source.txt` and hypothesis chart metadata
- `scripts/build-desk-positions.py` → `trading/desk-positions.json` from a private temporary holdings payload
- `scripts/build-trading-desk.py` → `trading/index.html` and the shared Trading nav/status/asset shell; close mode automatically consumes `trading/desk-close-quotes.json`
- `scripts/sync_trading_desk.py` → routed copies of pipeline regions
- `scripts/build-themes-static.py` → crawler-visible Themes snapshot from canonical `trading/themes.json`

The route bridge must remain idempotent under `python3 scripts/sync_trading_desk.py --check`.

## Scheduled publishers

Schedules live in Hermes, not this repository. Inspect them with the scheduler before changing behavior.

Expected chain:

- 08:45 CT weekdays: morning Desk overlay
- 15:05 CT weekdays: EOD radar/artifact producer
- 15:30 CT weekdays: consolidated EOD publisher/deployer
- 16:10 CT weekdays: Robinhood `thesis` watchlist synchronization

The retired hourly scan quote publisher and watchdog have no owner and must remain absent.

## Independent risk-rating updates

Risk journals are intentionally not scheduled. Run them only after an explicit user request and keep each model blind to the others.

```bash
python3 scripts/independent_risk_journal.py prepare \
  --as-of YYYY-MM-DD --session post-close --run-dir /private/tmp/zonted-risk-YYYY-MM-DD
python3 scripts/independent_risk_journal.py run-fable \
  --run-dir /private/tmp/zonted-risk-YYYY-MM-DD
```

The Fable command is the only supported Anthropic path for this workflow. It invokes `claude -p --model claude-fable-5`, requires `claude auth status` to report `claude.ai` OAuth, removes Anthropic API-key and Bedrock/Vertex/Foundry routing variables, and stages validated JSON without publishing it. Do not replace it with the Anthropic SDK or Hermes' native Anthropic provider.

Generate GPT and Grok responses independently in their own runtimes, then run `validate` and `bundle`. Publication remains a separate reviewed step through `publish-independent-risk-journal.py`.

## Required checks

Before publishing:

1. Run all `scripts/test*.py` Trading suites.
2. Run builder `--check` modes for the active morning or close cadence. For close builds, require the fallback quote date to equal `trading/hypothesis-charts.json` `as_of` and verify OTC rows name `robinhood` as their feed source.
3. Run `python3 scripts/sync_trading_desk.py --check`.
4. Run `python3 scripts/build-themes-static.py` after every `trading/themes.json` edit.
5. Run the external publisher tests and a no-write candidate render.
6. Assert the exact public route set and pipeline marker set.
7. Run privacy scans and `git diff --check`.
8. Run `scripts/smoke-trading-desk-v3.py` locally on desktop and 390px mobile.
9. Re-run affected checks after any rebase.
10. Verify the exact deployment SHA before requesting a fresh custom-domain URL.

Never publish credentials, account identifiers or suffixes, quantities, execution details, balances, buying power, NLV/portfolio value, dollar P&L, allocation denominators, or raw broker payloads.
