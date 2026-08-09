# Robinhood L2 Launch Radar — Research Plan

**Goal:** Build a system that ranks newly launching tokens / pools on Robinhood Chain (chain ID `4663`) by *likelihood of reaching a large market cap* relative to this chain’s opportunity set — not absolute Solana/Base “billion-dollar” mcap.

**Primary data:** Blockscout PRO API (`api.blockscout.com`, Bearer key via `BLOCKSCOUT_PRO_API_KEY`).  
**Market labels / reverse-engineering corpus:** [DexScreener Robinhood](https://dexscreener.com/robinhood) + DexScreener public API (`chainId=robinhood`).

**Non-goal for v1:** Automated trading, wallet recommendations, or claiming predictive certainty. This is a research → scoring → monitoring pipeline with explicit uncertainty.

---

## 0. Reality check (why a naive “top mcap” approach will fail)

A quick DexScreener search snapshot (2026-08-09) shows Robinhood Chain’s *current* listed runners are still early-stage:

| Observation | Implication |
|---|---|
| Top observed mcap in search results was ~$1.2M, with many “runners” in the $5k–$120k band | “Large mcap” must be **relative** (e.g. top decile of RH pairs, or thresholds like $100k / $500k / $1M / $5M) |
| Many pairs share meme names (`ROBINHOOD`, `HOOD`) and thin liquidity | Name/brand alone is useless; need **structure, distribution, and flow** features |
| DexScreener search returns a capped result set (~30), not a full chain census | Need Blockscout for **universe discovery**; DexScreener for **price/liquidity/volume labels** |
| Boosts / profiles exist for RH tokens | Social promotion is a feature *and* a confounder — treat carefully |

So the product question is closer to:

> Among tokens that just became tradeable on RH, which ones show **early on-chain + market microstructure patterns** that historically preceded the chain’s largest mcap outcomes?

not:

> Predict the next global mega-cap.

---

## 1. Problem framing

### 1.1 Success definition (freeze before modeling)

Pick measurable outcomes and keep them frozen:

1. **Primary outcome (recommended):** token reaches max circulating mcap ≥ threshold \(T\) within horizon \(H\) after first liquid pool appears.
   - Candidate thresholds: \(T \in \{100k, 500k, 1M, 5M\}\) USD.
   - Candidate horizons: \(H \in \{24h, 72h, 7d, 30d\}\).
2. **Secondary outcomes (useful for ranking quality):**
   - Peak liquidity USD
   - Sustained volume (e.g. median daily volume over days 3–7)
   - Drawdown from peak (rug / failed launch proxy)
   - Holder count growth without extreme top-holder concentration collapse

### 1.2 Unit of analysis

Use **token contract + primary pool** as the entity:

- Token address (ERC-20)
- Primary pair/pool address (usually WETH/ETH or USDG quote)
- Launch timestamp = earliest of: token creation block, first mint, or `pairCreatedAt` from DexScreener

Track **candidates** (new launches) and **labels** (what happened later).

### 1.3 Decision output

For each live candidate, emit:

- Score `0–100` (calibrated later)
- Top contributing features (explainability)
- Risk flags (honeypot / owner mint / LP unlockable / extreme concentration)
- Cohort context (“looks like historical top-decile at T+2h”)

---

## 2. Data sources and roles

```text
┌────────────────────┐     universe + structure      ┌─────────────────────┐
│ Blockscout PRO API │ ─────────────────────────────▶ │ Feature store       │
│ chain_id = 4663    │     holders, transfers,       │ (token, pool, t)    │
└────────────────────┘     contracts, hot contracts  └──────────┬──────────┘
                                                                │
┌────────────────────┐     mcap / liq / vol / age               │
│ DexScreener API    │ ─────────────────────────────────────────┤
│ chainId=robinhood  │     labels + market features             │
└────────────────────┘                                          ▼
                                                     ┌─────────────────────┐
                                                     │ Scorer + monitor    │
                                                     └─────────────────────┘
```

### 2.1 Blockscout (structural truth)

Use for discovery and hard-to-fake early signals.

| Need | Endpoint family (chain `4663`) | Notes |
|---|---|---|
| New / active contracts | `GET /4663/api/v2/stats/hot-smart-contracts`, recent txs, token list | Validate response shape before relying on “hot” |
| Token metadata + supply | `GET /4663/api/v2/tokens/{address}` | Supply, type, decimals |
| Holder structure | `GET /4663/api/v2/tokens/{address}/holders` + `/counters` | Concentration, growth rate |
| Transfer graph | `GET /4663/api/v2/tokens/{address}/transfers` | Unique receivers, burstiness |
| Deployer / contract provenance | `GET /4663/api/v2/addresses/{address}`, `.../smart-contracts/{address}` | Verified?, proxy?, creator |
| Creator history | Creator address → prior deployments / token transfers | Serial launcher / rug seriality |
| Activity intensity | Address counters, tx lists, logs | Early organic vs bot-looking bursts |
| Native fee / network context | `GET /4663/api/v2/stats`, charts | Regime features (busy day vs quiet day) |
| Contract state checks | `POST /4663/json-rpc` `eth_call` | Ownership, mint/pause/blacklist view methods when ABI known |

Auth: `Authorization: Bearer $BLOCKSCOUT_PRO_API_KEY`, plus `User-Agent` + `Accept: application/json`. Track `x-credits-remaining`.

### 2.2 DexScreener (market labels + microstructure)

Public API, no key. Chain slug is **`robinhood`**, not `4663`.

Useful endpoints:

| Endpoint | Use |
|---|---|
| `GET /latest/dex/search?q=...` filtered to `chainId=robinhood` | Seed corpus / discovery (capped) |
| `GET /latest/dex/pairs/robinhood/{pair}` | Point-in-time mcap, FDV, liquidity, volume, txn buys/sells, age |
| `GET /tokens/v1/robinhood/{addrs}` (≤30) | Enrich token → pools |
| `GET /token-pairs/v1/robinhood/{token}` | All pools for a token |
| `GET /token-boosts/latest/v1` + `/token-boosts/top/v1` | Promotion intensity (feature + bias) |
| `GET /token-profiles/latest/v1` | Soft social/marketing signal |

DexScreener is **not** a complete census. Treat it as:

1. Label provider for tokens that appear there
2. Market-feature provider once a pair is known
3. Incomplete for brand-new / unlisted pools → Blockscout must own discovery

---

## 3. Approach overview (four phases)

### Phase A — Build a historical labeled set from current / past runners

**Objective:** Reverse-engineer what “winners” looked like *before* they were winners.

1. **Collect corpus**
   - Pull DexScreener Robinhood pairs via search + boosts + profiles.
   - Dedupe by token address; keep primary pool (highest liquidity).
   - Persist raw JSON snapshots (immutable) under something like `data/robinhood-launch-radar/raw/`.

2. **Define winner / loser / unresolved**
   - Winner: peak mcap ≥ \(T\) within \(H\).
   - Loser: never reaches \(T\), or rugs (liquidity collapse / near-zero holders growth with massive dump).
   - Unresolved: too new for horizon \(H\).

3. **Reconstruct early windows with Blockscout**
   For each labeled token, fetch as-of features at fixed ages after launch:
   - T+15m, T+1h, T+6h, T+24h
   - Features listed in §4
   - Important: use Blockscout historical evidence (transfers/holders over time), not today’s holder table as if it were early-state. Where true point-in-time reconstruction is hard, mark feature as *proxy* and down-weight.

4. **Pattern mining (start simple)**
   - Compare winner vs loser distributions per feature.
   - Rank features by separation (effect size / mutual information), not vibes.
   - Produce a human-readable “winner fingerprint” memo before any ML.

**Deliverable:** `labels.parquet` / JSON + a short “what separated winners” note.

### Phase B — Live universe discovery on Robinhood L2

**Objective:** See launches *before* DexScreener ranking makes them obvious.

Candidate discovery loop (cron every 1–5 minutes):

1. Scan recent token contracts / token transfers / factory pool-creation logs via Blockscout.
2. Normalize to candidate tokens with:
   - creation block/time
   - deployer
   - first liquidity event (pool create / first add-liq)
3. Join DexScreener as soon as a pair appears (market features).
4. Enqueue for feature extraction.

**Bootstrap discovery tactics if factory addresses are unknown:**

- Watch WETH/ETH/USDG transfer spikes into new contracts
- Watch new verified contracts with ERC-20 interfaces
- Track “hot smart contracts” + recent token list deltas
- Maintain a growing set of known DEX router/factory addresses discovered from top pairs’ `dexId` / pair creation txs

**Deliverable:** `candidates` stream with first-seen timestamps.

### Phase C — Feature store + score

**Objective:** Turn raw data into a ranked shortlist.

1. Materialize features at each age bucket.
2. Start with an **interpretable scorecard** (logistic regression or hand-weighted points), not a black box.
3. Add hard vetoes / risk flags that can zero a score.
4. Persist scores over time so we can later measure calibration (“did top-decile actually win?”).

**Deliverable:** daily/ hourly ranked table + explanation rows.

### Phase D — Validation before trusting it

**Objective:** Prove the system is better than naive baselines.

Baselines to beat:

1. Rank by early 1h volume
2. Rank by early liquidity
3. Rank by DexScreener boosts
4. Random among new pairs

Metrics:

- Precision@K and recall of eventual winners at each horizon
- Lift vs baselines
- Time-to-detect (how early the winner enters top-K)
- False-positive cost proxy (how often top-K rugs)

Only after out-of-sample lift is real should we discuss UI / trading-desk integration.

---

## 4. Feature families to reverse-engineer

### 4.1 Launch structure (Blockscout-heavy)

- Token age at first liquidity
- Verified contract? proxy? unusual bytecode size
- Owner privileges still active (mint / pause / blacklist) via `eth_call` when ABI available
- LP ownership: burned / locked / held by deployer
- Initial liquidity USD and quote composition (WETH vs stable)
- Deployer funding path (fresh wallet vs known funder cluster)

### 4.2 Distribution quality (Blockscout-heavy)

- Unique holders at T+1h / T+6h / T+24h
- Top-1 / top-10 / top-50 holder share (ex LP)
- Gini / Herfindahl of holder balances
- % supply in deployer + deployer-linked wallets
- Transfer graph: organic fan-out vs cyclic wash patterns
- Median transfer size vs whale-dominated flow

### 4.3 Market microstructure (DexScreener-heavy)

- mcap / FDV / liquidity at early ages
- mcap-to-liquidity ratio (inflated mcap with tiny LP is a classic trap)
- volume / liquidity turnover
- buy/sell txn imbalance windows (m5, h1, h6)
- price impact fragility (large % moves on small volume)
- number of pools / quote assets (fragmentation)

### 4.4 Attention & contamination (DexScreener + heuristics)

- Boost count / profile present
- Symbol collisions (`ROBINHOOD` clones)
- Rapid social links appearing before holders
Treat these as **optional boosters**, never as primary quality.

### 4.5 Deployer pedigree (Blockscout)

- Prior tokens deployed by same creator
- Prior tokens’ peak mcap / rug rate
- Reused ABIs / identical bytecode clusters (factory launches)

---

## 5. Proposed scoring v0 (before ML)

Keep v0 boring and auditable.

```text
score =
  + distribution_quality
  + liquidity_quality
  + organic_flow
  + deployer_pedigree
  - concentration_penalty
  - privilege_risk_penalty
  - wash_trading_penalty
  - clone_name_penalty
```

Example gates (veto / hard flag):

- Top-1 holder (ex LP) > 40% at T+1h → flag
- Owner can mint unbounded → flag
- Liquidity < $X while mcap > $Y → flag
- Deployer has ≥N prior rugs → veto or heavy penalty

Only after scorecard shows lift, consider a small model trained on Phase A labels.

---

## 6. Concrete build sequence

### Milestone 1 — Data probe (1–2 focused scripts)

1. Snapshot DexScreener Robinhood corpus (search + boosts + profiles + pair details).
2. For top N tokens by mcap/liquidity, pull Blockscout token/holders/transfers/contract info.
3. Write a short findings note: which fields are populated, credit cost per token, missingness.

**Exit criteria:** we can join Dex pair ↔ token ↔ deployer for ≥80% of the corpus.

### Milestone 2 — Labeling + early-window features

1. Freeze \(T\) and \(H\).
2. Build historical feature snapshots at T+1h / T+6h / T+24h.
3. Produce winner vs loser feature comparison tables.

**Exit criteria:** at least a handful of clear separators (or an honest “no strong signal yet — chain too young / sample too small”).

### Milestone 3 — Live candidate watcher

1. Poll Blockscout for new tokens / new pools.
2. Enrich with DexScreener when pairs appear.
3. Emit ranked candidates every N minutes to JSON (site artifact or private log).

**Exit criteria:** new launches appear in our feed within minutes of first liquidity, with scores + flags.

### Milestone 4 — Paper evaluation loop

1. Store predictions without looking at later outcomes.
2. After horizon \(H\), score precision/recall vs baselines.
3. Recalibrate weights.

**Exit criteria:** statistically better than “rank by early volume” on a held-out period.

---

## 7. Suggested repo shape (if we implement)

Keep secrets out of git (`BLOCKSCOUT_PRO_API_KEY` in env / gitignored `.env`).

```text
scripts/
  rh_radar_snapshot_dexscreener.py
  rh_radar_enrich_blockscout.py
  rh_radar_build_labels.py
  rh_radar_score_live.py
  test_rh_radar_*.py
data/robinhood-launch-radar/          # gitignore large raw dumps if noisy
  raw/
  labels/
  features/
  scores/
docs/robinhood-l2-launch-radar-plan.md   # this file
```

Optional later: publish a privacy-safe summary panel on the trading desk (no wallets, no size advice) — only after Milestone 4.

---

## 8. Risks, bias, and honesty constraints

1. **Tiny / young market:** with few true “large” outcomes, models overfit meme of the week.
2. **Survivorship bias:** DexScreener top list over-represents survivors and promoted tokens.
3. **Look-ahead leakage:** never train on peak mcap features when predicting peak mcap.
4. **Wash trading / bots:** high early volume can be fake; prefer holder fan-out + unique buyers.
5. **Clone / sniper dynamics:** many RH names will collide; structure > ticker.
6. **API coverage gaps:** DexScreener incomplete; Blockscout credit budget can throttle deep holder pagination.
7. **Ethics / compliance:** this is research instrumentation, not investment advice. No “guaranteed runners” language in any UI.

If Milestone 2 finds weak separation, the correct answer may be: *monitor + alert on anomalies*, not *predict large mcaps*.

---

## 9. Open decisions for review

Please decide / edit before implementation:

1. **What is “large” on Robinhood L2 right now?**  
   Recommend starting with multi-threshold labels (`$100k`, `$500k`, `$1M`) rather than one number.
2. **Horizon?**  
   Recommend dual horizons: `72h` (momentum launches) and `30d` (stickier winners).
3. **Scope of universe?**  
   All new ERC-20 pools, or only DEX pairs that hit a minimum liquidity floor (e.g. ≥ $2k) to cut noise?
4. **Output surface?**  
   Private JSON/cron only for now, vs eventually a public trading-desk panel?
5. **Risk posture?**  
   Optimize for precision (fewer alerts, cleaner) or recall (catch more, noisier)?

---

## 10. Recommended next step after plan approval

Do **Milestone 1 only**: snapshot DexScreener’s current Robinhood top/boosted set, enrich each token with Blockscout holder/deployer/contract fields, and produce a short empirical memo:

- How big are “winners” today?
- What early structural traits do the top names share?
- Which Blockscout endpoints are dense enough to support a live scorer?

That memo should either greenlight Milestone 2 or tell us the chain is too early for predictive ranking and better suited to descriptive monitoring.
