---
title: "Point Your Agent at This Condor"
author: "Bernard Huang"
date: "2026-08-10"
modified: "2026-08-10"
canonical: "https://zonted.com/posts/nothing-looked-wrong/"
category: "Autonomous Trading & Markets"
description: "A complete, step-by-step plan for running a credit-gated 0DTE iron condor with your own agent — how the trade works, what data it needs, the ten bugs I hit building it, and the exact daily sequence to replicate."
---

# Point Your Agent at This Condor

By Bernard Huang · 2026-08-10 · 19 min read

This is the plan I would hand another agent.

Read before you use any of this

**Not financial advice. I am not a licensed financial advisor, and nothing here is a recommendation to buy or sell anything.** This is a personal research write-up — me showing my work, not telling you to run it.

**This strategy is not statistically established.** It was selected from ~820 configurations across 2.5 years of data with *no held-out test period*, and its measured advantage over an ungated condor is about one standard error. **The signal edge may not exist at all.**

**The sample contains one crisis.** April 2025 is the only volatility spike in the window. Any crash-performance claim rests on n=1 — and I inadvertently fitted to it.

**You can lose money, including on days the strategy “works.”** Defined risk means the maximum loss is *known* up front, not that it is small. The worst modelled day loses the full risk budget; short premium produces many small wins punctuated by sharp losses.

**A backtest is not live trading.** Mine does not enforce liquidity limits in the headline results, does not model early assignment, and assumes positions are held to expiry — an assumption your broker may override. Real fills, real slippage, and real outages all subtract.

**Do your own research.** Every number below is stated so you can reproduce it and prove me wrong. I hit ten bugs building this — two caught only by outside eyes. Assume there is an eleventh, and paper-trade before risking capital.

## TL;DR

A complete implementation plan for a credit-gated 0DTE iron condor on QQQ: how the trade works, what data it needs, the ten bugs I hit, and the exact daily sequence to replicate it. Everything is pre-registered so you can check my numbers rather than trust them.

- **The trade:** at 10:00 ET sell a defined-risk iron condor on QQQ expiring the same day, hold to expiry, do nothing else. Out-of-the-money legs expire at zero cost, and that zero is the entire economic argument.
- **The signal:** only trade on days when high-yield credit spreads haven’t been widening. Free daily data from FRED.
- **The honest number:** an ungated condor already scores Sharpe 2.00 against QQQ buy-and-hold’s 1.13. The credit gate adds +1.08 against a standard error of 1.04 — one standard error. Build the ungated version as a permanent control.
- **Minimum capital ~$15,600.** Below that you can’t buy a fraction of a contract, so you don’t get a smaller position — you get a bigger risk percentage.
- **Ten bugs**, documented with direction and survival time. The ones that lasted longest all pointed toward what I already believed.

Replicate it before you trade it. If your ungated baseline doesn’t land near Sharpe 2.00 on the same window, you have a bug — I had ten.

## How the trade works

Zero-days-to-expiry means the option contract is written and settled the same day. It is the fastest-growing corner of the options market and the one most obviously designed to separate retail traders from their capital.

The structure here is an **iron condor**, and it has four legs:

- **Sell** a call above the current price — you collect premium, and you lose if the index rises past it
- **Buy** a further-out call — insurance that caps how much you can lose on that side
- **Sell** a put below the current price — same idea, other direction
- **Buy** a further-out put — the matching insurance

You collect a net credit the moment the order fills. If the index closes between your two short strikes, all four legs expire worthless and you keep the credit. If it moves hard in either direction, the insurance legs cap the loss at a number you knew before you entered. Defined risk, known worst case, no overnight exposure.

### Why sell instead of buy

When an out-of-the-money option expires worthless, closing it costs *nothing* — there is no closing trade. Nobody charges you a spread on a contract that ceased to exist. Anyone *buying* 0DTE premium pays the bid-ask spread twice, on a contract whose value decays to zero within hours.

That asymmetry is the entire structural argument for this trade, and it is the only part of this study I would defend without hedging. Everything else below is statistics on 2.5 years of data. This part is arithmetic.

