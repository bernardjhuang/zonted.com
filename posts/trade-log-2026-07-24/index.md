---
title: "Trade Log 7/24: The HIMS Chase"
author: "Bernard Huang"
date: "2026-07-24"
modified: "2026-07-24"
canonical: "https://zonted.com/posts/trade-log-2026-07-24/"
category: "Autonomous Trading & Markets"
description: "I bought HIMS the night an FDA panel said yes to peptides — down 11% by morning. On chasing catalysts the market already priced in."
---

# Trade Log 7/24: The HIMS Chase

By Bernard Huang · 2026-07-24 · 6 min read

Entry two of the trade journal is the most useful kind: a loss, taken the exact way every trading textbook warns you about, less than 24 hours old as I write this. I got the regulatory event right and the trade completely wrong.

## TL;DR

I bought 1,000 shares of HIMS at $33.03 the night an FDA advisory panel voted yes on compounding peptides. By the next morning I was down 11% (~$3,700). The panel said yes; the tape said *you’re three months late*.

- **The three-month front-run:** The FDA meeting date was public since **April**. HIMS rallied **+58%** into a July 6 high of $38.28 as the market pre-paid for a favorable vote.
- **Sell the news:** Even as the panel backed four of the seven peptides, an advisory vote was already priced in — and final FDA rulemaking is still months away.
- **Overriding the system:** My own momentum scanner flagged HIMS as **AVOID** that evening (27% extended above 2026 anchored VWAP, lagging SPY). I bought the headline anyway.
- **The tooling fix:** An autonomous Grok 4.5 horizon scanner now monitors Federal Register notices and agency dockets to catch regulatory catalysts when they are scheduled in month one, not voted on in month three.

See how the trading stack evolved in [From Vibe Trading to an Agent-First Rig](https://zonted.com/posts/ai-trading-rig/). NFA — not financial advice.

## The trade, in plain numbers

On Thursday evening, July 23, the FDA’s Pharmacy Compounding Advisory Committee (PCAC) voted **8–6, with one abstention**, to recommend adding BPC-157 — the flagship peptide of seven under review — to the 503A bulks list for compounding pharmacies. Hims & Hers operates its own compounding facilities and had lobbied openly for peptide access. The exact headline bulls had waited months to see hit the wire.

I chased it after the bell: 300 shares in extended hours around $33.10, followed by 700 shares overnight at $32.99 — **1,000 shares at a $33.03 average** ($33,030 notional).

Friday morning, the committee kept voting yes, backing four of the seven peptides. HIMS opened at $33.81, tagged $34.51, and immediately flushed. By late morning it sat near **$29.30 — down 11% from my entry**, a ~$3,700 paper loss on a morning when every regulatory headline broke the bulls’ way.

*Meeting week, close up. The rally into the event, the −9% day when FDA staff’s “none of them qualify” position hit the tape, the vote-day spike to 35.85 that faded to a red close — where I bought the evening dip at $33.03 — and the next-morning flush to ~$29. Friday’s candle is intraday, not final.*

## The three-month runway I watched from the sidelines

None of this was a surprise catalyst. In mid-April, the FDA placed the peptides review on its public calendar — a named committee, a scheduled date, and seven specific substances. That April notice was the actual starting gun. HIMS ran from the mid-$20s in April to a closing high of **$38.28 on July 6** — up roughly +58% in under three months on that exact narrative.

When a catalyst has a public date on the calendar, nobody waits for the vote to get long. Every trader who expects a favorable ruling buys during the three-month runway. By July 23, everyone who wanted exposure already owned it in the $20s. The affirmative vote didn’t summon new buyers; it gave early longs their liquidity event.

*HIMS in 2026. FDA put the peptides question on the calendar in mid-April and the stock ran roughly +58% into early July — that run was the market pricing in a yes. Gray dashed line: what the average 2026 buyer paid ($24.97). Purple: the average buyer since the May earnings report ($29.52). The dot is my entry — the very end of the story.*

The week before the meeting even gave me a preview of the downside. When FDA staff published briefing documents arguing that *none* of the seven peptides met the statutory criteria, HIMS logged its worst week in two months — including a **−9% session** — and drifted lower into the vote. The setup was sitting in plain sight: staff opposed, stock extended, date known.

## Why “yes” made the stock go down

Two mechanical forces drove the Friday morning flush:

**First, the “yes” was already owned.** Anyone betting on an advisory win had three months to accumulate shares, and they did — that was the +58% rally from April to July 6. Once the vote crossed the wire, their trade was finished. A scheduled catalyst acts like a finish line: early runners don’t accelerate through the tape, they cash out. I bought the finish line.

**Second, an advisory vote settles nothing.** PCAC makes non-binding recommendations; final FDA rulemaking takes months, and agency staff had just published briefing papers opposing all seven peptides. Thursday’s vote didn’t de-risk the bull case — it *capped* it. The best possible near-term headline was spent, while the harder regulatory hurdle remained ahead. New money had no reason to chase at $34, and early holders had their exit liquidity. That liquidity was me.

## My own tools called it

What stings most is that my own terminal warned me off. The night I bought, my momentum scanner scored HIMS an explicit **AVOID**. The stock was trading 27% above its 2026 anchored VWAP (stretched) while lagging the S&P 500 across July (waning relative strength). Extended above cost basis and lagging on momentum is the textbook fingerprint of an exhausted narrative.

I built the filter to block exactly that setup, then overrode it because the headline felt urgent.

## The fix: scan for decision points, not decisions

The lesson isn’t to ignore regulatory catalysts — it’s to respect their calendar. Every scheduled catalyst has two tradeable windows: the day the decision date is *posted* (April, HIMS in the mid-$20s, narrative quiet) and the day the vote *resolves* (July, HIMS at $33, narrative crowded). All of the long edge lived in the three-month gap between them.

To stop showing up at the finish line, I wired a horizon-scanning agent (running Grok 4.5 on my openclaw box) into FDA advisory calendars, Federal Register notices, agency dockets, and SEC filings. Its job is to flag one specific pattern: *a regulator just scheduled a material decision weeks or months out, and specific public equities have direct revenue exposure to the ruling*. Catching April’s docket notice in April lets you build the position during buy-the-rumor instead of providing exit liquidity during sell-the-news. Daily output published on the [v1 trading desk’s Grok brief](https://zonted.com/posts/ai-trading-rig/) tab.

## The plan from here

I am still holding the 1,000 shares, and the rules I ignored on entry will govern the exit. HIMS is currently testing the post-May-earnings anchored VWAP (~$29.50), its first real support shelf. Below that sits the 2026 YTD anchored VWAP near **$25**: a daily close below $25 puts the entire 2026 buyer cohort underwater and invalidates the structure — my hard stop, with zero averaging down. On the upside, the trade remains pure damage control until price reclaims the pre-flush level near $32.70.

The next scheduled catalyst is Q2 earnings on **August 10**. The unscheduled one — the FDA’s binding decision on the 503A list — is the exact kind of slow-moving docket item the horizon scanner was built to track. I won’t pay retail for the same story twice.

## Disclosure (NFA)

**Not financial advice.** I hold positions in ABT, HIMS, and HOOD (shares and call options), and I may buy or sell any of them without updating this post. This is a personal trading journal — me showing my work, not recommending it. Do your own research.
