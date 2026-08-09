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

## Next steps (in order)

1. **Horizon executable labels** — depth/sellability at T+1h/6h/24h, not only launch-block veto enrichment.
2. **V4 InstantLaunch path** — PoolManager / poolId swap + liquidity reads; separate era stratum.
3. **V2 owner-powers + V4 deployer rug lineage** still unimplemented.
4. Calibrate scorecard weights on **dev only** (creator prior + depth/sellability); keep val frozen.
5. Re-evaluate promotion across ≥2 distinct weeks / eras.

## How to reproduce

```bash
set -a; source ~/.config/trading/blockscout.env; set +a
cd rh-launch-radar
PYTHONPATH=src python3 -u -m rh_radar.harvest --chunk 50000
PYTHONPATH=src python3 -u scripts/stamp_missing.py   # or: python3 -m rh_radar.stamp
PYTHONPATH=src python3 -u -m rh_radar.features --limit 300 --offset 1726 --era-prefix pons --only-offsets 600
PYTHONPATH=src python3 -u -m rh_radar.labels --limit 300 --offset 1726 --era-prefix pons --only-horizons 86400
PYTHONPATH=src python3 -u -m rh_radar.vetoes --limit 300 --offset 1726 --era-prefix pons --floor-usd 1000
PYTHONPATH=src python3 -u -m rh_radar.backtest --decision-offset 600 --label-field high_value_proxy
PYTHONPATH=src python3 -u -m rh_radar.backtest --decision-offset 600 --label-field executable_winner_proxy
```

Local artifacts (gitignored): `rh-launch-radar/data/**`.
