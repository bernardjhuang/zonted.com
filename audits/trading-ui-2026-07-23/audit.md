# Zonted Trading UI Audit & Simplification Plan

**Audited:** July 23, 2026
**Surface:** <https://zonted.com/trading/>
**Tabs:** Positions, Log, Momentum scan, YTD VWAP, 13F flows, Crypto spread
**Principle:** simple is best; less is more.

## Executive take

The visual foundation is clean. The problem is not styling—it is that every dataset is shown at once.

The page works like an analyst's raw notebook, not a decision surface. Desktop is readable but dense; mobile is materially broken by clipped controls, off-screen active tabs, and wide tables. The biggest win is subtraction: one summary, one primary dataset, one selected chart, details on demand.

### Keep

- Quiet visual design and restrained color.
- Freshness labels and disclosure language.
- Deep-linked tabs and keyboard arrow navigation.
- Row expansion with only one setup comparison open at a time.
- Accessible chart descriptions and keyboard chart inspection.
- Clear green/red semantics, provided contrast is fixed.

### Kill or hide by default

- The separate **Log** tab.
- Counts in tab labels.
- Search and Export controls on tabs where they do nothing.
- Empty tables.
- The 168-row scan on initial load.
- All-chart grids: 22 VWAP charts, 14 manager cards, and 7 crypto charts at once.
- Repeated explanatory paragraphs and repeated setup/invalidation copy.

## Verified findings

- No JavaScript console errors across all six tabs.
- The global **Search symbol** field only filters Positions/Log. On Crypto, entering `ZEC` left all 7 crypto rows visible while internal state reported `0 rows match`.
- **Export** always downloads positions/trades, even when Momentum, VWAP, 13F, or Crypto is active.
- Mobile screenshots at 390×844 show header metadata clipping, Search clipping, Export disappearing, wide tables overflowing, and the active 13F/Crypto tab staying off-screen.
- Momentum renders 168 full-scan rows and produces a 9,859 px desktop page.
- YTD VWAP renders 22 charts; 13F renders 14 office cards plus 3 tables; Crypto renders 7 charts plus a 10-column table.
- Lighthouse, desktop Momentum: Performance **70**, Accessibility **97**, CLS **0.696**. The major layout shift came from four web fonts loading against the 9,471 px content block.
- Lighthouse, mobile Positions: Performance **75**, Accessibility **96**, FCP/LCP **4.2 s**.
- Lighthouse confirmed insufficient contrast on muted header metadata and inactive tabs: **4.12:1**, below the required 4.5:1.

## Recommended information architecture

Reduce six top-level tabs to five:

1. **Portfolio** — open positions + recent activity
2. **Momentum** — qualified setups first; universe on demand
3. **VWAP** — market/sector/country trend explorer
4. **13F** — quarterly manager flow summary
5. **Crypto** — relative-strength explorer

Changes:

- Merge **Log** into **Portfolio**.
- Remove numeric counts from tab labels; they add noise without explaining what the number means.
- Shorten labels: `Momentum scan` → `Momentum`, `YTD VWAP` → `VWAP`, `13F flows` → `13F`, `Crypto spread` → `Crypto`.
- On mobile, keep the active tab automatically scrolled into view.

## Global shell audit

### Current problems

1. **Misleading controls:** Search and Export remain visible on all tabs but only operate on portfolio data.
2. **Broken mobile header:** metadata, Search, and Export overflow the viewport; late tabs remain off-screen even when active.
3. **Weak hierarchy:** `Trading` is a styled span, not an `<h1>`; each tab then starts at `<h2>`.
4. **Small, faint text:** the base is 13 px and muted text fails contrast.
5. **Too many fonts:** four families add load cost and caused severe desktop layout shift.
6. **The page explains before it answers:** most analytical tabs begin with long methodology paragraphs instead of today's takeaway.

### Plan

- Use a real `<h1>Trading</h1>`.
- Keep the title row to: title, last updated, and active-tab action only.
- Show Search only on Portfolio and Momentum, where it must actually filter visible content.
- Rename Export to **Download portfolio CSV** and place it inside Portfolio's overflow menu or footer.
- On mobile: title and freshness on line 1, tabs on line 2, optional full-width Search on line 3.
- Increase body text to 14–15 px; key summaries to 16 px; darken muted text to pass 4.5:1.
- Use the system sans stack plus IBM Plex Mono, or self-host/preload only the two fonts actually needed.
- Replace long introductions with one-sentence takeaways and a **How this works** disclosure.

## Tab-by-tab audit and plan

