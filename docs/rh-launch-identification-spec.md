# Identifying High-Value Token Launches on Robinhood Chain — Implementation Spec for Cursor

> **Audience:** Cursor (Grok 4.5) implementing the launch-identification layer. This document is self-contained — everything referenced here (addresses, endpoints, mechanics) was verified live on 2026-08-08/09 and does not need re-discovery.
>
> **Mission:** Build the system that watches every token launch on Robinhood Chain and ranks them by probability of becoming a *high-value, executable* winner — evaluated as a ranker against naive baselines, calibrated on the chain's full launch history, shipped as a live scorer with a paper ledger. Research and alerting only: no wallet, no keys, no signing path anywhere in this codebase. Live-trading decisions belong to Bernard, in a separate authorized system.

---

## 1. Ground truth (do not re-derive; do not contradict)

### Chain
- Robinhood Chain: Arbitrum Orbit L2, chain ID **4663**, ETH gas, mainnet 2026-07-01. FCFS sequencer — **no public mempool** (no sandwich MEV; latency is the constraint, not gas auctions).
- Public RPC: `https://rpc.mainnet.chain.robinhood.com` (fallback only).

### Primary data source — Blockscout PRO API
- REST base: `https://api.blockscout.com/4663/api/v2/…` (indexed: tokens, holders, transfers, logs, contracts, counters).
- JSON-RPC gateway: `https://api.blockscout.com/4663/json-rpc` (`eth_call`, `eth_getLogs`).
- Auth: `Authorization: Bearer $BLOCKSCOUT_PRO_API_KEY` — key lives in `~/.config/trading/blockscout.env` (gitignored, 0600). Never print or commit it.
- **Requests MUST send a real `User-Agent`** (e.g. `rh-launch-radar/0.1 (psyduckler@gmail.com)`) or Cloudflare returns 403.
- One key spans 100+ chains — use it for **cross-chain deployer forensics** (swap the `{chain_id}` path segment).
- Known failure mode: intermittent HTTP 500 under deep pagination. All log harvesting uses bounded block ranges, adaptive chunking, retry with backoff + jitter, and atomic checkpoints. Two runs to the same cutoff must produce identical output.

### Launchpads (the corpus spine)
| Platform | Contract | Notes |
|---|---|---|
| Pons legacy factory | `0x0c37a24F5D23A486FA692d1500881d698B1F77a4` | events from block **8,600,612**; fee split 90/10 |
| Pons active factory | `0xA5aAb3F0c6EeadF30Ef1D3Eb997108E976351feB` | events from block **8,991,118**; fee split 70/30 creator/protocol |
| Pons locker | `0x736D76699C26D0d966744cAe304C000d471f7F35` | LP custody verification target |
| pools.trade (Uniswap Labs) | **discover in M0** | live since **2026-08-05**; #1 launchpad within 2 days |

- Pons v1 mechanics: token + Uniswap **v3** pool deployed in one tx, no bonding curve, single full-range locked position, **graduation at 4.2 ETH** paired WETH, 0.0005 ETH launch fee. Emits `TokenLaunched` + standard pool events. Pons runs >50% of all chain transactions.
- Pons v2 (rolling out): ETH bonding curve → permanently locked Uniswap **v4** position at the same 4.2 ETH threshold.
- pools.trade: **Crowd Launch** = 4-hour TWAP auction, graduates only at ≥$10k FDV else full refund; **Instant Launch** = bonding curve, no minimum. Both settle into **v4** pools with permanently locked liquidity, 0.25% fee.
- Derive `topic0` for `TokenLaunched` (and pools.trade events) empirically: pull a known launch transaction's receipt from the active factory via the PRO API and read the actual topics. Do not guess event signatures from training data.

