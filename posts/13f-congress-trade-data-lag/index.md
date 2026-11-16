---
title: "Three Dashboards I Deleted"
author: "Bernard Huang"
date: "2026-07-25"
modified: "2026-07-25"
canonical: "https://zonted.com/posts/13f-congress-trade-data-lag/"
category: "Autonomous Trading & Markets"
description: "How stale is disclosure-delayed market data? Congressional trades ran a 122-day median age, 13Fs up to 4.5 months late — and copying buys lost to the sells."
---

# Three Dashboards I Deleted

By Bernard Huang · 2026-07-25 · 10 min read

Two days ago I wrote about buying a stock into an FDA vote that the market had already spent three months pricing in. The lesson was simple: information everyone can see, on a calendar date everyone knows, is not an edge. This week I pointed that same audit at my own trading terminal — and deleted three dashboards I built myself.

## TL;DR

I built three popular data feeds into my trading terminal — hedge fund 13F filings, congressional stock trades, and YouTube creator sentiment — then deleted all three tabs after measuring their reporting lag.

- **Congressional trades:** The median trade displayed on my dashboard was **122 days old** (25-day median filing lag plus aging in the feed; one trade arrived 437 days late).
- **13F whale flows:** Funds report quarter-end holdings up to **45 days after** the quarter closes — up to 135 days after a January entry.
- **The Alphabet markup:** GOOGL was the #1 whale buy ($8.4B across 13 of 14 funds) and #1 YouTube ticker (314 mentions). Funds accumulated near **$287** in Q1; the public found out May 15 at **$397** (+38% higher). It now sits near $320.
- **Buys vs. sells after filing day:** Over the 10 weeks after Q1 filings dropped, the 8 largest disclosed whale buys returned **−2.8%** while the 7 largest disclosed sells returned **+4.0%**.