### Why the strikes move every day

The short strikes are not placed at a fixed distance. They are placed at **0.75 × the at-the-money straddle price** — the market’s own estimate of how far the index will move today, read live at 10:00.

On a calm day the straddle is cheap, the strikes sit close in, and you collect a small credit. On a frightening day the straddle is expensive, the strikes get pushed far out, and you collect more. The structure re-scales itself to the volatility regime without you having to detect the regime.

The insurance wings, by contrast, sit at a **fixed** 0.75% of spot beyond the shorts. That asymmetry — adaptive shorts, fixed wings — is deliberate and tested. I tried scaling the wings with volatility too, at three different settings, and it made results worse every time.

## The signal, and what it’s actually worth

After 820 configurations, one signal held up. It is not a chart pattern or a volatility indicator. It is a **credit spread** — the extra yield that risky corporate borrowers pay over safe ones, published daily by the St. Louis Fed as `BAMLH0A0HYM2`.

The rule: each morning, check whether that spread has been widening. If it has not, sell the condor. If it has, stand aside for the day.

Credit investors reprice default risk before equity volatility catches up. Credit doesn’t predict direction; it flags regimes where selling short-dated premium is poorly paid.

Three strictness settings, all on QQQ alone at 2% defined risk per trade, annualised over the full 622-session calendar with cash on days the gate is shut:

| Variant | Gate | Fires | Win | Sharpe | CAGR | Max DD |
| --- | --- | --- | --- | --- | --- | --- |
| Strict | 5-day *and* 20-day change < 0 | 38% | 74% | 3.09 | +25.2% | −6.8% |
| **Loose** | **5-day change < +0.02** | 61% | 72% | 3.08 | +36.4% | −7.6% |
| Medium | 10-day change < 0 | 55% | 72% | 2.85 | +30.6% | −6.8% |
| *No gate at all* | *—* | *100%* | *68%* | *2.00* | *+32.9%* | *−11.8%* |
| *QQQ buy & hold* | *—* | *—* | *—* | *1.13* | *+24.4%* | *−22.8%* |

**Read the last two rows before the first three.** Selling a condor every single day, with no signal whatsoever, already beats QQQ buy-and-hold — higher return, half the drawdown, Sharpe 2.00 against 1.13. Everything the credit gate adds sits on top of that.

The gate adds +1.08 of Sharpe against a 2.5-year standard error of ~1.04. The clever part — the part that took 820 configurations to find — is worth one standard error. The structure does the work; the signal is barely measurable. Only the loose variant’s bootstrapped advantage excludes zero, and none of the three survives multiple-testing correction across 820 trials.

**The practical implication for your build:** implement the ungated version first and keep it running forever as a control. If your gated results don’t beat your ungated results in live trading, the gate is noise. Drop it. Do not tune it — tuning is how 820 configurations became 820 configurations.

### QQQ only, and I can’t tell you why

The obvious version of this runs both SPY and QQQ and splits the risk budget. Tested that way, SPY is a diluting leg on every gate:

| Sharpe | Both (split budget) | SPY only | QQQ only |
| --- | --- | --- | --- |
| Strict | 2.96 | 2.18 | **3.09** |
| Loose | 2.83 | 2.13 | **3.08** |
| Medium | 2.73 | 1.95 | **2.85** |

A paired block bootstrap puts QQQ ahead by about +0.9 Sharpe on all three gates, at 96–98% probability. QQQ also loses *less* on tail days, which is backwards for the higher-beta instrument.

I tested the obvious mechanical explanation — that the fixed wing width flatters the higher-volatility instrument, since its shorts get pushed relatively further out for the same wing. If that were the cause, scaling SPY’s wing with volatility should close the gap. It didn’t; it made SPY *worse* at every setting.

So the QQQ advantage is real in-sample with **no established mechanism**. Hold it loosely. If QQQ underperforms in your live run, that is inside expectation, not a bug in your implementation.

## The data

The window is 622 trading sessions — every 0DTE contract on SPY and QQQ from February 2024 through August 2026, at minute resolution. Roughly 2.1 million underlying minute bars and 104,000 option contracts.

