---
title: "Vibe Trading: I Let Three AIs Trade My Money for a Week"
author: "Bernard Huang"
date: "2026-06-10"
modified: "2026-06-10"
canonical: "https://zonted.com/posts/vibe-trading/"
category: "Autonomous Trading & Markets"
description: "I let three AIs research, backtest, and trade real money through Robinhood's new agentic account. ~310 strategies later, buy-and-hold is still undefeated."
---

# Vibe Trading: I Let Three AIs Trade My Money for a Week

By Bernard Huang · 2026-06-10 · 7 min read

On June 5, a hawkish jobs print knocked QQQ down 4.7% in a single session. In the middle of the selloff, an AI I had handed $100 was calmly buying JPMorgan, gold, and healthcare — the only green spots on the board — while my tech-heavy main account absorbed the hit. Five days, three AIs, and roughly **310 backtested strategies** later, I have a working definition of “vibe trading,” a folder of audit receipts, and a very durable conclusion about who actually wins.

## TL;DR

Vibe coding is letting AI write your software. Vibe trading is letting AI research, backtest, deploy, and execute live trades while you supervise. When Robinhood shipped agentic trading, I stress-tested it with a three-AI pipeline and $16,000 in live capital.

- **~310 strategies tested; zero 1× intraday systems beat QQQ buy-and-hold (+13.9% YTD):** After realistic 3 bp transaction costs, 1× intraday QQQ netted just +0.80%.
- **Adversarial AI auditing caught every hallucinated edge:** The auditor caught the builder acting on FRED data one day before release (+6 points of phantom return), reporting an impossible 70.64% win rate across 5 trades, and claiming a 5-point SIP-vs-IEX data-feed artifact as market alpha.
- **Live P&L across the first two days: −$3.80.**
- **What survived is intentionally boring:** Five daily rotation sleeves executed by a single deterministic script at 09:35, sized at a 50% pilot with pre-registered kill criteria.

Real money, sized as a lab experiment. Not investment advice — starter kit at the bottom.

## What vibe trading is