### DEX infrastructure
- Uniswap v3 factory: `0x1f7d7550b1b028f7571e69a784071f0205fd2efa` (`getPool` selector `0x1698ee82`; `slot0()` `0x3850c7bd`; `liquidity()` `0x1a686502`; `token0()` `0x0dfe1681`).
- Uniswap v4: PoolManager `0x8366a39cc670b4001a1121b8f6a443a643e40951`, StateView `0xf3334192d15450cdd385c8b70e03f9a6bd9e673b`, V4Quoter `0x8dc178efb8111bb0973dd9d722ebeff267c98f94`. Pool ID = `keccak256(abi.encode(currency0, currency1, fee, tickSpacing, hooks))`; native-ETH pools use `currency0 = 0x0`. StateView: `getSlot0(bytes32)`, `getLiquidity(bytes32)`.
- WETH `0x0Bd7D308f8E1639FAb988df18A8011f41EAcAD73` (18d) · USDG `0x5fc5360D0400a0Fd4f2af552ADD042D716F1d168` (6d) · native ETH (18d).
- Working reference code (PRO-API eth_call, v3/v4 state reads, keccak pool IDs, ±0.5% depth math): `~/Documents/trading/rhchain-scanner/scanner.py`. Reuse its patterns.

### Market-shape receipts (2026-08-08)
- ~131 new v3 pools/hour observed; median displayed liquidity ≈ **$2.6k**; of 370 sampled pools, 11 ≥ $10k, **zero ≥ $50k**, max ≈ $45.3k.
- Implication: "high value" on this chain today is measured in tens of thousands, not millions. All label thresholds are frozen from measured distributions in M0 — never assumed.

### Mechanism eras (mandatory stratification)
| `mechanism_era` | Window | Curve | Venue |
|---|---|---|---|
| `pons-v1` | Jul 1 → present | none (direct pool) | v3 |
| `pons-v2` | late Jul → present | bonding curve | v4 |
| `pools-instant` | Aug 5 → present | bonding curve | v4 |
| `pools-crowd` | Aug 5 → present | TWAP auction | v4 |

**2026-08-05 is a structural regime break** (pools.trade launch). Never pool eras in training or evaluation; never let a chronological split boundary silently coincide with it; report cross-era generalization as its own result.

---

## 2. Hard rules (violating any of these invalidates the work)

1. **Corpus = launchpad factory events.** The launch universe is every `TokenLaunched`-class event from the factories above, plus a completeness sweep of v3 `PoolCreated` / v4 `Initialize` to catch direct deployments and unknown factories (analyzed, but strategy-ineligible in v0). **DexScreener is never the corpus, never a ranking input, never a dependency** — descriptive garnish at most. Building the dataset from any "top tokens" list is survivorship bias and is prohibited.
2. **Point-in-time is structural, not aspirational.** Every feature row carries `observed_block`, `source_timestamp`, and `available_at` (the earliest wall-clock time the value could have been known). A test suite proves no feature with `available_at > decision_ts` can enter a decision row — it must fail closed, and the tests ship before the first scorer run.
3. **Decision timestamps are minutes, not hours:** T+3m, T+5m, T+10m, T+20m after first executable liquidity. Later snapshots (1h/6h/24h/72h/7d) exist only for outcome labeling. A feature that cannot be computed by T+20m is not an identification feature.
4. **Thresholds come from M0 distributions** (percentiles of the actual funnel), not from round numbers or other chains' intuitions.
5. **Chronological evaluation only, within-era.** No random splits. Clone families, deployers, and hype waves leak across random splits.
6. **No social/X data in pass one.** On-chain only. (Decided; do not re-litigate. Social is a later incremental test, if and only if an on-chain edge survives holdout.)
7. **Outcomes are executable, not displayed.** A 20× mark on $300 of liquidity is not a winner. Success is measured net of fees, price impact at fixed notionals ($250 / $1k / $5k), and a verified sell path. Rugs/honeypots/unsellable exits are losses, never missing data.
8. **No signing path.** No private key, wallet, approval, or transaction construction anywhere in this repo. Output is scores, alerts, and a paper ledger.

---

## 3. Definitions

- **Launch:** first executable liquidity event for a (token, canonical pool) from an audited factory. Multiple pools for one token = one launch (primary pool = deepest at T+3m); dedup by token contract, never by symbol.
- **Decision timestamps:** T+{3,5,10,20}min after first executable liquidity. The scorer emits a score at each.
- **Outcome horizons:** 15m, 1h, 6h, 24h, 72h, 7d after each decision timestamp.
- **Candidate outcome labels** (freeze exact cuts after M0 profiling, per era):
  - `executable_winner@H`: net executable return at horizon H ≥ frozen multiple (start by profiling the 3× band — it matches the intended recoup trigger) with the full simulated position sellable within impact budget.
  - `durable_winner`: retains frozen liquidity floor + holder breadth + sell path for ≥24h.
  - `failure`: rugged / unsellable / liquidity below floor / never traded.