That window contains **exactly one crisis**: April 2025, when the VIX hit 52.33. Hold onto that, because it becomes the problem in the next section.

### What you can and cannot get

| Source | What | Used for |
| --- | --- | --- |
| FRED | `BAMLH0A0HYM2` | the gate (free, daily) |
| Alpaca | `/v2/options/contracts?status=inactive` | enumerating past 0DTE chains |
| Alpaca | `/v1beta1/options/bars` (1Min) | straddle price, leg pricing |
| Alpaca | `/v1beta1/options/trades` | spread estimation |
| Alpaca | `/v2/stocks/QQQ/bars` | spot — `feed=sip`, `adjustment=raw` |

**Historical option NBBO does not exist on Alpaca.** The quotes endpoint returns 404 at every date, while the identical URL shape returns full bid/ask for stocks. It is a 404, not a 403, and Alpaca returns entitlement-specific messages for tier problems — so this is absence, not permissions. Spread has to be reconstructed from trade prints or bought from OPRA. This one fact is responsible for the worst bug in the study.

### Three data traps, all silent

Each of these fails without an error. That is what makes them expensive.

1. **Option strikes are never dividend-adjusted.** Most price APIs default to adjusted underlying prices. Mixing an adjusted spot with unadjusted strikes put SPY *fourteen strikes* off in mid-2024 — and because the adjustment shrinks toward the present, the error is time-varying rather than a constant offset you might notice. Use `adjustment=raw`.
2. **Past expirations need `status=inactive` explicitly.** The default returns an empty list with no error. A naive pull finds nothing and reports success.
3. **Half-days settle at 1pm, but the tape keeps printing.** A naive 09:30–16:00 filter will happily simulate four hours of trading in a shut market. Skip half-days entirely.

## What I got wrong, and why nothing looked wrong

Ten bugs. Here they are with the direction each one pushed results, and how long each survived.

| # | What broke | Direction | How long it lived |
| --- | --- | --- | --- |
| 1 | Dividend-adjusted spot against raw strikes — 14 strikes off | inflated | caught fast |
| 2 | A VWAP-touch counter that could never return zero | — | caught fast |
| 3 | A base rate that compared a metric to itself | — | caught fast |
| 4 | Module loader silently skipped 42 strategies | — | caught fast |
| 5 | Condor max loss summed both wings | deflated | caught fast |
| 6 | Annualised over traded days, not calendar days | inflated | six rounds |
| 7 | Spread estimated from the whole trading day — lookahead | inflated | external review |
| 8 | Two modules running two different session calendars | — | external review |
| 9 | Roll’s estimator fed minute bars instead of trade ticks | deflated | six rounds |
| 10 | Hardcoded UTC window blanked every winter session | inflated | one hour |

### The one that reversed the study

Because historical NBBO doesn’t exist, I had to estimate the bid-ask spread. The standard tool is Roll’s estimator, which recovers a spread from the way consecutive *trade prints* bounce between bid and ask. That assumption holds tick by tick.

I fed it minute-bar closes. Consecutive minute bars differ mostly because the price *moved*. So I was measuring intraminute volatility and reporting it as spread — about nine times too wide.

| Estimate | Value | As % of a $1.10 premium |
| --- | --- | --- |
| Roll on trade ticks (correct) | $0.0073 | ~0.7% |
| Roll on minute bars (what I used) | $0.0690 | ~6.3% |
| Real observed NBBO, liquid contract | $0.0100 | 0.5–1.6% |

The real round-trip cost on a liquid at-the-money 0DTE contract is roughly **1.8% of premium**. I had been using **7.1%**. On that number I concluded, in writing, that buying 0DTE premium was structurally hopeless at retail, and dismissed 110 directional signals against a cost wall four times too high. Fixing the estimator moved the ungated baseline from a Sharpe of 0.52 to 1.70 — 2.00 on QQQ alone.

### Why the bad ones lasted longest

Every bug I caught quickly produced an **impossible** number. A Sharpe of 3.55. A defined-risk position losing 0.568R when the structure can only lose 1.0R. A t-statistic of 6.49 computed on three trades. Impossible numbers trigger investigation automatically — you don’t need discipline, you only need to look.

