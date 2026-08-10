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

1. ~~Honest labels on existing 800~~ → **done (Round D below)**.
2. **Redesign exit policy** — hold-to-24h is economically dead; primary labels should be T+1h (and rule-based TP), not T+24h.
3. **Sample lineage-dedupe** on first-window traders for a 100-launch slice.
4. **Walk-forward + paper EV harness** with the short-horizon exit rule.
5. V4 InstantLaunch path + remaining vetoes (V2/V4) once EV spine exists.

---

## Round D — honest $250 labels (2026-08-09)

TVL-capped single-tick v3 math; entry T+10m; checkpoints 1h / 6h / 24h; binary winner = full $250 fill ∧ not rug ∧ gross multiple ≥ **3×** (spec band).

### Hold-to-24h (`executable_winner_250`)

| Metric | Value |
|---|---:|
| Labeled launches | 800 |
| Full $250 entry fill | 146 |
| `executable_exit` (≥0.85× at 24h) | **1** |
| `executable_winner_250` (≥3× at 24h) | **0** |
| Rug flag | 798 / 800 |
| Proxy “winners” that are rugs under honest labels | **50 / 50** |
| Veto survivors that are rugs under honest labels | **91 / 91** |

Validation money metric (all 800, chronological 70/30): model mean gross@10 ≈ **0.066** vs B1 ≈ **0.058** — both lose ~94¢ per dollar. rug-rate@10 = 1.0. **Promotion fails.** P@K is undefined/0 (no positives).

### Same inventory, exit@1h (derived from checkpoints)

| Metric | Value |
|---|---:|
| Full-fill rows with 1h recovery ≥ 0.85 | 17 |
| ≥1× at 1h | 15 |
| ≥3× at 1h (`executable_winner_250_1h`) | **3** |
| Of those 3 in veto-survivor set | **0** |

So: (1) the circular proxy label was counting pumps that are not holdable; (2) any edge is **short-horizon**; (3) current vetoes may be dropping the only 3×@1h names (needs confirmation on a larger 1h-positive set).

### Round D decision

- Stop iterating the scorecard against `high_value_proxy` or hold-to-24h 3× — both are the wrong target for this cohort.
- Next build: freeze an **exit@1h / staged-exit** label, rebuild vetoes with that objective, then re-run Phase 0 + walk-forward EV.

---

## Round E — V7 retimed to decision + hourly EV (2026-08-10)

### Root cause of “vetoes kill all 1h winners”

All three `executable_winner_250_1h` names were vetoed solely by **V7 at launch block**, while honest entry TVL at **T+10m** was already above (or near) the floor:

| launch_id | 1h multiple | V7 launch TVL | entry TVL @T+10m |
|---|---:|---:|---:|
| `0x017977…` | 7.22× | $960 | **$6,661** |
| `0x9b0a58…` | 4.00× | $96 | **$1,070** |
| `0xb2ab28…` | 3.89× | $115 | **$936** |

Liquidity arrives after first mint. Spec veto window is T+0…T+3m / decision-time — launch-block V7 is the wrong clock. Code default is now `--heavy-at decision` (T+10m).

### Walk-forward EV (`rh_radar.ev_backtest`, K=3/hour, exit=1h gross)

Cohort sits on a single UTC day → **hour folds** (14 hours; folds with ≥5 candidates used).

| Veto mode | Candidates | 3×@1h in set | model mean-of-fold-means | folds with mean>1 | C1 foldMeans | B1 foldMeans | EV bar |
|---|---:|---:|---:|---:|---:|---:|---|
| launch_v7 (old) | 91 | 0 | 0.25 | 1 | 0.14 | 0.14 | fail |
| **decision_v7 ($1k)** | 62 | 2 | **0.75** | **2** | 0.47 | 0.47 | fail (mean<1) |
| decision_v7 ($250) | 72 | 3 | **0.86** | **3** | 0.45 | 0.45 | fail (mean<1) |

**Takeaways**

1. Retiming V7 is mandatory — it is the difference between capturing 1h 3× names and missing them all.
2. `model_v0` is the best ranker on 1h EV once the sieve is fixed; C1/B1 lag.
3. Still **not** a product: mean fold recovery &lt; 1.0 (lose money on average even when a fold spikes). Need more history (≥2 weeks), tighter entry filter, and/or staged exits — not more proxy-label tuning.
4. Veto CLI default: `python3 -m rh_radar.vetoes --heavy-at decision`.

### Round E next

1. Re-harvest / expand aged Pons window so hour folds span multiple days.
2. Paper ledger with decision-V7 survivors, top-K/hour by `model_v0`, exit@1h (and optional TP at 1.5×/3× if mark hits earlier).
3. Lineage-dedupe sample on the 1h-winner hours only (cheap, targeted).

## How to reproduce

```bash
set -a; source ~/.config/trading/blockscout.env; set +a
cd rh-launch-radar
PYTHONPATH=src python3 -u -m rh_radar.harvest --chunk 50000
PYTHONPATH=src python3 -u scripts/stamp_missing.py
PYTHONPATH=src python3 -u -m rh_radar.features --limit 800 --offset 1726 --era-prefix pons --only-offsets 600
PYTHONPATH=src python3 -u -m rh_radar.labels --limit 800 --offset 1726 --era-prefix pons --only-horizons 86400
PYTHONPATH=src python3 -u -m rh_radar.vetoes --limit 800 --offset 1726 --era-prefix pons --floor-usd 1000 --heavy-at decision
bash scripts/run_honest_shards.sh 4 800 1726
PYTHONPATH=src python3 -u -m rh_radar.ev_backtest --veto-mode decision_v7 --fold-grain hour --k 3
PYTHONPATH=src python3 -u -m rh_radar.phase0 --label-field executable_winner_250_1h
```

Local artifacts (gitignored): `rh-launch-radar/data/**`.