- **High-value launch** (the thing this system identifies): a launch that becomes an `executable_winner` at ≥$1k notional AND `durable_winner`. Precision@K against this joint label is the headline metric.

---

## 4. Stage 1 — Veto gates (T+0 to T+3m; expect to kill most launches)

All computable the minute the pool exists. Any failure → excluded from ranking (logged with reason).

| Gate | Test | Source |
|---|---|---|
| V1 quote asset | quote ∉ {WETH, native ETH, USDG} | factory event / pool key |
| V2 owner powers | owner not renounced AND (mint / pause / blacklist / tax-mutation / upgrade selectors present); unverified contract with live owner → veto by default | PRO contract endpoint + `eth_call` probes |
| V3 LP custody | v3: position NFT owner is not Pons locker / burn; v4: pool not from a locked-liquidity launchpad path. Verify on-chain custody — never trust website copy | NFT owner lookup / pool provenance |
| V4 deployer lineage | deployer or its funding cluster has a prior confirmed rug / liquidity pull (this chain or others — cross-chain via PRO key), using strictly prior data | address txs + token transfers |
| V5 clone burst | ≥3 launches sharing bytecode hash or normalized name in trailing 60 min → all members flagged | bytecode + metadata fingerprints |
| V6 sell simulation | simulated sell of a $250-equivalent at current state fails or nets < 50% of quoted value | V4Quoter / v3 quote math `eth_call` |
| V7 liquidity floor | initial executable liquidity < floor (set at M0; provisional $1k) | pool state |
| V8 concentration | top-1 holder ex-LP/burn > 40% at decision time | PRO holders endpoint |

## 5. Stage 2 — Score (auditable weight table; ML only after lift is proven)

Five families. Every feature tagged with its earliest `available_at`. Weights start uniform within family; calibrate on the development window only (logistic or greedy rank-lift — keep final weights small integers, human-readable).

**F1. Mechanism prior (T+0).** Era/format one-hots (hypothesis to test, not assume: `pools-crowd` cleared-auction > `pools-instant` > `pons-v1`). For crowd launches: bid breadth, unique bidders, TWAP path, clearance margin over the $10k FDV gate — demand revelation someone else paid for.

**F2. Creator quality (T+0).** Wallet age; funding provenance depth (CEX-fresh vs. bridged vs. known cluster); prior launch count and their survival/graduation rates (strictly prior); cross-chain history via the same key. Within first minutes: creator fee-claim/sell behavior (the 70/30 split makes creator dumping observable — strong negative).

**F3. Liquidity quality (T+3m→).** Executable depth at ±0.5%; depth growth slope T+3→T+20; mcap-to-liquidity ratio (penalize inflated-mcap/thin-LP); pool fragmentation.

**F4. Flow breadth (T+3m→).** Unique buyers/min; buyer entropy (repeated-wallet concentration); first-block sniper share (**era-conditional: meaningful for `pons-v1`/`pools-instant`, structurally suppressed for `pools-crowd`**); buy/sell wallet imbalance; median trade size vs. whale dominance; net new holders excluding dust.

**F5. Graduation momentum (pons eras, continuous).** Distance to 4.2 ETH; graduation velocity (ETH/hour); stall/retreat pattern. Post-graduation continuation is a separate later question — at identification time, velocity toward the threshold is the signal.

**Contamination (negative features, not baselines):** DexScreener boost/profile present (paid promotion — test as negative prior); metadata similarity to recent launches beyond V5's hard veto.

`score = Σ family weights − penalties`, emitted per decision timestamp with full per-feature attribution so any score is explainable line-by-line.

## 6. Evaluation harness (this is what makes it science)

