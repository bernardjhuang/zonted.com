# RH Launch Radar — M0/M1/M2 backtest (2026-08-09)

Canonical spec: [`rh-launch-identification-spec.md`](./rh-launch-identification-spec.md)  
Code: [`rh-launch-radar/`](../rh-launch-radar/)

## Goal (frozen)

Rank factory launches on Robinhood Chain (`4663`) by probability of becoming a high-value / executable winner, evaluated chronologically against naive baselines. Research / paper scoring only — no signing path.

## Corpus

| Source | Count | Notes |
|---|---:|---|
| Pons (legacy + active) | 6,516 | v3 pools; stamped; primary backtest path |
| pools.trade InstantLaunch | 18,043 | v4 `poolId` (bytes32); stamped; **depth/swap path not yet wired** |
| **Total stamped** | **24,559** | InstantLaunch features blocked until v4 math |

Factories / events discovered empirically (see `rh-launch-radar/config/addresses.yaml`).

---

## Round A — pre-veto proxy (Pons, n=300)

| Step | Result |
|---|---|
| M1 features | T+**10m** swap-flow for **300** aged Pons launches |
| M1 labels | `high_value_proxy` = 24h quote-volume ≥ p90 **and** unique traders ≥ p80 → **24 / 300 (8%)** |
| M2 backtest | Chronological 70/30 (210 / 90). No veto filter. |

### Validation (decision = T+10m)

| Ranker | Precision@10 | Recall@10 | Precision@3 |
|---|---:|---:|---:|
| **model_v0** | **0.80** | **1.00** | 0.67 |
| B1 first-window volume | 0.60 | 0.75 | 1.00 |
| B3 unique traders | 0.60 | 0.75 | 1.00 |
| B4 random | 0.40 | 0.50 | 0.33 |
| B2 msg.value / launch ETH | 0.00 | 0.00 | 0.00 |

**Lift vs best baseline:** `1.33×` — **promotion bar (≥1.5×) not met**.

---

## Round B — veto survivors (Pons, n=300 → 38)

### Veto survival

| Gate | Hits (of 300) | Notes |
|---|---:|---|
| V5 clone-burst (≥3 launches / 1h by creator) | 182 | Dominant structural filter |
| V7 quote-side TVL floor (< $1k at **launch block**) | 80 | Uses WETH/USDG pool balance, not ±0.5% depth |
| V6 sell-recovery (< 0.5 on $250 notional) | 2 | Tick-local model; rarely fires after V7 |
| V1 / V3 / V8 | 0 | Quotes OK; Pons LP locked by construction; V8 holders never crossed 40% in this slice |
| **Survivors** | **38 (12.7%)** | |

Critical implementation note: V7 **must** read TVL at `first_liq_block`. Reading `latest` or using ±0.5% depth vetoes everything (drained pools / ~$6 depth).

### Enrichment signal (before ranking)

Among survivors, **21 / 38 (55%)** are `high_value_proxy` vs **8%** in the unfiltered cohort. Vetoes alone are a strong precision filter; they do not yet beat the promotion bar as a *ranker*.

### Survivor backtest (n=38, 70/30 → 26 / 12; val positives = 7)

| Ranker | Precision@10 | rug-rate@10 |
|---|---:|---:|
| model_v0 | 0.70 | 0.0 |
| B1 volume / B3 traders | 0.70 | 0.0 |
| B2 msg.value | 0.50 | 0.0 |
| B4 random | 0.50 | 0.0 |

**Lift vs best baseline:** `1.0×` — **promotion failed**.  
`executable_winner_proxy` (flow winner ∧ V6≥0.5 ∧ V7≥$1k) equals the flow proxy on survivors by construction → identical metrics. Rug-rate@10 is 0 for all rankers because survivors already cleared V6/V7; horizon-based rug labels are still TODO.

Cell is thin (12 val rows). Treat as directional only.

---

## Round C — expanded Pons cohort (n=800 → 91 survivors)

| Step | Result |
|---|---|
| Features / labels | 800 aged Pons; `high_value_proxy` = **50 / 800 (6.25%)** (thresholds re-frozen on n=800) |
| Vetoes | **91 survivors (11.4%)** — V5=499, V7=210, V6=10 |
| Enrichment | Survivors **44 / 91 (48%)** positive vs 6.25% unfiltered; **44 / 50** positives survive gates |
| Backtest | 70/30 on survivors → 63 / 28; val positives = 15 |

### Survivor validation (decision = T+10m)

| Ranker | Precision@10 | Precision@3 | Recall@10 | rug-rate@10 |
|---|---:|---:|---:|---:|
| **model_v0** | **1.00** | **1.00** | 0.67 | 0.0 |
| B1 first-window volume | 0.90 | 1.00 | 0.60 | 0.0 |
| B3 unique traders | 0.90 | 1.00 | 0.60 | 0.0 |
| B2 msg.value | 0.30 | 0.00 | 0.20 | 0.0 |
| B4 random | 0.70 | 1.00 | 0.47 | 0.0 |

