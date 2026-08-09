# RH Launch Radar — M0/M1/M2 first backtest (2026-08-09)

Canonical spec: [`rh-launch-identification-spec.md`](./rh-launch-identification-spec.md)  
Code: [`rh-launch-radar/`](../rh-launch-radar/)

## Goal (frozen)

Rank Pons factory launches on Robinhood Chain (`4663`) by probability of becoming a **high-value proxy winner**, evaluated chronologically against naive baselines. Research / paper scoring only — no signing path.

## What ran

| Step | Result |
|---|---|
| M0 harvest | **6,516** Pons launches from blocks `29,068,155–32,066,767` (~Aug 6–9 window). Active factory 6,486 / legacy 30. |
| Stamp | Anchor-interpolated timestamps (`~0.10s` block time empirically). |
| M1 features | T+**10m** swap-flow features for **300** launches with ≥24h history (cohort closes ~Aug 8 16:06 UTC). |
| M1 labels | Proxy label `high_value_proxy` = 24h quote-volume ≥ p90 **and** unique traders ≥ p80. **24 / 300 (8%)** positive. |
| M2 backtest | Chronological 70/30 split (210 dev / 90 val). Scorecard `model_v0` vs B1–B4. |

### Frozen proxy thresholds (`m0-proxy-v1`)

From the 300-launch labeled cohort:

- 24h quote volume p90 ≈ **11.9 ETH** equivalent through pool swaps  
- 24h unique traders p80 ≈ **195**

> These are **swap-flow proxies**, not yet executable depth-aware outcomes ($250/$1k/$5k notionals). Depth/sell-path labeling is the next hardening step.

## Validation results (decision = T+10m)

| Ranker | Precision@10 | Recall@10 | Precision@3 |
|---|---:|---:|---:|
| **model_v0** | **0.80** | **1.00** | 0.67 |
| B1 first-window volume | 0.60 | 0.75 | 1.00 |
| B3 unique traders | 0.60 | 0.75 | 1.00 |
| B4 random | 0.40 | 0.50 | 0.33 |
| B2 msg.value / launch ETH | 0.00 | 0.00 | 0.00 |

**Lift vs best baseline (B1):** `0.80 / 0.60 = 1.33×`  
**Promotion bar (≥1.5× P@10):** **not met** (`passed: false`).

### Read carefully

1. Validation positives = **8** in 90 rows — thin cell; treat lift as directional, not settled.
2. On **dev**, B3 unique traders alone hits P@10 = 1.0 — breadth is the dominant naive signal; the scorecard is not yet clearly additive beyond flow features.
3. B2 (launch `msg.value`) collapses because Pons launches are heavily concentrated near ~3.5 ETH (p50), so it does not rank.
4. Entire cohort is `pons-v1` only (pre–pools.trade stratification incomplete in this window slice).
5. No rug-rate@K yet (spec requirement for promotion).

## Funnel notes (harvest window)

- Unique creators: **2,277**; creators with ≥10 launches: **107** (serial launchers are common — creator prior belongs in the scorecard).
- `msg_value_eth` is bimodal (p10≈0.014, p50≈3.5) — useful as a structure flag once vetoes land, weak as a solo ranker.
- Durable winners at tradeable depth are still rare under the proxy definition (8%). Do **not** declare a live predictive product yet.

## Next steps (in order)

1. **Executable labels** — V4Quoter / v3 quote math for $250/$1k notionals; redefine winner as executable + durable per spec §3.
2. **Veto stage** — implement V1–V8 at T+0…T+3m; re-run ranker only on survivors.
3. **Expand corpus** — rewind harvest to factory start blocks; discover pools.trade factory; stratify by `mechanism_era`.
4. **Calibrate weights on dev only** — especially creator prior + breadth; keep validation untouched until freeze.
5. Re-evaluate promotion bar across ≥2 distinct weeks.

## How to reproduce

```bash
export BLOCKSCOUT_PRO_API_KEY=…   # or ~/.config/trading/blockscout.env
cd rh-launch-radar
PYTHONPATH=src python3 -m rh_radar.harvest --chunk 50000
PYTHONPATH=src python3 -m rh_radar.stamp --every 20000
PYTHONPATH=src python3 -u -m rh_radar.features --limit 300 --offset <aged_offset> --only-offsets 600
PYTHONPATH=src python3 -u -m rh_radar.labels --limit 300 --offset <aged_offset> --only-horizons 86400
PYTHONPATH=src python3 -u -m rh_radar.backtest --decision-offset 600
```

Local artifacts (gitignored): `rh-launch-radar/data/**`.
