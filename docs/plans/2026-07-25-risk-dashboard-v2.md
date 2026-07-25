# Risk Dashboard v2 Implementation Plan

> **For Hermes:** Execute this plan task-by-task with tests before implementation and independent review where practical.

**Goal:** Convert the public Risk tab from an unvalidated conditions snapshot into an auditable 2013-present conditions history, conditional-outcome table, and evidence-gated momentum decision layer; publish fitted probabilities only if they beat both unconditional and VIX-persistence baselines out of sample.

**Architecture:** Zonted is the canonical versioned owner because `/Users/psy/trading` is not a Git repository. Pure point-in-time math lives in `scripts/trading_risk_core.py`; `generate-trading-risk.py` owns public-source collection and serialization; `update-trading-scan.py` consumes the generated artifact. The public JSON remains the interface for the dashboard and scanner. A future private backtest may import the core directly instead of copying it.

**Tech stack:** Python stdlib, Yahoo/Cboe/FRED public data, vanilla JS/SVG, existing static-site generator/tests/Playwright. No black-box model and no added fear indicators.

## Frozen decisions

- Horizons: 21 and 42 completed trading sessions.
- Targets: any VIX close strictly above 25 within horizon; SPY maximum close-to-close drawdown from today's close of at least 5% within horizon.
- Point-in-time rule: FRED HY OAS observation for date T becomes available to the score on the next completed trading session; it is shifted one session before joins.
- Percentiles: trailing 756 available observations, excluding the current observation; minimum 252 observations. Bands are `<60`, `60–85`, `>85` percentile.
- Staleness: compare each input's latest date to the VIX calendar; over two completed VIX sessions old means stale and receives zero score weight.
- Curve: interpolate constant-maturity 30-day and 60-day futures values by calendar days to expiry and score their percentage slope. Preserve raw M1/M2 only as readable context.
- Score: percentile-based components for VVIX, MOVE, and SKEW; constant-maturity curve; HY OAS percentile/momentum slow-confirm component. Normalize active component points back to 0–100 so missing/stale inputs do not mechanically lower apparent risk.
- Stage 2 policy: Watchful annotates fresh ENTER/ENTER+ longs. Elevated is a hard public gate only if Stage-1 bands show monotonic separation and Elevated exceeds unconditional event frequency for at least one frozen target at both horizons; otherwise it is shadow-logged and displayed without suppression.
- Stage 3 kill rule: fitted probabilities ship only when walk-forward Brier beats unconditional and VIX-percentile persistence baselines for the same target/horizon under episode-blocked evaluation. No discretionary override.

---

### Task 1: Create the point-in-time risk core

**Files:**
- Create: `scripts/trading_risk_core.py`
- Modify: `scripts/test-trading-risk.py`

**Steps:**
1. Write failing tests for trailing percentile exclusion, staleness in VIX-session units, T+1 credit shifting, constant-maturity interpolation, direction arrows, future target labels, and score normalization.
2. Run `python3 scripts/test-trading-risk.py`; verify failure.
3. Implement pure deterministic functions with no network/file I/O.
4. Re-run tests; require pass.

### Task 2: Build 2013-present history and conditional frequencies

**Files:**
- Modify: `scripts/generate-trading-risk.py`
- Modify: `scripts/test-trading-risk.py`
- Generate: `trading/risk-ytd.json`

**Steps:**
1. Add failing schema/cardinality tests for 2013-present score history, point-in-time joins, 21/42 targets, base rates, band frequencies, source dates, and deterministic output.
2. Fetch VIX/VVIX/MOVE/SKEW/VIX9D/VIX3M/SPY since 2013, official monthly VX contracts, and lagged HY OAS.
3. Emit full-history analytics plus YTD display slices, current percentiles/deltas/staleness, constant-maturity slopes, conditions-score history, and frequency tables.
4. Compute a machine-readable `gate_policy` from the frozen Stage-2 rule.
5. Run generator twice and require byte-identical output/hash.

### Task 3: Render the falsifiable dashboard

**Files:**
- Modify: `js/trading-risk.js`
- Modify: `css/trading-risk.css`
- Modify: `trading/index.html`
- Modify: `scripts/test-trading-ui.py`
- Modify: `scripts/smoke-trading-ui.py`

**Steps:**
1. Add failing DOM/browser contracts for “Conditions Score,” score history since 2013, VIX≥25 shading, level/percentile/5d/20d direction on every metric, stale zero-weight flag, VIX9D/VIX and VIX/VIX3M, frequency table/base rates, and model-withheld status.
2. Render lightweight responsive SVG/table components from the lazy JSON asset.
3. Keep the current conditions layer but remove fixed-threshold scoring language.
4. Bump CSS/JS/data hashes and validate desktop plus 390px mobile with zero console errors/overflow.

### Task 4: Add the auditable scanner decision link

**Files:**
- Modify: `scripts/update-trading-scan.py`
- Modify: `scripts/test-trading-ui.py`
- Modify: `trading/scan-universe.json`
- Modify: `trading/index.html`

**Steps:**
1. Add tests for exact risk date alignment, Watchful annotations, Elevated hard-vs-shadow policy, gated counts/takeaway, and per-symbol decision logs.
2. Load `trading/risk-ytd.json`; fail closed if risk is older than the scan date by more than two completed sessions.
3. Add public `risk_gate` metadata and per-entry audit records to the generated universe artifact without quantities, prices beyond existing public marks, or brokerage data.
4. Annotate Watchful entries. Gate Elevated entries only when `gate_policy.hard_gate_enabled` is true; otherwise keep entries and mark `shadow_gate`.
5. Regenerate against the latest scan fixtures and verify idempotency.

### Task 5: Run the persistence gauntlet

**Files:**
- Create: `scripts/evaluate-trading-risk.py`
- Create: `scripts/test-trading-risk-evaluation.py`
- Generate: `trading/risk-evaluation.json`

**Steps:**
1. Freeze target definitions and feature registry/hash in the output.
2. Build unconditional and VIX-percentile lookup baselines first.
3. Use expanding walk-forward folds grouped by contiguous stress episodes; do not count overlapping daily windows as independent evidence.
4. Fit at most five pre-registered features with logistic/monotonic machinery only if dependencies are available and effective episode count supports it.
5. Compare Brier for every target/horizon against both baselines, report calibration/top-decile/false-alarm/per-year receipts, and emit `model_status: shipped|withheld` with reasons.
6. Never expose fitted live probability unless every frozen kill criterion passes.

### Task 6: Release and production verification

**Files:**
- Modify only generated/cache-query files required by Tasks 1–5.

**Steps:**
1. Run syntax checks, risk tests, UI contracts, browser smoke, `git diff --check`, and generator idempotency.
2. Run `/Users/psy/.hermes/scripts/zonted_trading_refresh.py --dry-run --repo <worktree>` and verify Stage-1/2 preservation.
3. Rebase on current `origin/main`, rerun all gates, push, open/merge PR, and wait for exact-SHA Cloudflare success.
4. Production-smoke `#risk` and `#scan` on desktop/mobile: asset hashes, histories, frequency counts, gate metadata, zero overflow/errors, and model shipped/withheld receipt.
5. Update the weekday EOD scheduler contract so future publishing cannot erase v2.