**Lift vs best baseline (B1):** `1.00 / 0.90 = 1.11×` — **promotion failed** (bar ≥1.5×).  
Executable joint label identical to flow proxy on survivors (same lift).

### Round C read

1. On the larger survivor set the scorecard **beats** B1 (P@10 1.0 vs 0.9) but not by the promotion margin — baselines are already very strong after vetoes.
2. Veto stage remains the main precision lever (6% → 48% positive rate among survivors).
3. rug-rate@10 stays 0 by construction on launch-block V6/V7 survivors; need horizon rugs to make that metric informative.
4. InstantLaunch (18k stamped) still excluded via `--era-prefix pons` until v4 pool math lands.

---

## Phase 0 — response to Fable review (2026-08-09)

Review reframes the product question as **economic**: buy top-K at T+10m with fixed notional, exit by rule — is EV positive after impact, gas, and rugs? **Adopted** as the north star. Precision@K stays a diagnostic, not the promotion objective. No weight-tuning against the circular proxy from here.

### Take / leave

| Review point | Decision |
|---|---|
| EV-after-costs is the real objective | **Take** — promotion later requires positive EV across ≥2 weeks, not 1.5× P@K alone |
| Funnel > ranker | **Take** — Round C already shows vetoes do the heavy lifting |
| Creator-prior test before more ML | **Take** — ran immediately (below) |
| Stop model iteration on `m0-proxy-v1` | **Take** |
| Honest labels: continuous $250 round-trip + measured rug flag | **Take as next build** — replaces proxy for any promotion call |
| Lineage-deduped breadth | **Take, deferred** — sample 1–2 hop funding map after honest labels sketch; call budget is the risk |
| Walk-forward folds + paper portfolio harness | **Take as Phase 2** — after honest labels exist |
| Pivot architecture to “reputation DB” now | **Conditional** — proxy evidence says yes; freeze pivot until honest labels agree |
| Discard factory-corpus / InstantLaunch work | **Leave** — keep harvest; InstantLaunch still needs v4 math |
| Trust current promotion fail/pass on 8–15 val positives | **Leave** — diagnostic only |

### Phase 0 result (`python3 -m rh_radar.phase0`)

On the **800-launch** labeled Pons cohort (still `high_value_proxy` — circular with flow):

- **All 50 / 50 positives are first-time creators** (`creator_prior_launches == 0`). Prior ≥ 1 → **0** proxy winners.
- Unfiltered validation: `C1_first_time_then_volume` **matches** `model_v0` at P@10 = 1.0 (gate: `creator_prior_matches_model=true`).
- Veto survivors (91): 86 / 91 already first-time (V5 killed serials). Model P@10 = 1.0 vs C1/B1/B3 = 0.9 — a thin 0.1 edge among survivors, not a product claim.

**Working hypothesis:** under current labels this is closer to a **creator reputation + veto sieve** than an ML flow ranker. Ranker work is a tiebreaker among first-time / veto-survivor launches — and only after honest labels.

### Revised next steps (in order)

1. **Honest labels on existing 800** — continuous $250 entry@T+10m → exit@24h (tape/TWAP or historical quote math); measured rug flag (sell-path fail / −90% / LP gone). No model retune until this lands.
2. **Re-run Phase 0 gate on honest labels** — if C1 still ≈ model, freeze reputation-first architecture; else keep flow features.
3. **Sample lineage-dedupe** on first-window traders for a 100-launch slice (Blockscout PRO funder hops); compare raw vs deduped breadth ranks.
4. **Walk-forward + paper EV harness** (top-K/day, $250, rule exits) — promotion metrics become EV / rug-rate / decay, not P@K lift alone.
5. V4 InstantLaunch path + remaining vetoes (V2/V4) once the above evaluation spine exists.

## How to reproduce

```bash
set -a; source ~/.config/trading/blockscout.env; set +a
cd rh-launch-radar
PYTHONPATH=src python3 -u -m rh_radar.harvest --chunk 50000
PYTHONPATH=src python3 -u scripts/stamp_missing.py   # or: python3 -m rh_radar.stamp
PYTHONPATH=src python3 -u -m rh_radar.features --limit 800 --offset 1726 --era-prefix pons --only-offsets 600
PYTHONPATH=src python3 -u -m rh_radar.labels --limit 800 --offset 1726 --era-prefix pons --only-horizons 86400
PYTHONPATH=src python3 -u -m rh_radar.vetoes --limit 800 --offset 1726 --era-prefix pons --floor-usd 1000
PYTHONPATH=src python3 -u -m rh_radar.phase0
PYTHONPATH=src python3 -u -m rh_radar.backtest --decision-offset 600 --label-field high_value_proxy
```

Local artifacts (gitignored): `rh-launch-radar/data/**`.