See how the trading stack evolved in [From Vibe Trading to an Agent-First Rig](https://zonted.com/posts/ai-trading-rig/). NFA — not financial advice.

## What I built: 13F, Congress, and YouTube feeds

Over the past few weeks I wired three alternative-data feeds into my trading dashboard, each one a fun scraping and parsing project:

**13F whale flows.** Fourteen flagship managers — Buffett, Ackman, Loeb, Coatue, Einhorn, Druckenmiller, Tepper, and peers — parsed directly from SEC EDGAR filings. Last quarter the tracked group sold a net **$33.1 billion**, with only 3 of 14 offices net buyers.

**Congressional trades.** Every equity transaction disclosed under the STOCK Act: 3,798 trades across 149 members of Congress this year, scraped from House and Senate clerks and priced at disclosure-bracket midpoints.

**YouTube creator sentiment.** The 25 largest investing channels, their five most recent videos each, transcripts run through a finance sentiment model across 2,855 organic ticker mentions. The aggregate read: “cautious, not euphoric.”

All three pipelines ran cleanly. All three were fun to browse. And I never once checked any of them before placing a real trade — which was the signal to ask why.

## The lag, measured: 122 days of staleness

Every one of those feeds has structural latency baked into its reporting rules. Instead of hand-waving about delay, I measured the exact staleness sitting on my screen:

*The structural problem, drawn to scale. The dark bar is when the buying or selling actually happened. The pink bar is the legal reporting delay — the window where the position exists and you cannot see it. The dashed line is how long you sit reading stale news. Right now the median congressional trade on my dashboard is **122 days old**, and Q1 whale positions were filed in mid-May.*

**Congress:** The STOCK Act gives members up to 45 days to report. On my dashboard, the median filing gap between trade execution and public disclosure was 25 days — and once filed, trades sit in the feed and age. The median transaction displayed on my screen had happened **122 days ago**. One disclosure in the top 40 arrived **437 days** after execution.

**13F funds:** Worse by design. Institutional managers report holdings as of the last day of the quarter and have 45 days after quarter-end to file. A position opened on January 2 appears in a filing on May 15 — a *snapshot of a trade up to four and a half months old*. The fund could have exited the entire position in April without filing a word until August.

**YouTube:** No legal delay, just an incentive delay. Creators record videos about stocks that have already moved because volatility drives clicks. Attention is downstream of price: a wall of Alphabet thumbnails tells you Alphabet already had its run.

## Alphabet: the same name at the top of every list

All three feeds converged on a single ticker, turning an abstract latency problem into basic arithmetic.

Alphabet was the whales' largest net purchase in Q1 — **$8.4 billion** across 13 of the 14 offices I tracked. It was also the #1 ticker on YouTube, with 314 mentions across 21 of 25 creators. If you wanted one name where institutional money and retail attention lined up, GOOGL was it.

*Alphabet, 2026 — the single name at the top of every one of the three feeds. The whales accumulated it during Q1 (gray), when it traded near **$287**. By the time their filings became public on May 15 (purple line) it was **$397** — you would have paid a 38% markup for the privilege of copying them. It is $320 now.*

The funds accumulated Alphabet in Q1 near **$287**. Their 13Fs became public on May 15 with the stock at **$397** — a **38% markup** before a copycat trader could click buy. Today it trades near $320. Anyone who chased the Q1 whale consensus on filing day is down ~19%, while the funds that bought in Q1 are still sitting on gains.

The managers weren't wrong. Copy-traders were just four months late — and in markets, late is wrong.

## What if you’d just followed the 13F filings?

To check whether Alphabet was an outlier, I ran the portfolio test across the whole board: buy the eight largest disclosed Q1 whale purchases on May 15 (filing day), compare them against the seven largest disclosed sales, and track both baskets through July 24.

*Buying what the whales disclosed buying, and avoiding what they disclosed selling, on the day the filings went public. The stocks they were dumping beat the ones they were loading by nearly 7 points over the next ten weeks. Sample of 8 and 7 names over one window — an illustration, not a study.*

Over the next ten weeks, the stocks these funds were *dumping* beat the stocks they were *buying* by 6.8 percentage points (+4.0% vs. −2.8%, with SPY at −1.0%). Disclosed sells — Visa, Mastercard, Chevron, Domino's — rallied. Disclosed buys — Alphabet, Broadcom, Uber — fell.

Congressional disclosures ran the same way. Apple was Congress's most-sold stock this year across eight sellers; it rose **+11.7%** afterward. Microsoft was their most-bought across seven buyers; it fell **−6.6%**.

**A necessary caveat:** fifteen stocks across one ten-week window — with Alphabet (−19%) dragging the buy basket — is an illustration, not a backtest. The real indictment isn't the ten-week return spread; it's the calendar. By the time a delayed filing becomes public, the price move that justified the trade has already happened.

## What lagging market data is actually good for

Deleting the tabs doesn't mean the underlying data is useless — it means it doesn't belong on an execution terminal. Disclosure-delayed data is terrible for “what should I buy today?” and genuinely useful for three slower jobs:

**Regime and positioning context.** Fourteen flagship funds net-selling $33.1 billion in a single quarter tells you something real about institutional risk appetite — a weather report on consensus rather than a trade trigger.

**Idea generation for deep-dive research.** If five independent managers build a position in the same mid-cap industrial, that's a prompt to pull the 10-K — the start of underwriting, not a buy signal.

**Crowding and contrarian checks.** The sharpest signal in my 13F panel was crowding: Alphabet was held by 13 of 14 offices and performed worst post-filing. When every fund already owns a name, you are the exit liquidity.

None of those jobs belong on a live trading screen. They belong in a quarterly reading session.

## What I deleted, what I kept

Removing the three tabs made the trading page 24% lighter. The panels that survived all measure *now* or *next*: live positions, the momentum scanner, VWAP levels, crypto relative strength, the forward macro risk dashboard, and the regulatory catalyst calendar.

The scrapers and archives still sit in the repo. When Q2 filings drop in mid-August, I'll run the script once and read the tables like a quarterly letter. They just won't sit next to my execution buttons pretending to be live tape.

That visual framing is the real trap. Dashboards imply recency. Put four-month-old disclosures inside a live terminal UI and your brain quietly files them under “what smart money is doing today” — which is how you end up buying Alphabet at $397 because someone smarter bought it at $287.

## The data, preserved

Since the tabs are gone, here is the final snapshot of each feed, kept so this post stands on its own. The 13F numbers describe holdings as of March 31, 2026, filed in mid-May. The congressional figures are 2026 year-to-date through July 23. The YouTube pass ran July 24.

### 13F: fourteen offices, Q1 2026

Net flow is the change in disclosed U.S. equity holdings between filings, priced at quarter-end. Options and non-13F assets are excluded, so this is a partial view of any manager's book — Berkshire's insurance float and private holdings don't appear here.

| Office | Manager | 13F AUM | Net flow |
| --- | --- | --- | --- |
| Coatue Management | Philippe Laffont | $29.1B | −$10.1B |
| Berkshire Hathaway | Warren Buffett | $263.1B | −$6.1B |
| Third Point | Dan Loeb | $2.1B | −$5.1B |
| Bridgewater Associates | Ray Dalio | $22.4B | −$4.9B |
| Tiger Global | Chase Coleman | $22.8B | −$3.7B |
| Duquesne Family Office | Stanley Druckenmiller | $2.9B | −$1.2B |
| Appaloosa | David Tepper | $5.9B | −$799.5M |
| Icahn Enterprises | Carl Icahn | $8.6B | −$667.7M |
| Pershing Square | Bill Ackman | $13.7B | −$553.6M |
| Altimeter Capital | Brad Gerstner | $5.7B | −$353.3M |
| Baupost Group | Seth Klarman | $5.1B | −$28.4M |
| Scion Asset Management | Michael Burry | $68.1M | $14.9M |
| Soros Fund Management | George Soros | $5.5B | $160.8M |
| Greenlight Capital | David Einhorn | $3.2B | $271.9M |

Across the group: **−$33.1B** in net selling, with only **3 of 14** offices net buyers.

| Most bought | Net | Most sold | Net |
| --- | --- | --- | --- |
| Alphabet Inc | $8.4B | Chevron Corporation | −$7.0B |
| Delta Air Lines Inc | $2.6B | Visa Inc | −$2.7B |
| Taiwan Semiconductor Manufac | $1.3B | Mastercard Incorporated | −$2.5B |
| Equinix Inc | $1.1B | Unitedhealth Group Inc | −$1.7B |
| New York Times Co Mtn Be | $838.5M | Constellation Brands Inc | −$1.7B |
| Asml Hldg Nv | $665.4M | Dominos Pizza Inc | −$1.4B |
| Broadcom Inc | $527.8M | Microsoft Corp | −$1.3B |
| Uber Technologies Inc | $366.3M | Ishares Tr | −$1.1B |

And the crowding measure — how many of the fourteen held the same name:

| Most widely held | Offices holding |
| --- | --- |
| Alphabet Inc | 13 |
| Amazon Com Inc | 10 |
| Meta Platforms Inc | 8 |
| Ishares Inc | 8 |
| Taiwan Semiconductor Manufac | 7 |
| Nvidia Corporation | 7 |
| Microsoft Corp | 7 |
| Broadcom Inc | 7 |
| Ishares Tr | 7 |
| Uber Technologies Inc | 6 |

### Congress: 3,798 trades, 149 members

Every transaction disclosed under the STOCK Act this year: 2,501 House and 1,297 Senate trades across 770 tickers, with $74.5M bought against $63.2M sold. Amounts are midpoints of the disclosure brackets, because members report ranges, not exact figures.

| Most bought | Net | Most sold | Net |
| --- | --- | --- | --- |
| AESI | $5.0M | AAPL | −$9.7M |
| AB | $1.0M | RILA | −$7.0M |
| INTC | $976,000 | DIS | −$3.0M |
| MSFT | $767,003 | QCOM | −$992,002 |
| UBER | $500,001 | NVDA | −$744,005 |
| CDRE | $250,001 | SMA | −$500,001 |
| MDB | $242,000 | TXN | −$500,001 |
| BRO | $201,998 | PGR | −$476,000 |

The largest individual disclosures, with the reporting delay on each — the column that made me delete the tab:

| Member | Ticker | Side | Amount | Traded | Disclosed after |
| --- | --- | --- | --- | --- | --- |
| Nancy Pelosi | AAPL | Sell | $5,000,001 | Dec 24 | 30d |
| Nancy Pelosi | AAPL | Sell | $5,000,001 | Dec 30 | 24d |
| Chip Roy | AESI | Buy | $5,000,001 | Apr 30 | 9d |
| Jefferson Shreve | RILA | Sell | $5,000,001 | Feb 9 | 33d |
| Jefferson Shreve | RILA | Sell | $5,000,001 | Feb 9 | 33d |
| Nancy Pelosi | DIS | Sell | $1,000,001 - $5,000,000 | Dec 30 | 24d |
| Nancy Pelosi | AB | Buy | $1,000,001 | Jan 16 | 7d |
| Nancy Pelosi | GOOGL | Sell | $1,000,001 | Dec 30 | 24d |
| Nancy Pelosi | AMZN | Sell | $1,000,001 | Dec 24 | 30d |
| Nancy Pelosi | NVDA | Sell | $1,000,001 | Dec 24 | 30d |

### YouTube: 25 creators, 2,855 mentions

The five most recent long-form uploads from each of 25 investing channels, transcripts scored by a finance sentiment model across 1,787 ticker mentions. “Cross-creator read” is the consensus across the creators who discussed each name.

| Ticker | Mentions | Creators | Cross-creator read |
| --- | --- | --- | --- |
| GOOGL | 314 | 21 | mixed |
| GOLD | 238 | 11 | bearish |
| TSLA | 230 | 16 | mixed |
| SPX | 187 | 23 | mixed |
| AMZN | 150 | 19 | mixed |
| AAPL | 140 | 14 | mixed |
| BTC-USD | 135 | 11 | bearish |
| NVDA | 109 | 17 | mixed |
| NFLX | 106 | 9 | bearish |
| MSFT | 85 | 15 | mixed |
| AMD | 56 | 5 | mixed |
| PYPL | 49 | 6 | mixed |

## Common questions

### How late are 13F filings?

Up to 135 days. Institutional managers report positions held on the final day of the quarter and have 45 calendar days after quarter-end to file. A position opened on January 2, 2026 appears in a filing dated May 15, 2026 — and the fund can exit in between without disclosing anything until the next quarter.

### How long do members of Congress have to report stock trades?

The STOCK Act requires disclosure within 45 days. Across the 40 largest trades on my dashboard, the median filing gap was 25 days (with one outlier arriving 437 days late). Once filed, disclosures age in the feed: the median trade displayed on my terminal had executed 122 days earlier.

### Does copying 13F filings work?

Not as an execution trigger. Over the ten weeks after Q1 2026 filings dropped on May 15, the eight largest disclosed buys averaged −2.8% while the seven largest disclosed sells averaged +4.0% — a 6.8-point spread in favor of the castoffs. The structural reason matters more than the single-quarter sample: the price move that made a position attractive usually happens before the public sees the filing.

### Is congressional trading data useful at all?

For slow policy research or sentiment tracking, yes. As a same-day trade signal, no — by the time a filing is public, the median trade is months old and reported only as a broad dollar bracket without an execution price.

## Disclosure (NFA)

**Not financial advice.** I hold positions in ABT, HIMS, and HOOD, and I may buy or sell any of them without updating this post. Performance figures are from Alpaca SIP data through July 24, 2026; 13F and congressional data from SEC and House/Senate disclosure systems. This is a personal research journal — me showing my work, not recommending it.