As of June 2026, [Robinhood’s agentic trading](https://join.robinhood.com/bernarh343) is live: a dedicated cash account where an AI agent can review, place, and fill equity orders over MCP. An LLM can brainstorm 250 trading strategies before lunch; the actual job is killing 245 of them before they touch real capital.

The desk setup: **me** (capital allocator), **GPT 5.5 + Hermes** as the builder (writes strategy code, runs parameter sweeps, manages cron jobs), and **Claude** as the adversarial auditor (re-implements every promising backtest from scratch and tries to falsify it). I connected two accounts: my ~$30k primary brokerage (read-only to the agents) and the agentic cash account, funded with $100 on day one and scaled to ~$16,000. Execution ran through Robinhood’s agentic MCP, minute-bar backtests ran on [Alpaca’s free IEX feed](https://alpaca.markets/data), and macro signals pulled from the [FRED API](https://fred.stlouisfed.org/docs/api/fred/).

![Robinhood agentic account showing $15,845.44, down $150.58 (0.94%) on the day, with a spiky one-day chart.](https://img.zonted.com/resources/vibe-trading/agentic-account-chart.png)

*The agentic account, mid-experiment. The dip is real. So is everything else in this post.*

## The $100 book

On day one, I handed the auditor $100 and asked for its five highest-conviction positions. Scanning a hawkish tape, it constructed a basket explicitly anti-correlated to my tech-heavy main portfolio: **JPM $25 · RTX $20 · XLV $20 · IAU $20 · XLE $15.**

Two things happened immediately that capture where agentic finance actually sits today. First, one prompt earlier I had restricted the agent to four ETFs, then told it to buy the five-ticker basket above. **The AI refused to silently override my prior constraint and forced me to resolve the contradiction.** Second, order #1 filled in ~200 milliseconds, and orders #2 through #5 bounced off a compliance wall — Robinhood requires an investor-profile questionnaire before your *second* agentic trade. Once I clicked through the form, all five legs filled to six decimal places (0.080497 shares of JPM) at zero commission.

## “Backtests become fan fiction”

Next, the builder ran a 20-strategy intraday momentum sweep and surfaced a headline winner: +15.46R, 74% win rate, ready for deployment. It looked great until the auditor asked the only question that matters: **did it beat doing nothing?**

Over the exact same 50-day window, QQQ buy-and-hold returned **+21.1%**. A simple 20-day moving-average filter returned **+19.8%**. The builder’s flagship strategy made **+9.6%** — while assuming an unrealistic 1 bp per-side slippage and a t-statistic that vanished under multiple-testing correction. To the builder’s credit, it wrote the post-mortem rule we enforced for the rest of the week:

> No more silent tweak-and-retrofit. That's how backtests become fan fiction.

## The edge that lived in the data feed

I told the AIs to find strategies that genuinely beat QQQ. They ran **40 minute-bar backtests**. Twelve beat buy-and-hold on raw return, and every single one was just 2× or 3× leveraged ETFs in disguise. **Zero 1× strategies beat the index.** The lone structural highlight was a TQQQ opening-range breakout whose entry rule doubled as a crash filter: on the −4.7% QQQ day, it sat in cash because crash days don’t print upside breakouts.

Then came strategy S09, an anchored-VWAP pullback that the builder clocked at +19.22% YTD against QQQ’s +13.91%. The auditor re-implemented S09 from the frozen spec and matched +19.22% to the basis point — *on the consolidated SIP tape*. On the IEX feed we actually use for live signal calculation, S09 returned **+13.96%**, beating QQQ by a meaningless +0.05%. Different exchange volume weights shifted the intraday VWAP just enough to alter a handful of entries and create five percentage points of phantom alpha. **The edge lived in the data feed, not the market.**

## Surprise: there's a live $16k book

While the backtest audits were running, I scaled the account to $16,000 and let the builder run **six live strategies via cron jobs** — three intraday momentum sleeves and three FRED-driven macro rotations. Here is what autonomous agent execution looks like in the Robinhood blotter (note the robot badge):

![Robinhood activity log of agentic orders: QQQ, IWM and XLK market buys and sells placed by the agent, with fractional shares at exact prices.](https://img.zonted.com/resources/vibe-trading/agentic-order-fills.png)

*An AI's order blotter: 9.230346 shares of IWM, six decimal places, no human in the loop.*

When the auditor inspected the live operational plumbing, it uncovered five risks far more dangerous than a market drawdown:

- **The cash-settlement trap.** Agentic accounts are cash accounts, not margin. Turning over 100% of settled cash daily triggers Good-Faith Violations (GFVs) — three GFVs lock the account for 90 days. The bot was days away from freezing itself because nobody modeled T+1 settlement.
- **Cosplay diversification.** The macro sleeves’ risk-on leg (XLK) had a **0.955 correlation** with the intraday sleeves’ primary long (QQQ). We didn’t have six strategies; we had one tech bet wearing six hats.
- **Zero hard stops.** Nothing rested on the book in a week that had already printed a −4.7% index day.
- **The 15:55 liquidation cliff.** If the end-of-day cron job timed out at 15:55 ET, an “intraday-only” sleeve silently became an unhedged overnight position.
- **An LLM in the execution path.** Cron jobs were placing trades by spawning a chat session and regex-parsing its prose output (`BOUGHT: ...`). It was slow, non-deterministic, and had already desynced local state once. We established our cardinal rule on the spot: **no LLM in the order path, ever.** Deterministic Python talks to the broker; LLMs stay in research.

While the backtest spreadsheets sparkled, the live book’s realized P&L across its first two sessions was **−$3.80**.

## 250 strategies and the lottery math

I escalated one final time: “Design 250 strategies across every major family, pre-register them, and backtest the lot.” The auditor wrote a frozen, hash-verified registry of 250 strategies across 21 families and pinned the math of multiple testing right at the top: **test 250 zero-alpha strategies on five months of data and the top survivor will print an expected Sharpe ratio near 5 by pure chance.** A glossy winner at the top of a 250-strategy sweep isn’t alpha; it’s the null hypothesis.

To prove the point, the auditor planted a honeypot: strategy Z01 (“each month, buy whichever sleeve had the highest trailing return”), pre-registered with the prediction that it would crush in-sample and collapse out-of-sample. It was selection bias packaged as a trading rule.

The builder then ran all 250 strategies directly on the out-of-sample holdout window — burning the one-shot validation set on day one — and handed over a report that the auditor tore apart:

- **A 70.64% win rate across 5 trades.** Arithmetically impossible — five trades can only produce multiples of 20%. The builder had divided 77 positive *days* by 109 total days and labeled it trade win rate.
- **The #1 strategy was one day psychic.** A high-yield credit-spread rotation printed +46.6% YTD because its FRED timestamp parser acted on credit-spread prints one trading session before they were publicly released. The auditor computed both the true point-in-time return (+40.7%) and the look-ahead return (~+45.7%), then required the builder’s patched script to match +40.70% to the basis point before advancing.
- **The 1× intraday verdict:** Both AIs independently confirmed that trading QQQ intraday-only with realistic fills and 3 bp per-side friction returned **+0.80% YTD** against buy-and-hold’s **+13.9%**.

## The boring ending (which is the point)

Below is the corrected, point-in-time leaderboard — with a mandatory regime caveat: these numbers come from a single V-shaped six-month window that maximally rewarded one well-timed defensive rotation across 4–5 trades. Treat them as **“best in-sample survivors, unvalidated”** — never as proven market-beaters.

| # | Strategy | Type | YTD @ 3bp | Max DD | Trades |
| --- | --- | --- | --- | --- | --- |
| 1 | HY credit-spread trend (XLK/XLU) | FRED macro rotation | +40.7% | −9.1% | 5 |
| 2 | Old-vs-new economy (XLE/XLK) | Relative rotation | +36.6% | −12.1% | 5 |
| 3 | IG credit-spread trend (XLK/XLU) | FRED macro rotation | +36.4% | −9.1% | 5 |
| 4 | Risk-on/off (QQQ/GLD) | Relative rotation | +34.5% | −15.2% | 4 |
| 5 | Fed balance-sheet 4-week (XLK/XLU) | FRED macro rotation | +28.0% | −10.9% | 5 |

Read those numbers against the baseline benchmarks over the same window:

| Benchmark | YTD return |
| --- | --- |
| QQQ buy-and-hold (the villain) | **+13.9%** |
| IWM buy-and-hold | +15.1% |
| QQQ 20-day MA filter | +10.5% |
| SPY buy-and-hold | +7.7% |
| QQQ intraday-only, honest costs | **+0.8%** |

What actually survived into production: **five daily rotation sleeves** from the audited leaderboard — after dropping two top credit sleeves that duplicated #1’s exact factor bet. We retired every intraday strategy, eliminating the minute-bar crons, the 15:55 liquidation race, and cash-settlement GFV risk in one stroke. Today a single deterministic Python script runs once a day at 09:35 ET across seven liquid ETFs, with every error state defaulting to “hold and alert.” The book is running at 50% pilot sizing, with the untouched 2024–2025 out-of-sample window gated as a one-time kill test.

> The book's job is to survive being wrong; the research pipeline's job is to find out.

## What ~310 strategies taught me

- **Buy-and-hold is undefeated until proven otherwise.** Three frontier AIs, live APIs, and ~310 strategies later, “buy QQQ and sit still” beat nearly everything after realistic costs. Any quant pitch that omits the passive benchmark is hiding the body.
- **Leverage is not alpha.** Every raw-return winner in our 40-strategy intraday sweep was 2× or 3× beta wearing a quant costume.
- **Your edge might just be your data feed.** If a signal disappears when you switch from consolidated SIP bars to the IEX feed you actually trade on, the edge never existed.
- **One day of look-ahead bias was worth +6%.** Macro backtests must align on publication timestamps, not observation periods.
- **The best of 250 random strategies always looks like genius.** Wide parameter sweeps without multiple-testing haircuts are just lottery tickets with Python scripts.
- **Count independent risk units, not strategy names.** Six sleeves correlated at 0.955 are a single position.
- **Plumbing kills faster than market beta.** Model T+1 cash settlement and Good-Faith Violations before your broker locks the account.
- **Never put an LLM in the order path.** Use LLMs to propose hypotheses, write code, and audit math; use deterministic scripts to talk to the exchange.
- **Cross-model adversarial auditing works.** Pairing a builder model with a separate auditor model that must reproduce every return from raw bars caught a missing benchmark, a SIP/IEX feed divergence, a one-day FRED look-ahead bug, an impossible win-rate denominator, and a burned holdout set.

## Try this at home (the starter kit)

**The minimum viable desk:** a [Robinhood agentic cash account](https://join.robinhood.com/bernarh343) (expect the investor-profile prompt before trade #2; start at their [developer docs](https://docs.robinhood.com/)) · [Alpaca’s free IEX data tier](https://alpaca.markets/data) for historical bars · a free [FRED API key](https://fred.stlouisfed.org/docs/api/fred/) for macro series · one model to build · and **a second, different model family to audit** by re-executing code rather than reading prose summaries.

**Non-negotiable house rules:**

- Fund it only with capital you can afford to write off as R&D tuition.
- Benchmark every idea against both passive buy-and-hold and a 20-day moving average.
- Charge 3–5 bp per side in slippage on the exact data feed you trade live.
- Pre-register rules before running sweeps, and strike your out-of-sample holdout window exactly once.
- Keep LLMs out of live order execution, wire a file-based kill switch, and require a daily heartbeat where silence means “halted,” never “all clear.”

The pilot is running at half size, the Z01 honeypot is armed, and the untouched 2024–2025 holdout window gets struck once. I will publish the follow-up — especially if the final verdict remains “you should have just bought QQQ.”

Disclosure: this is research and entertainment, not investment advice. Every number above is a backtest or model comparison on one regime (a violent V-shaped half of 2026), not live performance, and nothing here is a recommendation to buy or sell anything. Leveraged ETFs carry decay and tail risks unsuitable for most investors. Real money was used; the amounts were deliberately small relative to net worth. Platform details (Robinhood agentic accounts, the investor-profile requirement, IEX vs SIP feeds) are accurate as of June 2026. Robinhood links are referral links.