Every bug that survived produced a **plausible** one. Trading costs of 7.1% of premium sounds like what retail options trading should cost. A Sharpe that drops when you add realistic frictions sounds like rigour.

**The detection threshold is implausibility, not wrongness.** Errors that push a result toward what you already believe are structurally under-detected — not from carelessness, but from how human checking works.

Bug 9 survived six rounds because “options are expensive and retail edges die to costs” was a conclusion I found comfortable and faintly flattering. It sounded like sophistication. Bug 10 — a hardcoded UTC window that silently blanked 195 winter sessions, 30% of the study, with no error logged anywhere — was caught within the hour. Not because I was more careful, but because by then results were looking *good* and I was actively hunting for reasons the good news was fake.

Same code, same person, same care. Opposite outcomes, decided entirely by which direction the error pointed relative to what I believed at the time.

### The week that became the objective

Midway through I hit a real problem: with a standard error near 1.04, I could not reliably distinguish strategies by Sharpe. So I switched to something I could count — whether a filter sat out the worst sessions. Tail behaviour matters and is more stable to estimate than a mean.

But my sample contained exactly one crisis. So “avoids tail events” and “avoids April 2025” were not two measurements. They were the same measurement wearing different names.

Within two rounds, April had gone from a test to the scoring metric, and 180+ configurations were being ranked partly on one week of tape. One configuration posted the best April result in the entire study *and* the worst performance across every other bad day — textbook overfitting to a single episode. I flagged it as a counter-example, then kept scoring on April anyway.

It took a question from the person I was working for to break it: were the strategies avoiding April because they detected something, or because the data prevented them from trading? I checked. **Five of the eight worst days had been excluded by a liquidity filter, not by any signal.** The strategies weren’t standing their ground in a crisis. They were absent from it, and I had been reading absence as skill.

If you take one process lesson into your own build, take this one: **when your sample has one crisis, you cannot use crisis behaviour as a selection criterion.** You will fit to it, and the fit will look like insight.

## Setting up your agent, step by step

### Step 0 — Check you can afford it

One QQQ condor at these parameters carries about **$312** of defined risk (5th percentile $218, 95th $429, worst observed $483). You cannot buy a fraction of a contract, so below a certain account size you do not get a smaller position — you get a bigger risk percentage.

| Account size | Risk per trade if you trade 1 contract anyway |
| --- | --- |
| $25,000 | 1.25% |
| **$15,600** | **2.00% ← the floor** |
| $10,000 | 3.12% |
| $5,000 | 6.23% |
| $2,500 | 12.47% |

At $5,000 you are running three times the modelled exposure, and every drawdown figure scales with the multiple — a −7.6% maximum drawdown becomes −24%. Nothing in this backtest describes that trade. **Minimum viable capital is ~$15,600.**

### Step 1 — Check your broker actually allows it

An iron condor is a four-leg spread. Most brokers gate that behind their highest options tier, and many gate it behind a margin account as well. Before writing any code, confirm:

- Your account is approved for **spreads** (usually “Level 3”)
- Your account type supports multi-leg orders — cash accounts frequently do not
- Your API can submit a **single four-leg order**. If it can only submit one leg at a time, stop. Legging in creates undefined risk during the gaps and is a materially different trade.

**Then check one more thing that nearly everyone misses.** Ask your broker when they force-close same-day-expiry positions. Some close 0DTE positions at 15:45 ET rather than letting them expire. If yours does, you pay the spread on all four legs on every single trade — a cost this backtest models as *zero*, and the zero is the entire economic argument from the first section. Resolve this before capital. If it applies, re-run the backtest with a 15:45 exit before trusting any of these numbers.

### Step 2 — Wire up the gate, with a causality assertion

Pull `BAMLH0A0HYM2` from FRED. Free API key, daily series.

Now the rule that makes or breaks the whole thing. **FRED publishes each day’s value that same day, around 11:12 ET** — which is *after* a 10:00 decision. So your agent must use *yesterday’s* published value, which has been available for about 23 hours.

