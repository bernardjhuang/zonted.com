# Horizon scanner — trading-day catalyst research

## Why this exists

GPT brief owns the next **six weeks of binary events** (PDUFA/AdCom-style resolution risk).

Horizon owns the **HIMS-April pattern**: a regulator just committed to deciding something material, on a date weeks or months out, while the equity narrative is still incomplete. The edge is announcement-day asymmetry, not resolution-day chase.

## Cadence

- **When:** 06:30 America/Chicago on NYSE trading days
- **Cron wrapper:** `scripts/cron-publish-horizon.sh`
- **Renderer:** `scripts/update-trading-horizon.py`
- **Payload:** `trading/horizon.json`
- **Surfaces:** classic `#horizon` tab + routed `/trading/horizon/`

## Agent job (openclaw)

1. Scan primary sources across FDA, DEA, CFTC, SEC, DOD, WHO, USDA, NRC, FCC, and the Federal Register.
2. Keep only events with the shape: *dated or dateable public decision + mappable public-company leverage*.
3. Prefer niches outside PDUFA muscle memory (compounding policy, event contracts, critical minerals, procurement plumbing, listing standards).
4. Rewrite `trading/horizon.json` with at most ten theses.
5. Run `python3 scripts/update-trading-horizon.py` (or let the cron wrapper do it).
6. Push via the cron script when the working tree changes.

## Required thesis fields

Mirror the HIMS reasoning path:

| Field | Role |
|---|---|
| `what_happened` | Primary-source fact pattern |
| `transmission` | How the announcement becomes equity leverage |
| `company_exposure` | Why these tickers, specifically |
| `asymmetry` | Why now vs. later / crowded finish line |
| `catalyst_chain` | Ordered multi-stage sequence (≥3 steps) |
| `second_order` | Adjacent effects worth monitoring |
| `invalidation` | What kills the thesis |
| `watch` | Concrete next signals |
| `sources` | Working http(s) primary links |

Also required: `narrative_stage` ∈ {early, building, crowded}, `priority` ∈ {P0, P1, P2}, `confidence` ∈ [0,1] for **source quality**, not expected return.

## Validation gates

Enforced by `update-trading-horizon.py`:

- `scope` must be `cross-agency-horizon-theses`
- cadence must mention `06:30`
- ≥5 agencies scanned, ≥4 agencies represented in theses
- ≤10 theses, ≤4 FDA theses
- ≥1 early-stage thesis
- every thesis has sources with valid URLs and a ≥3-step catalyst chain

## Product boundary

| Surface | Job |
|---|---|
| `/trading/brief/` | Daily desk brief / positions / macro |
| `/trading/gpt-brief/` | Six-week sector-diverse binaries |
| `/trading/horizon/` | Longer-dated cross-agency deep theses |

Do not dump near-term CAPR/REPL-style binaries into Horizon unless unused multi-stage runway remains.
