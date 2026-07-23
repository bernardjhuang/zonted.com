# Zonted Trading UI Plan — v2 (reviewed & revised)

Reviewed July 23, 2026 by Claude, against production HTML (`zonted.com/trading/`), `origin/main` at `c4d661b`, and the generator/injector sources. This revises Sol's July 23 audit ("Zonted Trading UI Audit & Simplification Plan"). The original's diagnosis and most of its findings hold up; this version corrects the ones that don't, maps every work item to the file that actually owns that surface, and separates what's already shipped from what's still to do.

---

## 1. Verdict on the original audit

**Adopt the direction.** "Every dataset is shown at once; the page is an analyst's notebook, not a decision surface" is the correct diagnosis, and the P0 list (contrast, mobile header, h1, fonts, scoped controls) is right and cheap.

Three structural gaps, fixed in this revision:

1. **It plans against a static site.** Every panel on this page is emitted by a generator/injector into an `AUTO:` marker block, the openclaw box's nightly cron rewrites the position/trade blocks, and the Positions/Log tables don't exist in the HTML at all — `js/trading-broker-light.js` builds them client-side from `#bl-raw`. A hand edit inside any AUTO block is clobbered on the next refresh. Every item below names its owning file.
2. **Part of it is already shipped, and part contradicts what Sol shipped this week.** The setups tab is already retired (#75), crypto tables already consolidated (#76), the "Day" column data already exists (live quotes + day-change sort). Meanwhile the Log-tab buys/sells split and Top-10 tables the audit wants removed were *added* in #69/#73/#74 days ago. Reversing them may be right — but it's a decision for Bernard to ratify once, not churn.
3. **A few recommendations break working contracts.** Renaming `ENTER+`/`WATCH`/`AVOID` would break injector validation allowlists, the GPT handoff docs, and the vocabulary Bernard and Allen actually speak. Display-layer gloss, never data-layer rename.

## 2. Fact-check of "Verified findings"

| Claim | Verdict | Notes |
|---|---|---|
| No `<h1>`; tabs start at `<h2>` | **Confirmed** | 0 h1, 7 h2 on prod |
| Four web fonts | **Confirmed** | Fraunces, Source Serif 4, IBM Plex Sans, IBM Plex Mono |
| Search visible on all tabs, filters only Positions/Log | **Confirmed** | `#bl-q` lives in the global header; `matchSym` is only applied by the positions/trades/extremes renderers (`trading-broker-light.js:497–537`); the chips row is hidden outside Positions/Log but the search box is not |
| Export always downloads portfolio CSV | **Confirmed** | Single handler over positions/trades data |
| Empty short table renders | **Confirmed** | Header-only `<table>` inside AUTO:SCAN |
| 22 VWAP charts / 14 manager cards / 7 crypto charts / 10-col crypto table | **Confirmed** | Counted on prod |
| Contrast 4.12:1 on muted text | **Confirmed, understated** | `--bl-muted: #7a7d83` ≈ 4.13:1 on white cards — but ≈ **3.8:1 on the cream page background**, so it's worse than reported. Fix at the token |
| "Momentum renders 168 full-scan rows" | **Corrected** | The universe is **84 symbols** (83 watchlist + SPY). 168 counts each symbol's hidden accordion detail row too. The visible dump is 84 rows. The point stands; the number is inflated 2× |
| 9,859 px page, CLS 0.696, mobile FCP/LCP 4.2 s | **Plausible, not re-run** | Consistent with the real root cause: the page HTML is **962 KB** because every chart SVG and its tooltip JSON is inlined. The audit undersells this — page weight is the single biggest perf lever (see P2) |
| Mobile clipping at 390 px | **Accepted** | Per Sol's screenshots; the header is a non-wrapping flex row, so the mechanism checks out |
| Evidence files | **Committed** | See this directory's before/after mobile contact sheets and audit summary |

Also verified: the lazy SVG parking in `trading-broker-light.js` **is deployed** (the versioned `?v=` JS on prod matches origin). Inactive tabs already park their SVGs; the CLS culprit is font loading against the active panel, so the font fix is the real CLS lever, not more lazy-loading.

## 3. Already shipped — do not redo

- **Setups tab retired**, charts live in Momentum accordions fetching `trading/scan-charts.json` (sha256-paired with the scan; do not break that pairing) — #75.
- **Crypto tables consolidated** to one 10-column table — #76.
- **VWAP charts ranked by z** — #71 (superseded by "select one chart" below, but the ordering logic is reusable for the leader/laggard chips).
- **Live prices + day-change sort on Momentum** — gives the plan's "Day" default column for free. Side effect to fix in P2: the quote refresher commits a full-page rewrite to main several times a day (4 deploys today were quote refreshes).

## 4. Architecture constraints (read before touching anything)

- Page = static shell + `AUTO:{ROBINHOOD,TRADES,YTD,SCAN,VWAP,WHALES,CRYPTO}` blocks.
- Nightly openclaw cron rewrites the position/trade blocks. **Its markup contract must not change**; all Positions/Log restructuring happens in the enhancer (`js/trading-broker-light.js`), same trick as the original Broker Light redesign.
- Injectors: `scripts/update-trading-{scan,vwap,whales,crypto}.py` + `scripts/generate-trading-crypto.py` (crypto generation now lives in this repo). Momentum's injector validates labels against `{ENTER+, ENTER, SHORT+, SHORT, BREAKING}` — UI renames must be display maps inside the injector, never changes to the JSON artifacts, which the `~/Documents/trading` pipeline, the GPT handoff docs, and the blog all share.
- Deep links exist and are linked from posts: keep hash redirects working (`#watchlist`→`#scan` already exists; add `#log`→ portfolio if the merge happens).
- Bump the JS `?v=` on every enhancer change — the unversioned URL is long-cached on Cloudflare.

## 5. Revised information architecture

Five tabs, pending Decision 1: **Portfolio** (positions + activity feed) · **Momentum** · **VWAP** · **13F** · **Crypto**.

Tab counts: **drop the constant ones, keep the variable one.** "22", "14", "7" never change — that's noise. Momentum's count is a real daily signal (4 qualified today vs 0 yesterday). This replaces the audit's blanket "remove all counts."

Labels: shorten as proposed (`Momentum`, `VWAP`, `13F`, `Crypto`). Keep `ENTER+`/`WATCH`/`AVOID` **visible** in the UI with a plain-word gloss (tooltip or legend line: "ENTER+ = qualified"), because that vocabulary is the shared language of the pipeline, the handoff docs, and Bernard's conversations with Allen. Do not rename it away.

## 6. Implementation sequence, mapped to owners

### P0 — Truth and polish (shell-only; no generator contracts touched)

| # | Item | Owner file(s) |
|---|---|---|
| 1 | Real `<h1>Trading</h1>`; title row = title + freshness only | `trading/index.html` |
| 2 | Darken `--bl-muted` to ≥4.5:1 **on the cream background** (e.g. `#5c5f66` ≈ 5.9:1); same for inactive tabs. Base table text 13→14 px, meta 12.5→13 px | `trading/index.html` styles |
| 3 | Kill font CLS: preload the two families the page actually uses, `font-display: swap` + metric-compatible fallbacks. Don't fork trading typography from the site — fix loading, not fonts | shared head template / `scripts/build.py` |
| 4 | Scope Search + Export: hide both outside Positions/Log; rename Export → "Download positions CSV" | `trading/index.html`, `trading-broker-light.js` (extend the existing `filters.hidden` logic at ~line 66) |
| 5 | Mobile header: let the row wrap (title+freshness / tabs / search); tab strip scrollable with active tab `scrollIntoView` on activate | styles + 3 lines in `activate()` |
| 6 | Empty short table → one line: "No qualified shorts today" | `scripts/update-trading-scan.py` |
| 7 | Drop constant tab counts; keep Momentum's | `trading/index.html` + count writers in injectors |

### P1 — Answer-first defaults (per-generator; needs Decisions 1–3)

| # | Item | Owner file(s) |
|---|---|---|
| 1 | One-line takeaway at the top of every tab, generated from data the JSONs already carry (scan verdicts, VWAP leaders/laggards + last crosses, 13F net flows, crypto side flags). Current methodology paragraphs collapse into a `<details>` "How this works" | each injector |
| 2 | Momentum default = takeaway + qualified table; 84-row universe behind "Browse full universe" with a working scoped search. No virtualization — it's 84 rows | `update-trading-scan.py` + enhancer |
| 3 | Sector strip → "Leading: X, Y · Lagging: Z, W" chips + "view all sectors" | `update-trading-scan.py` |
| 4 | VWAP: summary table rows select **one** large chart; default SPY; leader/laggard quick chips (reuse #71's z-ranking). Keep emitting all figures, hidden — the parking pattern already makes hidden SVGs cheap; real payload fix is P2 | `update-trading-vwap.py` + enhancer |
| 5 | 13F: headline sentence → two consensus lists (most bought / most sold) → manager leaderboard with one-at-a-time expansion; aggregate holdings behind a toggle; stale-quarter warning at section level. Ticker-first naming **needs a CUSIP→ticker map** (SEC `company_tickers.json`) — real work, schedule with the Aug 14 Q2 refresh | `whale_13f.py` output + `update-trading-whales.py` |
| 6 | Crypto: per-coin plain-English status combining both axes ("Strong trend, weakening vs BTC"); rows select one chart; absolute price/VWAP into row detail | `generate-trading-crypto.py` + `update-trading-crypto.py` + enhancer |
| 7 | Portfolio: group by symbol (3 cards), instruments as a secondary line, thesis/invalidation once per symbol, "View setup" action, activity feed below (consolidated round trips, top-3 best/worst). All client-side from the unchanged cron markup | `trading-broker-light.js` only |

### P2 — Weight and plumbing (the biggest perf lever lives here)

| # | Item | Owner file(s) |
|---|---|---|
| 1 | Move inlined SVGs + `data-d` JSON out of the HTML into fetched per-tab JSON (extend the `scan-charts.json` pattern to VWAP and Crypto). Target initial HTML **< 200 KB** (from 962 KB). This, not lazy-rendering, is what moves mobile FCP/LCP | injectors + enhancer |
| 2 | Live quotes via a small fetched JSON instead of full-page rewrite commits — kills the repo/deploy churn (4 quote-refresh deploys today) and makes intraday refresh cheap | openclaw quote job + enhancer |
| 3 | URL state for selected symbol / manager / coin (tab hash already works) | enhancer |
| 4 | Sticky headers inside scrollable table regions only | styles |
| 5 | Commit audit artifacts (screenshots, Lighthouse JSON) to `audits/` in-repo | process |

Dropped from the original: dataset virtualization/pagination (over-engineering for 84 rows once the universe is collapsed — the plan's own "less is more" principle applies to code too).

## 7. Revised acceptance criteria

- 390 px: no page-level horizontal overflow, no clipped header controls, active tab visible after navigation.
- Every tab's first viewport contains its one-line takeaway and primary data.
- No **unbounded** table by default (replaces the hard 12-row cap — never truncate the qualified-setups list; that's the decision surface).
- Muted and inactive text ≥ 4.5:1 **against the cream page background**, not just white cards.
- Search visible only where it filters the active dataset; download button names its payload.
- Initial HTML payload < 200 KB (P2.1); mobile Lighthouse ≥ 90 is tied to that item landing, not P0/P1.
- Data-layer labels (`ENTER+`, `SHORT`, `BREAKING`…) unchanged in all JSON artifacts; UI gloss only.
- Existing deep links keep working, including legacy `#watchlist` and (post-merge) `#log`.
- Keyboard tab nav, row expansion, chart inspection, aria labels unchanged; a11y 100.
- The nightly cron and the sha256 scan/scan-charts pairing survive every change untouched.

## 8. Decisions needed from Bernard before P1

1. **Merge Log into Portfolio?** The audit says yes; Sol built the split + Top-10 tables just this week (#69/#73/#74). Ratify once.
2. **Tab counts:** agree with "variable-only" (keep Momentum's count, drop the constants)?
3. **Verdict vocabulary:** gloss (`ENTER+ — qualified`) vs full rename? v2 recommends gloss.
4. **Generator repo split** — the standing question, now actually blocking: P1 touches Sol's injectors and the `~/Documents/trading` pipeline in the same stroke. Decide shared repo vs Sol-owns-dailies before parallel edits collide.
5. **Quote refresh cadence:** OK to move intraday quotes to a fetched JSON (P2.2) so main stops accumulating rewrite commits?