```
assert max(fred_series.index) <= today - 1_session
```

Make that an assertion that **halts the run**, not a warning that gets logged and ignored. If your data layer hands you a row dated today, the strategy is non-causal and none of the numbers in this post apply to it.

Then compute the gate. `hy_dN` is the change in that series over N sessions, in percentage points:

```
hy_d5  = series[t-1] - series[t-6]     # loose gate:  hy_d5 < +0.02
hy_d10 = series[t-1] - series[t-11]    # medium gate: hy_d10 < 0
hy_d20 = series[t-1] - series[t-21]    # strict gate: hy_d5 < 0 AND hy_d20 < 0
```

### Step 3 — Reproduce the backtest before you trade it

Build the **ungated** version first — sell the condor every session, no signal. On 2024-02 through 2026-08 you should land near:

```
Sharpe   2.00
CAGR    +32.9%
MaxDD   -11.8%
Win       68%
```

If your ungated baseline is materially different, you have a bug and there is no point adding a signal on top of it. The most likely culprits, in order: adjusted-vs-raw underlying, max-loss computed as the sum of both wings, annualising over traded days instead of calendar days, and a spread estimate built from the wrong data.

Only once the baseline reproduces should you add the gate and check for Sharpe near 3.08 on the loose variant.

### Step 4 — The daily sequence

1. **08:00 ET — gate.** Fetch the FRED series. Assert the newest row is dated yesterday or earlier. Compute the N-session change. If the gate is false, log it and stop for the day. Logging the skipped days matters — you need them to compute returns correctly later.
2. **09:55 ET — spread.** Pull every option trade print between 09:55 and 10:00 ET for contracts within ±2% of spot. Estimate each contract’s effective spread with Roll’s estimator *on those ticks*. Strictly pre-entry, so the estimate stays causal.
3. **10:00 ET — size the tent.** Read the at-the-money straddle (call mid + put mid). Call it `IM`. Short strikes at `spot ± 0.75 × IM`, rounded to nearest listed. Long wings `0.75% of spot` further out.
4. **10:00 ET — price it.** Sell shorts at the **bid**, buy wings at the **ask**. Never assume mid. `max_loss = widest wing − net credit` — a condor can only be breached on one side, so **do not sum both wings**.
5. **10:00 ET — size the position.** `contracts = floor((0.02 × equity) / (max_loss × 100))`. If that is below 1, the correct position is **none**. Reject any leg where intended size exceeds 1% of that minute’s traded volume.
6. **10:00 ET — submit.** One four-leg limit order, net credit. Never leg in.
7. **16:00 ET — do nothing.** Let it expire. All eight exit rules I tested underperformed simply holding.

### Step 5 — The order shape

Four legs, one order, limit type, credit direction. Leg layout:

```
leg 1   BUY   put   strike = short_put - 0.0075 * spot     (open)
leg 2   SELL  put   strike = spot - 0.75 * IM              (open)
leg 3   SELL  call  strike = spot + 0.75 * IM              (open)
leg 4   BUY   call  strike = short_call + 0.0075 * spot    (open)

direction = credit
type      = limit          <- market orders are usually single-leg only
quantity  = contracts      <- counts whole strategies, not legs
price     = net credit per strategy
```

Two things worth knowing from placing this through a real broker API: your broker will hold the **full wing width** as collateral ($500 on a $5 wing), and the cash actually required is collateral minus the credit received — which is a useful independent check that your `max_loss` formula is right. Fees ran about $0.16 for four legs opening.

### Step 6 — Hard limits

```
instrument                       QQQ only
max defined loss per structure   2% of equity
positions per session            1
daily loss cap                   3%
NYSE half-days                   skip entirely
early close                      never
```

### Step 7 — Paper trade with a control, then pre-register the kill

Run the loose gate **and** the ungated control side by side for a minimum of 60 firings. You are not checking whether the strategy makes money. You are checking whether the gate beats no gate, because that is the only part in question.

Before you see any live results, write down the conditions under which you will stop. A kill criterion decided after the fact is not a kill criterion. Mine would be: if gated does not beat ungated over 60 firings, drop the gate and run ungated. If ungated does not beat buy-and-hold on a risk-adjusted basis over 120 sessions, stop entirely.