### 1. Positions → Portfolio

**Job:** answer “what do I own, how is it doing, and what invalidates the thesis?”

#### Problems

- Six rows represent only three symbols because equities and options are split.
- Eight columns force horizontal scrolling and make the two important columns—setup and invalidation—the hardest to scan.
- Setup/invalidation copy repeats for both equity and option rows.
- Equity rows show empty strike, expiry, and since-entry cells.
- Mobile exposes only the left side of the table; the thesis and risk are effectively unreachable.
- The tiny chevron is the only visible chart affordance.

#### Plan

- Group by symbol: one row/card each for **ABT, HOOD, V**.
- Default fields: **Symbol · since-entry P&L · thesis · next risk**.
- Put instruments (`shares`, `Jan 2027 $120 call`) in one secondary line.
- Put strike, expiry, side, and chart in an expanded detail panel.
- Rewrite thesis and invalidation to one sentence each; never repeat them per instrument.
- Replace vague chevrons with a clear **View setup** action.
- Add recent activity directly below positions as a compact chronological list.

**Target default:** 3 position rows + 5 recent events; no horizontal page overflow.

### 2. Log → merge into Portfolio

**Job:** answer “what changed recently?”

#### Problems

- Separate buy and sell columns make round trips hard to reconstruct.
- The same symbol/date appears on both sides, forcing mental reconciliation.
- Four simultaneous blocks—buys, sells, wins, losses—compete for attention.
- Repeated META/IBIT rankings are ambiguous because contract details are absent.
- Fill count is implementation detail, not the primary reading task.
- “By %” controls add interaction without improving the core flow.

#### Plan

- Replace buy/sell columns with one reverse-chronological activity feed.
- Consolidate same-day fills and show one event: `Jul 22 · TSLA · closed · −2.7%`.
- Keep action, instrument, status, and P&L; move fills and contract details into expansion.
- Replace two Top 10 tables with one compact **Best / worst YTD** summary: top 3 each, then **View all**.
- If repeated contracts remain separate, show strike/expiry; otherwise consolidate them by trade thesis.

**Result:** one scan direction, one chronology, no duplicate mental bookkeeping.

### 3. Momentum

**Job:** answer “what qualifies now, and why?”

#### Problems

- The actionable four setups are followed by an empty short table and a 168-row dump.
- The page is 9,859 px tall before a chart is opened.
- Eleven sector cards consume space to communicate two real takeaways: hottest and coldest sectors.
- `Spread Z`, `Dist Z`, `vs Earn VWAP`, and `ENTER+` assume expert context.
- The global Search field looks relevant here but does not filter the scan.
- The full table violates the “large lists should be virtualized” guideline and dominates mobile.

#### Plan

- Start with a one-line summary: **4 qualified longs, all Energy; no shorts.**
- Replace 11 sector cards with two chips: **Leading: Energy, Financials** and **Lagging: Consumer Discretionary, Communication Services**. Add **View all sectors**.
- Hide the empty short table entirely; show `No qualified shorts today` as one line.
- Default table columns: **Ticker · Day · relative strength · earnings · status**.
- Move raw Z-scores and VWAP distances into expanded detail.
- Rename status labels for clarity: `ENTER+` → `Qualified`, `WATCH` → `Watch`, `AVOID` → `Not qualified`.
- Put the 168-symbol universe behind **Browse full universe** with working search, filters, sticky headers, and virtualization/pagination.
- Preserve the expanded stock/sector comparison; on mobile stack charts and show one chart at a time.

**Target default:** summary + 4 setup rows + at most one opened chart.

### 4. YTD VWAP → VWAP

**Job:** answer “which markets are above or below their yearly cost basis, and what just changed?”

#### Problems

- A long paragraph precedes the useful table.
- The default table exposes seven columns, including lag-to-SPY and cross counts that are secondary diagnostics.
- Twenty-two charts render at once; most are too small to interpret, especially on mobile.
- The US and country datasets create a 3,896 px page.
- Three-column chart grids prioritize quantity over readability.

#### Plan

- Lead with: **10 of 12 US markets are above YTD VWAP; Technology leads, Communication Services lags.**
- Use a small `US / Countries` segmented control.
- Default columns: **Symbol · market · vs VWAP · trend since**.
- Move last-cross date, lag vs SPY, cross count, and 50D Z into row detail.
- Make table rows select one large chart below/alongside the table.
- Default selection: SPY. Add quick chips for top 3 leaders and bottom 3 laggards.
- Do not render 22 charts simultaneously.
- Collapse the explainer into a one-line legend plus **Method** disclosure.

