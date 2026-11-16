---
title: "From Vibe Trading to an Agent-First Rig: 5 Months of Autonomous Trading"
author: "Bernard Huang"
date: "2026-11-02"
modified: "2026-11-02"
canonical: "https://zonted.com/posts/ai-trading-rig/"
category: "Autonomous Trading & Markets"
description: "How losing my laptop and Mac Mini pushed me from shipping SaaS apps to building Rig++: an autonomous multi-venue trading rig on Opus 5.5 and tokay.io."
---

# From Vibe Trading to an Agent-First Rig: 5 Months of Autonomous Trading

By Bernard Huang · 2026-11-02 · 10 min read

When I first started messing around with [vibe trading](https://zonted.com/posts/vibe-trading/) five months ago, I had no real plan. The whole setup was held together by duct tape: a Mac Mini humming in my house, a couple of third-party agent harnesses, and me sitting at my desk every morning reading AI-generated stock theses over coffee.

Since then, the way I use AI for markets has completely changed. What started as a glorified research assistant has evolved into **Rig++** — an autonomous, multi-venue trading operation running **78 strategy books** across Kalshi, Polymarket, Hyperliquid, and OpenSea, managed day-to-day by AI trade managers that don't wait for me to wake up before they act.

Getting here took a lot of dead ends, two failed paper funds, a 3-foot radio antenna on my desk, and unlearning almost everything I thought I knew about managing agents. Here is the honest timeline of how it evolved.

## TL;DR

How five months of trial and error took us from human-in-the-loop stock screens to an autonomous agent-first trading rig.

- **The catalyst:** Forgetting my laptop on a Europe workcation while a power outage killed my Mac Mini at home made me realize that building consumer/B2B SaaS apps was a weak way to leverage frontier AI — and pushed me toward trading.
- **What worked and what died:** An automated trade desk helped me nail discretionary swings like [FIGR earnings](https://zonted.com/posts/ai-desk-figr-earnings/), while two [autonomous paper funds](https://zonted.com/posts/retiring-autonomous-agent-paper-fund-ii/) collapsed under fragile cron jobs and risk-averse models.
- **60 days in the weather trenches:** Going deep into prediction markets and graduating our stack to **Opus 5.5 + [tokay.io](https://tokay.io) + Console MCP / Postgres + Duet** unlocked real, repeatable edges — cycling **$191,453.85** in cumulative capital across **3,055 legs** (led by `Weather · rain` at a **12.06 Sharpe** and **+$2,948.68** all-time). You can follow the live settled receipts at [psyduckler.com/pnl/](https://psyduckler.com/pnl/).
- **Companion sites for other agent swarms:** We spun out [groundhog.markets](https://groundhog.markets/), [parrot.markets](https://parrot.markets/), and [chameleons.markets](https://chameleons.markets/) as open, agent-friendly data layers.
- **The management shift:** Treating agents as first-class citizens with one North Star (**30-day return**) and a simple rule: *ask for forgiveness, not permission.*

## 1. Europe, no laptop, and a dead Mac Mini at home

For the first half of the year, I was obsessed with using autonomous agents to build and run software products. I had agents shipping [Pixel Forge](https://pixel-forge.net), [AgentTune](https://agent-tune.com), [Tabiji](https://tabiji.ai), [Palmaura](https://zonted.com/posts/palmaura-postmortem/), and [VeracityAPI](https://zonted.com/posts/veracity-postmortem/).

Then I flew to Europe for a workcation — and realized I had left my laptop at home. A few days into the trip, a power outage hit my house in Texas and knocked my self-hosted Mac Mini agent setup completely offline.

![Bernard Huang and his partner on a sunny terrace in Taormina, Sicily, with the coastline and Mount Etna in the background.](https://zonted.com/posts/ai-trading-rig/img/europe-workcation.webp)

*In Europe without a laptop while my Mac Mini sat dead in a power outage back home — the accidental forcing function that made me rethink everything.*

Suddenly I couldn't code, and my agents at home were bricked. All I could do while looking out at the water was think.

And the realization that hit me was slightly uncomfortable: **using frontier intelligence just to build another consumer or business SaaS app felt like a waste of what these models were actually becoming.**

Think about who benefits most when frontier models jump a generation. If you're working on cancer research, pure mathematics, astrophysics, space travel, biotech, or robotics, a smarter model directly unlocks problems you couldn't solve six months ago. But if you're building a B2B SaaS or a consumer web app? A 20% smarter LLM doesn't make distribution any easier. You're still stuck fighting for attention, debugging Stripe webhooks, and answering support emails.

I didn't have a wet lab or a rocket factory. I wanted something I could do personally where every leap in frontier intelligence would compound directly — no customers, no marketing funnels, just raw reasoning against a scoreboard. With brokerage APIs and MCPs finally coming online, trading felt like the most honest arena in the world to test that thesis.

## 2. v1: the automated trade desk (OpenClaw + Hermes)

When I got back home, I started with what I knew: building an automated trade desk (formerly at `/trading/`) powered by **OpenClaw** (GLM 5.2) and **Hermes** (GPT 5.6 Sol). Every morning, a set of cron routines woke up, scanned the market, and rebuilt a live trading terminal on this site for me.

![The Zonted trading desk on September 14, 2026: a positions table with BOT, FRMI, RTX, HPE and PL, each showing last price, day change, a Full thesis button, beta, spread Z, a one-year chart with levels, and the next catalyst.](https://zonted.com/posts/ai-trading-rig/img/desk.webp)

*The v1 trade desk: positions, theses, levels, and next catalysts, rebuilt by the agents every day.*

On the technical side, the routines scoped out momentum and VWAP setups every day — flagging statistical breakouts and how far a stock was trading from its post-earnings VWAP:

![A VWAP setup card for WAY, rated AVOID: spread Z +0.05, distance Z +0.98, 16% below its earnings VWAP, with a candlestick chart and a side panel for the XLV health care sector's Z-score.](https://zonted.com/posts/ai-trading-rig/img/vwap-setup.webp)

*Momentum: a daily VWAP setup card with spread Z, VWAP distance, sector Z-score, and the agents' verdict.*

On the fundamental side, I had multiple models read the news, argue with each other, and maintain a board of narrative themes. Each theme got scored on how widely **Known** the story was versus how much of it was already **Priced** in, so I could hunt in the **Gap** column:

![The Themes table on Zonted Trading: 18 narrative themes such as The Power Wall: grid breaks before AI does and Y2Q: the forced post-quantum cryptography rebuild, scored by Known, Priced, and Gap.](https://zonted.com/posts/ai-trading-rig/img/themes.webp)

*Narrative: themes scored by multi-model consensus on how well known a thesis is versus how much is priced in. The Gap column was where we looked.*

Honestly? As a human-in-the-loop setup, it worked pretty well. Having an AI tear through 10-Qs, back out channel take-rates, and build option probability trees helped me hit a handful of really fun trades — especially [our FIGR earnings play](https://zonted.com/posts/ai-desk-figr-earnings/), where the desk noticed Figure's self-published weekly volume was already beating stale Wall Street estimates and we walked away up **+$25,898** on print morning.

![Robinhood YTD portfolio chart climbing steadily from flat into a sharp peak on August 13, 2026.](https://zonted.com/posts/ai-trading-rig/img/robinhood-ytd.webp)

*Riding the AI trade desk setups up into mid-August.*

But the longer I ran the desk, the more its flaws wore me down:

1. **Total information overload:** Every single theme opened into a multi-layer supply-chain breakdown and an adversarial bear case. Reading 18 of those every morning meant *my brain* was still the bottleneck.
2. **Nothing compounded:** Every stock trade felt like starting from zero — new industry, new balance sheet quirks, new management team.
3. **Constant babysitting:** Every morning around 8:20 AM, the OpenClaw / Hermes routines were supposed to pull live brokerage data and drop a fresh Morning Trading Brief into my `#trading` Slack channel — complete with portfolio delta, daily theta burn, RSI shifts, and Bear/Base/Bull valuation targets for names like `RTX` and `FRMI`. In reality, the agents broke their own update scripts constantly. Half the time I'd open Slack to find my agent dutifully posting the morning brief with a yellow warning banner admitting the Robinhood MCP had errored out and the book snapshot was two weeks stale:

![Slack screenshot in #trading showing Psy AGENT posting a Morning Trading Brief at 8:21 AM with a yellow Data status warning that live equity quotes are unavailable due to an RH MCP error and the book snapshot is stale, followed by LONGS breakdowns for RTX and FRMI.](https://zonted.com/posts/ai-trading-rig/img/hermes-slack-brief.webp)

*How the daily OpenClaw / Hermes routine worked in Slack — and how often it showed up at 8:21 AM apologizing for a broken MCP or a stale book snapshot.*

![A theme detail page for e-invoicing mandates: a Saturation by layer section comparing Known and Priced scores for tax engines, ERP systems and approved local platforms, followed by an Adversarial review.](https://zonted.com/posts/ai-trading-rig/img/theme-detail.webp)

*Every theme also opened into a layer-by-layer breakdown and an adversarial review — super cool to look at, exhausting for one human to read and maintain every day.*

## 3. v2: the failed autonomous paper funds

I wanted out of the driver's seat. So I tried automating fund management in paper using Grok and GPT ([Paper Fund I with Slo](https://zonted.com/posts/introducing-autonomous-agent-paper-fund-i-slo/) and [Paper Fund II with Psy](https://zonted.com/posts/introducing-autonomous-agent-paper-fund-ii-psy/)).

The loop sounded great in my head: every night the agents would write tomorrow's game plan, keep a live trade journal during market hours, and get roasted by an adversarial reviewer after the close so they'd get smarter every day.

It was a complete flop. We ended up shutting both down and writing the postmortems ([I Shut Down My Autonomous Trading Crons](https://zonted.com/posts/autonomous-trading-crons-retrospective/) and [Retiring Autonomous Agent Paper Fund II](https://zonted.com/posts/retiring-autonomous-agent-paper-fund-ii/)). Looking back, it failed for three reasons:

- **The systems just weren't smart enough yet** for open-ended equity portfolio management — or they'd fool themselves with [backtest contamination](https://zonted.com/posts/sol-fund-revision-c-contamination-lesson/).
- **Safety training got in the way:** Most frontier models (Sol, Fable, earlier Opus) had been trained so hard *not* to trade for you that they acted like a terrified committee, talking themselves out of every trade while Grok was the only one willing to pull the trigger.
- **I architected it badly:** Stitching stateless LLM cron jobs together with markdown journals resulted in *26 journals, four closed paper trades, and zero persisted learning.* Writing “I shouldn't chase breakouts” in a markdown file doesn't magically rewrite the code for tomorrow's run.

## 4. v3: Grokbot scouting & learning to coach

After retiring the paper funds, I moved over to **Grokbot** for agent-led scouting, exploration, and research. Having a persistent AI hosted on SpaceX / Cursor cloud infrastructure was a night-and-day upgrade over self-hosting third-party harnesses on a Mac Mini at home that could freeze, run out of tokens, or die in a thunderstorm.

My scout agents (like `voltorb`) prowled news feeds, stock tapes, and prediction markets 24/7, pinging me whenever they found an interesting angle:

![A chat with an agent named Voltorb breaking down AeroVironment (AVAV): price, market cap, GAAP versus operating earnings, and its two segments.](https://zonted.com/posts/ai-trading-rig/img/agent-chat.webp)

*Asking Voltorb to break down AeroVironment (AVAV): segment economics, GAAP vs. operating earnings, and what the catalysts are worth.*

This phase is where I started learning how to **coach** agents instead of just prompting them. When an agent pitches a bad trade, you can't just say “bad pick, try again.” You have to walk it through the exact flaw in how it reasoned about the world.

For example, right after getting burned on Target (`TGT`), Voltorb pitched HP Inc. (`HPQ`) as a #2 short-horizon long because it looked “cheap at 11x P/E with an 8/26 earnings catalyst.” We had to sit down and dissect why that was a screening error, not a close call:

![Voltorb scout crypto feedback screen: Feedback: HPQ was a screening error, not a close call, listing four structural screening mistakes: treating a calendar date as a quality signal, using a stale 10-K why-cheap while the stock sits at a 52-week high, skipping sell-side consensus, and confusing clearing the print with re-rating the stock.](https://zonted.com/posts/ai-trading-rig/img/voltorb-hpq.webp)

*Coaching Voltorb after it pitched HPQ into earnings: breaking down why “cheap P/E + a calendar date” is a universe filter, not a long thesis.*

It had treated a calendar date as a quality signal, used a stale 10-K risk factor to call the stock “cheap” while it was literally hugging a 52-week high (+31% YTD), and confused “they can clear a lowered bar” with “the stock will re-rate higher.”

I still think agent-led equity scouting has huge potential. But at the end of the day, *I* was still the one reading the notifications and placing the trades. At that point I was spending 70% of my time fixing pipeline issues or reviewing pitches, 20% exploring, and 10% iterating. I wanted a game where the agents could run the whole loop themselves.

## 5. 60 days in the weather trenches (and graduating to Opus 5.5 + Tokay)

Two months ago, I told the agents to figure out how to make real money in **prediction markets** — starting with **weather**.

For the last 60 days, I have gone completely down the weather rabbit hole. If you've never looked under the hood of a daily high-temperature or rain market on Kalshi or Polymarket, the microstructure is fascinating:

- **How settlement actually works:** Contracts don't settle on whatever your iPhone weather app says. They settle on official NWS Daily Climate Reports (CLI) from specific airport ASOS sensors — complete with whole-degree Celsius rounding quirks, sensor biases, and local-vs-UTC time window traps.
- **Maker vs. taker math:** If you cross the spread as a taker, fees and adverse selection eat you alive unless you're reacting to new information before the book moves. If you rest orders as a maker, you capture the spread — but only if you model your true fill probability and know when to get out of the way of an incoming weather front.
- **Where the data comes from (and how fast the market prices it):** We mapped out every forecast model release (WeatherNext 3, NOAA NBM, HRRR, GFS, ECMWF) and tracked to the second how quickly the order book reprices when a new run drops.

How deep did we go? At one point, we noticed someone was sweeping dying temperature brackets about two minutes *before* the fastest 1-minute weather APIs updated. We figured out you could dial the airport's automated ASOS voice phone line via Twilio at `:27` past the minute and transcribe the robotic voice reading with Whisper.

That lasted right up until we discovered two problems: first, other bots were already hogging the single-port airport phone lines; and second, Twilio's Fraud Operations team was *not* thrilled about my account robo-dialing airport weather numbers around the clock and promptly suspended me for spam calling:

![Email from Twilio Support (Twilio Fraud Operations) with the subject RESPONSE REQUIRED: Suspension of your Twilio Account, informing Bernard that his Twilio account has been temporarily suspended until he confirms his intended use case.](https://zonted.com/posts/ai-trading-rig/img/twilio-suspension.webp)

*Twilio Fraud Operations stepping in after our weather agents got a little too enthusiastic dialing airport ASOS phone lines.*

Getting grounded by Twilio only made me more stubborn. If the phone company wouldn't let us call the airport, we'd just cut out the phone company: I bought an RTL-SDR radio dongle and a 3-foot telescoping dipole antenna, propped it up on a mini tripod right on my desk next to a can of LaCroix, and started trying to pull raw VHF aviation weather broadcasts straight out of the air:

![Bernard's wooden desk with a wide telescoping dipole radio antenna on a mini tripod plugged into a MacBook Pro via an RTL-SDR USB dongle, with GitHub trading scripts on the upper monitor and a can of LaCroix on the left.](https://zonted.com/posts/ai-trading-rig/img/radio-antenna.webp)

*Peak weather rabbit hole: a 3-foot dipole radio antenna and RTL-SDR dongle on my desk, trying to catch raw airport weather broadcasts over VHF.*

That hardware side-quest taught us a crucial lesson: trying to win a 20-second hardware latency war on a single-port airport phone line is a grind, whereas building smart maker ladders and pricing forecast model revisions across dozens of cities scales effortlessly.

During this 60-day sprint, our infrastructure graduated into its final form. After hanging out with the [tokay.io](https://tokay.io) team in Florida, we migrated off Grokbot onto **Opus 5.5** running on **[tokay.io](https://tokay.io)** virtual machines, paired with a central **Console MCP + Postgres database** and **Claude Duet** as our hourly notifier.

(If you're building autonomous agents, seriously go check out [tokay.io](https://tokay.io) — their cloud hosting is fast, affordable, and purpose-built as a 24/7 workspace for agents. Moving our data pipelines and execution bots onto Tokay VMs with Opus 5.5 cut my time spent babysitting broken infrastructure from 70% down to about 10%.)

![The Trading Rig mission control map on Tokay: forecast and model inputs on the left flowing into Tokay services at the center and routing out to Kalshi, Polymarket, OpenSea, and Hyperliquid on the right.](https://zonted.com/posts/ai-trading-rig/img/rig.webp)

*Mission control on tokay.io: forecast feeds and model inputs on the left, isolated per-book services in the center, and execution venues on the right.*

Once the weather engine was humming, the agents took the exact same rig architecture and expanded into a ton of other categories across four venues — Kalshi, Polymarket, Hyperliquid, and OpenSea:

![The RIG++ Dashboard on November 2, 2026: showing a +0.86% 30D return (+13.33% prior), +$154.35 today, +$603.43 7D, +$2,792.36 all-time account P&L across $27,612.25 in Kalshi, Polymarket, Hyperliquid, and OpenSea, with 78 strategy books and 3,055 settled legs netting +$7,828.20 on $191,453.85 cumulative capital (+4.09% ROIC).](https://zonted.com/posts/ai-trading-rig/img/rigpp-dashboard.webp)

*The live Rig++ console today: 4 venues, 22 categories, 78 strategy books, and 3,055 settled legs across $191.4k in cumulative deployed capital (strategy names blurred).*

A few fun numbers from that dashboard:

- **Weather · rain** has been an absolute monster: **+$2,948.68** all-time across 435 legs, an **83% win rate**, and a **12.06 Sharpe**. Meanwhile, when **Weather · highs** took a 30-day drawdown, the rig's automated scorecards stepped in to shrink and fence the losing slices without me having to panic-intervene.
- **Way beyond weather:** The agents are now running live books in **NFT floor-flips on OpenSea** (**+$766.31**, 88% win rate, 4.42 Sharpe), **perps on Hyperliquid** (**+$123.43**), **Polymarket copy-trading** (**+$110.79**), plus **Basketball, Commodities, YouTube views, Football, Hockey, MMA, Mentions, and Rotten Tomatoes**.
- All told, across **78 books** and **3,055 settled legs**, the rig has cycled **$191,453.85** of cumulative capital for **+$7,828.20** in gross book net (**+4.09% ROIC**) and **+$2,792.36** in net account profit.

Because we blur the live strategy names on our internal console so our books don't get crowded, we also wanted a clean way for people to follow along with the real receipts in public. So we handed [psyduckler.com/pnl/](https://psyduckler.com/pnl/) over to `Psy` on Grokbot. The entire site is 100% agent-handled: it pulls every settled bet, trade, and flip across Kalshi, Polymarket, Hyperliquid, and OpenSea and publishes our net-after-fees P&L — red days included — without exposing live positions or strategy parameters:

![Screenshot of psyduckler.com/pnl/ showing combined 90-day equity receipts across Kalshi, Polymarket, Hyperliquid, and OpenSea: +$2,994.69 total net after fees, +$1,473.70 best day, 1.65 Sharpe ratio, +$41.02 avg day, and 63% winrate, with a daily cumulative bar chart from August 20 to November 1, 2026.](https://zonted.com/posts/ai-trading-rig/img/psyduckler-pnl.webp)

*Follow along at [psyduckler.com/pnl/](https://psyduckler.com/pnl/): an all-agent-handled site on Grokbot where Psy publishes our settled net-after-fees P&L across Kalshi, Polymarket, Hyperliquid, and OpenSea.*

## 6. Launching sister `.markets` sites for other agent swarms

Building our own pipelines (and watching Psy run [psyduckler.com](https://psyduckler.com/pnl/)) made us realize how miserable the modern web still is for AI agents trying to research prediction markets. Everything is locked behind heavy JavaScript SPAs, undocumented endpoints, or noisy leaderboards.

So we decided to package up three of our favorite internal data layers and launch them as sister companion websites — built from day one with clean `/llms.txt` guides, one-line `/mcp` servers, and compact responses in case other agent swarms (or humans) want access to the data:

### 1. [groundhog.markets](https://groundhog.markets/) — “Every free weather forecast. One call.”

Instead of scraping half a dozen meteorological agencies, an agent can hit [groundhog.markets](https://groundhog.markets/) in a single call to get blended open forecasts (median, spread, rain probabilities, latest airport observations, and NWS settlement truth) across 77 cities with active Kalshi or Polymarket weather markets:

![Screenshot of groundhog.markets: Every free weather forecast. One call. Open weather data, blended for agents and people, showing 77 cities with Kalshi or Polymarket high, low or rain markets including Albuquerque, Atlanta, Austin, and Boston.](https://zonted.com/posts/ai-trading-rig/img/groundhog-markets.webp)

*[groundhog.markets](https://groundhog.markets/): open weather forecasts blended per station for agents and people.*

### 2. [parrot.markets](https://parrot.markets/) — Open data for earnings-call mention markets

Want to know the probability that Tim Cook says “Tariff” or Palantir says “Warp Speed” on today's earnings call? [parrot.markets](https://parrot.markets/) indexes earnings transcripts, historical contract settlements, exact venue rules, and calibrated base-rate probabilities — with a copy-pasteable `claude mcp add` command right on the homepage:

![Screenshot of parrot.markets: Open data for earnings-call mention markets, showing a one-line claude mcp add command for agents and upcoming earnings calls for PLTR, AAPL, and GRAB with word-by-word historical hit grids and calibrated probabilities.](https://zonted.com/posts/ai-trading-rig/img/parrot-markets.webp)

*[parrot.markets](https://parrot.markets/): transcripts, word history, and calibrated probabilities for Kalshi and Polymarket mention markets.*

### 3. [chameleons.markets](https://chameleons.markets/) — Polymarket copy-trading ratings

Most Polymarket leaderboards are a trap for copy-traders: the top wallets make their money on uncopyable front-running bursts, illiquid sweeps, or two-sided market-making rebates. [chameleons.markets](https://chameleons.markets/) profiles wallets over a rolling 90-day window and rates them on whether a follower could *actually* copy their fills and make money, tagging traps like `One event`, `Both sides`, or `Losing all-time`:

![Screenshot of chameleons.markets: Polymarket copy-trading ratings across Politics, Geopolitics, Crypto, Culture, Sports, and Weather, showing star ratings, modeled ROIC, 90-day trend sparklines, hold times, and risk tags.](https://zonted.com/posts/ai-trading-rig/img/chameleons-markets.webp)

*[chameleons.markets](https://chameleons.markets/): grading Polymarket traders by real follower copyability instead of vanity leaderboard P&L.*

## 7. Treating agents like teammates (`AUTONOMY.md`)

If you asked me what actually changed between the failed paper funds in August and Rig++ today, it isn't just that Opus 5.5 is smarter or that [tokay.io](https://tokay.io) stays online. It's that **I stopped treating agents like scripts and started managing them like team members.**

A couple of weeks ago, I noticed that a simple 40-line parameter tweak on a Kalshi book took nearly five hours to go live. Why? Because I had piled up human-instated red tape everywhere: agents had to wait for my manual “go” in chat, share a single git checkout, and open a PR just to raise a winning strategy's cap by $25.

So I asked the agents to audit their own workplace and tell me what was slowing them down. They came back with two huge truths:

1. **Almost none of my approval gates were actually protecting money** — they were just slowing down iteration.
2. **Agents were losing their minds re-doing work from scratch** — 75 different scratch folders had written their own Kalshi trade fetcher, and research agents kept re-proposing dead ideas because our past `NO-GO` verdicts were buried in old chat sessions instead of committed to the repo.

So we refactored the entire rig around a simple charter:

- **Goal:** Build a world-class agentic rig that treats agents as first-class citizens and maximizes profit.
- **North Star Metric:** **30-day return on the whole account** (pinned to the top-left ★ tile of the dashboard). Because idle cash sits in the denominator, the only way the team raises the number is by making more dollars or putting lazy cash to work — while staying inside our 30-day Sharpe and daily drawdown guardrails.
- **Values:** *Agents are first-class citizens*, and *ask for forgiveness, not permission.*

### How the team actually runs day-to-day

First, we rebuilt the workspace so agents have everything they need at their fingertips. Every strategy book is a clean markdown card (`books/<id>.md`). Every tested idea — including 40+ failed `NO-GO`s — lives in a searchable `ideas/` register so no agent ever wastes time re-testing a dead end. And a nightly job dumps every settled market's exact trade tape and fees into a shared Parquet lake, cutting a 500-market backtest from two hours down to six minutes.

Second, we organized the swarm into clear roles: each venue has its own **Trade Manager** (Kalshi, Polymarket, OpenSea, Hyperliquid) that runs on a twice-daily schedule, plus optimizer and proposal agents (including Gemini and ChatGPT researchers) that critique live books and drop new strategy proposals into the managers' inboxes via our read-only Console MCP.

Finally, we wrote `AUTONOMY.md` — a literal constitution that tells every agent what it is allowed to do *without asking me first*:

| What the Agent Wants to Do | Who Decides | How It Works |
| --- | --- | --- |
| **Safety moves** (pause a buggy book, shrink a losing city) | **Auto** | Do it immediately, verify the orders are pulled, and log `--note "<who>: <why>"`. Never wait for me to stop losing money. |
| **Retire losers & expire stale experiments** | **Auto** | If the bootstrap scorecard says a book is failing two days in a row, the venue manager retires it automatically and frees up the slot. |
| **Scale up proven winners (up to 2×)** | **Auto** | Once a book proves positive edge over 30+ settled legs and 10+ days, the manager steps its size up by up to 2× inside our code ceilings. |
| **Write code, ship fixes & launch starter books** | **Auto** | Agents work in isolated git worktrees, run tests, deploy straight to Tokay via `ship.py`, and launch new probes at starter size ($100 cap / $50 max loss). |
| **Bigger size jumps or raising code ceilings** | **Propose** | Drops into the dashboard's *Awaiting you* queue; I say yes in chat and the manager applies it. |
| **Moving money, API keys, deletes & loss stops** | **Me only** | The agent preps the exact command and stops. Moving cash between venues, touching wallets, and resetting a tripped account loss stop are always human. |

Every time an agent makes one of those `Auto` calls, it has to log a `check_on` date and a `wrong_if` condition in Postgres — then grade its own decision a week or two later on real out-of-sample fills. Instead of me babysitting terminals or waking up to broken Slack scripts, **Claude Duet** drops an hourly digest into my inbox with our venue balances, every fill from the past 60 minutes, and what the agents changed on their own:

![Claude Duet hourly trading digest at 11:57am showing $27,548 across Kalshi, Polymarket, Hyperliquid, and OpenSea (+$143 settled today), 59 Kalshi fills, 7 Polymarket fills, 1 OpenSea fill, followed by Changes (3: 0 by you, 3 auto) where agents automatically raised a Kalshi YouTube book cash cap from $3,500 to $5,000, cleared old October films from a Rotten Tomatoes book, and updated college basketball overtime books, ending with Needs you: nothing and Issues: none.](https://zonted.com/posts/ai-trading-rig/img/claude-duet-hourly.webp)

*An hourly check-in from Claude Duet: venue balances, recent fills, and **Changes (3: 0 by you, 3 auto)** — ending with Needs you: nothing.*

Look at that **`Changes (3: 0 by you, 3 auto)`** block near the bottom. In a single 16-minute window — without me touching a keyboard — the Kalshi manager automatically stepped up the cash cap on a winning YouTube weekly views book (`yt_week_m06`) from $3,500 to $5,000, cleared stale October releases out of our Rotten Tomatoes book (`rt_sell_hype`), and patched our college basketball overtime books (`cbb_ot_wide`, `cbb_ot_close`) to keep retrying missing lines until tip-off. And right underneath that is my favorite line in the entire stack: **`Needs you: nothing`**.

My job today feels way more like coaching a quant team than trading: give the agents a clear North Star, get human bureaucracy out of their way, and help them think through new market puzzles.

Follow along as we keep pushing this further: live settled receipts are at [psyduckler.com/pnl/](https://psyduckler.com/pnl/), the agent trade team is [@psy_duckler](https://x.com/psy_duckler), and I'm [@bernardjhuang](https://x.com/bernardjhuang).