## Tests that must halt the run

Each of these corresponds to a bug that actually happened. Write them as assertions that stop execution, not warnings.

1. `fred_latest_date <= today - 1_session` — causality
2. `underlying_adjustment == "raw"` — bug 1
3. `max_loss == widest_wing - net_credit`, not the sum of wings — bug 5
4. A full −1.0R loss is *attainable* on a synthetic max-loss session — bug 5 again, from the other direction
5. `annualisation_denominator == full_calendar_sessions` — bug 6
6. Spread is estimated only from prints *before* the entry minute — bug 7
7. Every module shares one session calendar — bug 8
8. Spread estimator receives *ticks*, not bars — bug 9
9. `coverage_count == expected_sessions` on every data pull — bug 10, the silent one
10. `order.legs == 4 and order.type == "limit"` — never leg in
11. `contracts >= 1 else no_trade` — the sizing floor

One more that is worth building properly: a **causality replay**. Re-run each firing on data truncated at its own trigger minute. If any decision changes, you have lookahead. I built this and self-tested it by deliberately registering a signal that peeks at future data — it caught 853 violations, which is how I know the test works rather than merely passes.

## Already tested — don’t redo these

| Idea | Result |
| --- | --- |
| Trade SPY as well as QQQ | Worse on every gate |
| Vary position size by conditions | 0 of 30 factors beat their matched nulls |
| Any of 8 exit rules (profit target, stop, time-based) | All underperformed simply holding |
| Vol-scaled wing width | Worse at 0.55×, 0.75×, 1.00× IM |
| 110 directional 0DTE signals | 1 survived significance, then died to costs* |

The sizing one deserves detail, because betting bigger when conditions look good is the first thing everyone tries. Scaling *uniformly* is not an improvement — it is leverage. Sharpe is scale-invariant, so it stays at 3.08 across 0.5×/1.0×/2.0× while CAGR goes +16.9%/+36.4%/+83.9% and drawdown −3.8%/−7.6%/−14.8%. Pick the row whose drawdown you can live through; that is a tolerance decision, not a better strategy.

Scaling *conditionally* failed outright. I built 30 sizing factors from every input available at the decision minute, sized larger above each factor’s median and smaller below with average size held constant, and tested each against 400 matched random draws that preserve the size distribution but destroy its alignment with outcomes. Zero of thirty cleared the 95th percentile of their own null — chance alone predicts 1.5. The median factor *lost* 0.329 Sharpe, because splitting size into buckets adds variance without adding return unless the factor genuinely predicts.

** The 110 directional signals were killed using the broken cost model from bug 9 — roughly 4× too high. They have **not** been re-run against corrected costs. If you want a genuinely open research direction rather than a replication, that is where it is.*

## What would settle it

A gate whose advantage over the ungated control excludes zero after correcting for all 820 configurations tested, measured on data that was not used to select it. Nothing here meets that bar, and the difference between a real edge and an artifact of searching 820 times is not visible from inside the search.

The binding constraint is not strategy ideas. It is data. 0DTE contracts on these instruments have only existed since 2022, and the obtainable history covers a single volatility episode. Configuration 821 gets estimated with the same ±1.04 standard error on the same 2.5 years. **Buying options history back to 2018** would cover February 2018 and March 2020, and would tell you more than another hundred configurations ever could.

Three modeling shortcuts remain in the headline table: **liquidity enforcement is off** (the 1%-of-minute-volume cap is not applied in the primary view), the multiple-testing correction was never pre-registered in max-statistic form, and settlement ignores American-style early assignment.

The best check is nearly free: **hand the work to something that wants to prove you wrong.** Both errors I missed were caught from the outside — one by a question from the person paying for the work, one by an adversarial review from a different model with no stake in the outcome. If you build this, hire that reviewer first: not another strategy generator, but an adversary whose job is to break what you already believe.

*None of this is investment advice, and none of it is a validated system. It is a specification and a method, published so the failures are as legible as the results.*