**Target default:** one summary table + one selected chart.

### 5. 13F flows → 13F

**Job:** answer “what did tracked managers buy and sell last quarter?”

#### Problems

- Five summary cards repeat arithmetic instead of telling the story.
- Fourteen manager cards are shown in full, then a 25-row holdings table, then two more leaderboards.
- The strongest content—consensus buys/sells—is near the bottom.
- SEC issuer names are truncated and harder to recognize than tickers/common names.
- One stale filing is marked inside a card, where it is easy to miss.
- AUM and flow appear together without enough hierarchy; readers can confuse stock level with quarterly change.

#### Plan

- Replace five cards with one headline: **Tracked managers sold $33.1B net; 3 of 14 were net buyers.**
- Put **Most bought** and **Most sold** consensus lists first.
- Replace 14 full cards with a compact manager leaderboard: **Manager · net flow · AUM · top change**.
- Expand one manager at a time for sold/bought totals and top three changes.
- Move aggregate holdings behind **View shared holdings**; it is reference data, not the primary story.
- Use ticker/common company name first; keep SEC issuer name in details.
- Surface stale-quarter warnings at the section level and exclude stale managers from the headline unless explicitly toggled in.

**Target default:** one headline, two top-5 consensus lists, one compact manager table.

### 6. Crypto spread → Crypto

**Job:** answer “which coins lead or lag BTC, and are they above their own yearly cost basis?”

#### Problems

- Two dense methodology paragraphs delay the takeaway.
- A 10-column table is unusable on mobile.
- Seven charts repeat the same structure and make each chart small.
- Labels can appear contradictory without explanation: HYPE is +30.9% above VWAP but lagging BTC.
- Absolute price and absolute VWAP are less useful than the relative readings in this view.

#### Plan

- Lead with: **ZEC leads BTC; ETH and SOL are improving but remain below YTD VWAP; DOGE and BNB lag.**
- Default columns: **Coin · vs BTC · vs VWAP · trend · status**.
- Move absolute price, YTD VWAP, coin Z, and streak durations into details.
- Give each row a plain-English status combining both axes, e.g. `Strong trend, weakening vs BTC`.
- Make rows select one large chart; do not render all seven at once.
- Keep the methodology in a collapsed **Method & data source** section.

**Target default:** seven compact rows + one selected chart.

## Implementation sequence

### P0 — Fix misleading/broken UI

1. Hide or correctly scope Search and Export.
2. Fix the mobile header and viewport overflow.
3. Auto-scroll the active tab into view.
4. Increase type size and fix muted/inactive-tab contrast.
5. Add a real `<h1>`.
6. Reduce font loading to eliminate CLS.

### P1 — Subtract default content

1. Merge Log into Portfolio.
2. Collapse Momentum's 168-row universe and remove the empty short table.
3. Convert VWAP and Crypto to one selected chart.
4. Convert 13F cards into a leaderboard with one expanded manager.
5. Replace long intros with one-line takeaways + method disclosures.

### P2 — Make details fast, not absent

1. Add working, scoped search to Momentum's universe.
2. Add compact mobile row/card layouts with prioritized fields.
3. Preserve URL state for active tab, selected symbol/coin/manager, and open chart.
4. Add sticky table headers only inside scrollable data regions.
5. Lazy-render details and virtualize/paginate datasets over 50 rows.

## Acceptance criteria

- At 390 px width, no page-level horizontal overflow; no clipped header controls.
- The active tab is visible after direct navigation and tab changes.
- Every tab's first 844 px contains a one-line takeaway and its primary data/action.
- Default visible content: no empty tables, no dataset over 12 rows, no more than one detailed chart.
- Search is visible only where it changes the active dataset.
- Download labels identify exactly what will be exported.
- Base reading text is at least 14 px; muted and inactive text pass 4.5:1 contrast.
- Keyboard tab navigation, row expansion, chart navigation, and deep links continue to work.
- Mobile Lighthouse: Performance ≥90, Accessibility 100, FCP/LCP <2.5 s, CLS <0.1.
- Desktop Momentum CLS <0.1.

## Evidence

- Mobile contact sheet: [`mobile-before.png`](mobile-before.png)
- Final mobile contact sheet: [`mobile-after.png`](mobile-after.png)
- Lighthouse evidence is summarized in [`README.md`](README.md)

## Bottom line

Do not add more controls, cards, legends, or visual chrome. Make each tab answer one question, show one primary view, and hide everything else until requested.