**Baselines (all four, always):** B1 rank by first-hour volume · B2 rank by liquidity at decision time · B3 rank by unique buyers in first 10m · B4 random among veto-survivors. (Boosts are not a baseline — they're a tested feature.)

**Metrics, per era and pooled-with-caveats:** Precision@K and recall of eventual high-value launches (K = 3, 10 per day); lift vs. each baseline; time-to-detect (minutes from first liquidity until the eventual winner enters top-K); rug-rate@K; capacity-weighted top-K basket return at $250/$1k/$5k notionals (the money metric).

**Protocol:** chronological dev → validation split within era; validation untouched until weights freeze; failed strategies stay failed (no holdout reuse after revision). Report actual N per cell; thin cells are "insufficient," never quietly pooled.

**Promotion bar (to paper trading):** on out-of-sample data, ≥1.5× Precision@10 lift over the best naive baseline AND rug-rate@10 ≤ the baseline's, sustained across ≥2 distinct weeks. Below bar → the honest deliverable is "monitor + anomaly alerts, no predictive ranking yet."

## 7. Build sequence

**M0 — Funnel profile (replaces any DexScreener snapshot; 1–2 days).**
Harvest all factory events (both Pons factories from their start blocks; discover pools.trade contracts from its earliest v4 pools / verified-contract search / a sampled app transaction, then harvest since Aug 5). For every launch: era, terminal outcomes (current liquidity, ever-hit $5k/$10k/$25k/$50k executable, graduated y/n, alive-at-7d). Deliverable: funnel memo — launches/day by era, winner frequency at each depth band, distribution percentiles → **freeze label thresholds and V7 floor from these numbers.**
*Exit: memo exists; thresholds frozen; if durable winners ≈ 0/week at tradeable depth, STOP and report — descriptive monitoring only.*

**M1 — Historical features + labels.** Point-in-time feature snapshots at all four decision timestamps for the full corpus; outcome labels at all horizons; leakage tests shipping and failing closed.
*Exit: winner-vs-matched-control tables (matched on era, launch hour, initial liquidity — not naive winners-vs-everything) show ≥ a handful of separators, or an honest "no separation."*

**M2 — Scorecard + backtest.** Freeze v0 weights on dev window; run the harness vs. all baselines on validation.
*Exit: promotion bar met or explicitly failed.*

**M3 — Live watcher.** Poll factories every 60–90s; run vetoes at T+0, scores at T+3/5/10/20m; emit ranked JSONL + alert on top-K entries. Latency target: candidate visible ≤2 min after first liquidity.
*Exit: live feed running with attribution per score; 48h soak with no silent gaps.*

**M4 — Paper ledger.** Every alert logged with simulated entry at next-block quote, the intended exit policy (sell-to-recoup at 3× executable, ride remainder), simulated depth-aware fills, and horizon outcomes. No look-ahead: predictions stored before outcomes exist.
*Exit: ≥2 weeks of paper results scored against baselines; only then discuss anything downstream (execution is out of scope for this repo).*

## 8. Repo & data contract

```text
~/Documents/trading/rh-launch-radar/
├── pyproject.toml            # python 3.12, uv
├── config/addresses.yaml     # everything in §1, checksummed
├── src/rh_radar/             # collectors, vetoes, features, score, harness, watcher
├── tests/                    # incl. test_point_in_time.py (fail-closed), decode fixtures
└── data/                     # gitignored
    ├── raw/                  # immutable payloads + checkpoints
    ├── launches.jsonl        # launch_id, token, pool(s), era, factory, creator, first_liq_block/ts
    ├── features/             # per decision_ts, with available_at on every field
    ├── labels/               # per horizon, with threshold-version tag
    ├── scores/               # score + per-feature attribution
    └── paper_ledger.jsonl    # append-only predictions & simulated fills
```

Stable IDs: `launch_id = keccak(token, primary_pool)[:16]`; carry `token_id`, `pool_id`, `clone_family_id`, `mechanism_era` on every row so this dataset can join the parallel research repo (`rhchain-launch-research`, Hermes) without translation. Raw dumps are large — keep them out of git and out of iCloud-synced paths if they grow (this Mac's `~/Documents` is iCloud-managed).

## 9. Honesty constraints (carry these into every report)

Tiny young market — overfitting to the meme-of-the-week is the default failure; era break on Aug 5 — pre-break signals may be dead on arrival; wash trading — prefer holder fan-out and unique-buyer metrics over raw volume everywhere; symbol collisions are constant — join on contract addresses only; Blockscout credit budget — batch, checkpoint, and log spend per module; and the correct possible conclusion of the entire project is **"no predictive edge at current market depth — monitor and alert only."** Write that if the data says it.
