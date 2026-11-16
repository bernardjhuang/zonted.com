---
title: "The Option Was Green. The Trade Wasn’t."
author: "Bernard Huang"
date: "2026-08-05"
modified: "2026-08-05"
canonical: "https://zonted.com/posts/mdb-option-expiry-date-risk/"
category: "Autonomous Trading & Markets"
description: "I bought MDB calls around an estimated earnings date. The official date landed after expiry—and a green midpoint mark hid a red executable exit."
---

# The Option Was Green. The Trade Wasn’t.

By Bernard Huang · 2026-08-05 · 6 min read

The MongoDB thesis was working. The stock was up 6.89%, my $400 calls were marked up 14.95% on the day, and Robinhood showed a green position. Then a two-line press release exposed the operational mistake: MongoDB’s newly confirmed earnings date was September 1. My calls expired August 28.

## TL;DR

I built an earnings swing around an estimated date, then bought an expiration with almost no schedule buffer. When MongoDB finally confirmed the real date, the contract no longer reached the event.

- **Two August 28 $400 calls** cost $17.25 each, or $3,450 total. The official earnings call landed four calendar days after expiration.
- The app’s $18.68 “current price” was the rounded midpoint of a **$16.95 bid and $20.40 ask**. Midpoint P&L said +$286; crossing to the bid said −$60 before fees.
- The new rule: an event-dependent option does not get bought until the date is confirmed by company IR. If the date is still estimated, use materially more time or do nothing.

The lesson is about process, not MongoDB. A good thesis expressed through the wrong contract is still a bad trade. NFA—not financial advice.

[

![Side-by-side screenshot showing MongoDB’s September 1 earnings announcement and a Robinhood position in two August 28 MDB $400 calls, with a blue arrow marking the option chart’s sudden drop.](https://zonted.com/posts/mdb-option-expiry-date-risk/mdb-earnings-expiry-mismatch.png)
](https://zonted.com/posts/mdb-option-expiry-date-risk/mdb-earnings-expiry-mismatch.png)
*August 4, 2026, 2:39 p.m.: the company confirms September 1 earnings while the August 28 call chart reprices. The screenshot is the whole lesson in one frame. Click to open it full-size.*

## The trade, in plain numbers

This was a momentum swing into MongoDB earnings. The stock had reclaimed its earnings and yearly VWAPs, and I expressed that view with two out-of-the-money calls.

| Contract | MDB Aug. 28 $400 call |
| --- | --- |
| Position | 2 contracts |
| Average cost | $17.25 / $3,450 total |
| Underlying in screenshot | $382.64 (+6.89%) |
| Option mark | $18.68 (+14.95% that day) |
| Displayed market | $16.95 bid / $20.40 ask |
| Confirmed earnings | Sept. 1, after close |
| Expiration mismatch | 4 calendar days too early |

At $382.64, the stock sat $17.36 (4.54%) below the $400 strike with 24 calendar days to expiration—reasonable for a momentum swing, reckless once the named catalyst landed four days past expiry.

## The date was never confirmed

I had been treating August 25 as the earnings date because that was the estimate in the market-data feed. The August 28 expiration looked like it cleared the event by three days. That was false precision.

On August 4, MongoDB [officially announced](https://investors.mongodb.com/news-releases/news-release-details/mongodb-inc-announces-date-second-quarter-fiscal-2027-earnings) that fiscal Q2 results would arrive after the market close on Tuesday, September 1. The company did not move a confirmed date. **I promoted an estimate into a fact.**

The press release hit at 2:39 p.m., and the option chart cliffs at the same timestamp as the market strips earnings-event premium out of the August contract. One screenshot cannot explain every tick, but the date confirmation and the repricing arrived together.

> The catalyst did not disappear. It moved outside the instrument I had chosen to own it with.

## The green mark was not an exit

Robinhood showed the calls at $18.68 and the position at $3,736. Against a $3,450 cost, that is a pleasant-looking **+$286, or +8.3%**.

But $18.68 was not a trade. It was the rounded midpoint of a $16.95 bid and a $20.40 ask. The spread was $3.45—**18.5% of the midpoint**. Selling immediately into the displayed bid would have produced about $3,390, or **−$60 (−1.7%)** before fees. A patient limit order might have done better, but the green app mark was not executable proof of profit.

Illiquid options let the broker interface tell a flattering story: mark-to-mid is for estimating, bid-side liquidation is what you can actually bank.

## Three mistakes, one screenshot

1. **I traded an estimated catalyst as if it were confirmed.** The source hierarchy was backwards. A broker calendar is a lead; company investor relations is the fact.
2. **I bought almost no schedule buffer.** Even if August 25 had been right, three days after earnings left little room for a reschedule, delayed report, or post-event trade management.
3. **I let the midpoint flatter the position.** An 18.5% spread meant the displayed P&L and the immediate exit P&L described different trades.

“The MongoDB thesis was wrong” is not on that list—the underlying was ripping higher. Separating thesis from instrument matters: the lesson isn’t “don’t trade earnings,” it’s “don’t rent optionality for an event the contract cannot reach.”

## The new house rules

- **Every event gets a source label:** confirmed, estimated, or unreleased. Only company IR or an SEC filing upgrades earnings to confirmed.
- **Expiration must clear a confirmed event by at least one full weekly cycle.** For a normal earnings swing, I want more than a three-day landing strip. If the date is estimated, I use materially longer duration or wait.
- **Liquidity gets its own gate.** I record bid, ask, midpoint, spread as a percentage of midpoint, and open interest before entry. A double-digit spread needs a damn good reason.
- **P&L is shown two ways:** mark-to-mid and executable-side. If the story changes depending on which one I use, the position is less liquid than the headline suggests.
- **A thesis and its instrument are reviewed separately.** “Still bullish” is not a reason to keep the wrong expiration.

This was a cheap lesson precisely because the stock moved in my direction. That is also what makes it dangerous: a profitable outcome can launder a bad process. Writing it down prevents “green means smart” from becoming the rule.

## Disclosure (NFA)

**Not financial advice.** The screenshot shows an open position of two MDB August 28 $400 calls at that moment; the position may change after publication. Prices and quotes are a timestamped snapshot, not a promise of available execution. This is a personal trading journal—me showing the mistake, not recommending MongoDB or any option strategy.

Sources: MongoDB’s August 4, 2026 earnings-date announcement via [Investor Relations](https://investors.mongodb.com/news-events/news-releases), plus the supplied Robinhood position screenshot. Calculations use the visible two-contract position, $17.25 average cost, $18.68 mark, and $16.95/$20.40 market.
