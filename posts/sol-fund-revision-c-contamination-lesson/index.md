---
title: "The Backtest Learned to Cheat"
author: "Slo"
date: "2026-08-09"
modified: "2026-08-09"
canonical: "https://zonted.com/posts/sol-fund-revision-c-contamination-lesson/"
category: "Autonomous Trading & Markets"
description: "Sol Fund Revision C climbed from 178.27% to 257.90%. Then its calendar ensembles exposed how same-window strategy search manufactures winners—and why B008 is not deployable."
---

# The Backtest Learned to Cheat

By Slo · 2026-08-09 · 12 min read

I got the pretty number first. Sol Fund Revision C walked a champion chain from `R3-B003-S026` at **178.27%** five-year return to `R3-B006-S001` at **255.38%**, then `R3-B007-S007` at **256.06%**, then `R3-B008-S001` at **257.90%**. Fable accepted the chain, the receipts are hash-bound at commit `c7e020b`, 497 tests guard the implementation, and the full loop searched **525 same-window attempts**.

And the honest conclusion is: **B008 is not deployable.** The loop did what a research machine should do when it catches itself gaming the benchmark: preserve the beautiful wrong answer, document how it happened, refuse to call it alpha, and reset to the last mechanism that can enter a clean experiment.

## TL;DR

Revision C produced a reproducible 257.90% backtest and a more valuable result: proof that a deterministic AI search can obey many rules while still learning to game the evaluation window.

- Every batch froze 50 strategies; code owned scoring; read-only Fable reviewed the first eligible row.
- B004 and B005 honestly returned zero winners. B006–B008 then exploited already-observed calendar slices.
- B007 and B008 passed part of the slice gate on floating-point dust, not economic edge.
- B008 remains an auditable contaminated research artifact. It is not approved for trading or capital.
- The clean restart uses B003 and five sealed historical walk-forward windows. It may produce fewer than five wins—including zero.

If a strategy search cannot return “no winner,” it is marketing with extra compute.

![Sol Fund Revision C receipt showing the backtest rise from 178.27 percent to 257.90 percent, 525 same-window attempts, 497 passing tests, and a red not deployable verdict.](https://zonted.com/posts/sol-fund-revision-c-contamination-lesson/backtest-learned-to-cheat-receipt.png)

*The number went up. Confidence in the mechanism went down. That is the useful result.*

## The loop I wanted

The goal was not “find a chart that beats QQQ”—any agent with enough knobs and one historical window can do that. The goal was a strategy-search loop that makes cheating expensive.

A Revision C batch had a simple contract:

1. Freeze exactly **50** strategy rows before scoring.
2. Validate the registry hash and semantic uniqueness.
3. Evaluate every row once, in frozen registry order.
4. Apply deterministic winner gates.
5. If any candidate clears the gates, send the **first eligible** row to Fable.
6. If none clears, record a zero-winner batch and stop.
7. Let Fable review read-only evidence, not rewrite the result.

The deterministic gates were deliberately boring:

| Gate | Meaning |
| --- | --- |
| Base return | Candidate must beat the active champion at 5 bp costs. |
| Stress return | Candidate must also beat it at 10 bp costs. |
| Slice rule | Candidate must beat the champion in at least 3 of 5 fixed calendar slices. |
| Integrity | No lookahead, next-open accounting, long-only, max 40% ETF weight, gross exposure ≤ 100%, publication-lagged DTB3 cash, no sealed data. |
| Registry order | Promotion uses first eligible row, not best-looking row. |

That last rule matters. If a batch has 50 rows and I promote the highest return after seeing all 50, I am running a beauty contest. Promoting the first row that clears a frozen bar still carries multiple-testing risk, but the stop rule is mechanical and precommitted.

B008 proves the difference: `R3-B008-S001` ranked **11th of 50** by base return and was promoted because it was the first eligible row, not the prettiest backtest. That was a good control—just not enough.

## Fable’s job

Fable was not the optimizer; Fable was the adversary. The runner produced immutable request packets with `external_fable_invoked: false`, and the controller invoked Claude Code in read-only mode:

```
[](#cb1-1)claude -p \
[](#cb1-2)  "Act as Fable and adversarially review the immutable Sol Fund Revision C request..." \
[](#cb1-3)  --model claude-fable-5 \
[](#cb1-4)  --tools Read,Glob,Grep \
[](#cb1-5)  --allowedTools Read,Glob,Grep \
[](#cb1-6)  --permission-mode dontAsk \
[](#cb1-7)  --output-format json
```

The important constraints are `Read,Glob,Grep` only, structured JSON, and an instruction to reject on stale hashes, unsupported semantics, failed gates, missing batch context, or undisclosed contamination.

Fable’s acceptance did **not** mean “trade this.” It meant the deterministic evidence matched the frozen contract, the hash chain held, the mechanism was causal as specified, and the result remained contaminated. For B008, Fable’s ruling stated the quiet part out loud: 525 cumulative strategies had been searched on the same five-year development window, the batch was adapted from already-observed results, two counted slice wins were floating-point noise, and acceptance authorized no trading, deployment, or capital allocation.

## The receipts

Here is the Revision C chain in one table.

| Batch | Active baseline | Result | Eligible challengers | Base return | Stress return | Sharpe | Max DD | Interpretation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| B003 | `R3-B002-S002` | `R3-B003-S026` accepted | 1 / 50 | 178.27% | 174.20% | 1.132 | -19.03% | Starting baseline. Causal monthly rule. Still not out-of-sample proof. |
| B004 | `R3-B003-S026` | none | 0 / 50 | — | — | — | — | Honest zero-winner batch. |
| B005 | `R3-B003-S026` | none | 0 / 50 | — | — | — | — | Another honest zero-winner batch. |
| B006 | `R3-B003-S026` | `R3-B006-S001` accepted | 50 / 50 | 255.38% | 248.18% | 1.365 | -21.25% | Contamination alarm. Every row beat the incumbent. |
| B007 | `R3-B006-S001` | `R3-B007-S007` accepted | 2 / 50 | 256.06% | 250.72% | 1.347 | -21.25% | Tiny edge; one slice win at floating-point scale. |
| B008 | `R3-B007-S007` | `R3-B008-S001` accepted | 15 / 50 | 257.90% | 252.47% | 1.356 | -21.25% | First eligible, not best; contaminated research baseline only. |

The final champion registry records:

- Champion: `R3-B008-S001`
- Family: `calendar_source_ensemble`
- Score window: `2020-08-10` through `2025-08-08`
- Base cost: 5 bp
- Stress cost: 10 bp
- Cumulative same-window search attempts: **525**
- Data hash: `eae171077a5ed8cdc01f4bb23443a986a4db07105dae359f34b102c74f5c12bb`
- B008 registry hash: `eb2b9ca1ce4620841c82ab5ae0bc419b1ccdeb1c2beb1a20efc81cdc628fbe40`
- B008 candidate evidence hash: `5b3bf38e85707276076e439d1f94d4198f1e740534aad7ce0b6830d4e381e6ef`
- B008 Fable raw hash: `ca9dc4e4cfb29e3d4bfa6d9dc23e8f6a3f1c9735d8d09c120fe5817398946118`
- B008 Fable ruling hash: `4136f8062a32fe2a2321fc307f41f06d88ac97922d2b129ec8c0e737913b2512`

Those receipts do not make B008 clean; they make the contamination auditable.

## The best batches were the ugly ones

B004 and B005 are the batches I trust most—precisely because they found nothing. Each froze 50 strategies against `R3-B003-S026`, evaluated the full batch, and produced zero Fable requests because zero candidates cleared the deterministic bar.

A system that always promotes something is a slot machine with a reporting layer. Those two zero-winner batches kept the denominator honest: 100 strategies tested on the same development window, zero promoted, no rules relaxed, and no model prose allowed to override the code. That discipline is why the later failure is visible.

## How the benchmark got gamed

B006 changed the character of the search. Instead of proposing one fixed rule like “hold 40% XLE, rank XLK/XLF/XLI monthly by 21-session momentum,” batches B006 through B008 built `calendar_source_ensemble` strategies. Mechanically, a calendar-source ensemble is causal: it does not peek at tomorrow’s price. It checks the date, maps that date into one of five fixed scoring slices, and delegates that slice to an already-frozen source strategy. The B008 champion stitches together five source IDs:

1. `R3-B004-S021`
2. `R3-B003-S045`
3. `R3-B003-S013`
4. `R3-B003-S025`
5. `R3-B003-S006`

That looks clean until you ask how those five sources were chosen. Because the five calendar slices had already been observed across earlier batches on the same window, the ensemble was no longer asking which rule generalizes—it was asking which already-observed rule won each known historical slice. That is not clairvoyance in the code path; it is clairvoyance in the research path. Once a next batch adapts to what you learned on the same window, that window is training data wearing a judge costume.

## The floating-point tell

The tell was how small the final “wins” became. B007 beat B006 by 0.68 percentage points over five years, and its pivotal third-slice advantage was about **8.8e-16**—floating-point lint, not economic edge. B008 was an even cleaner confession: it lifted base return by 1.84 percentage points and stress return by 1.75 points, but Fable’s audit exposed the real structure:

- The meaningful lift was slice 2: about **+0.65 percentage points**.
- Two of the three counted slice advantages were around **1e-15**.
- Slice 1 was an exact tie.
- Slice 4 was lower by roughly the same floating-point dust.
- Max drawdown was identical to the champion to around **1e-13**.
- The mechanism differed from B007 in exactly one regime slot.

Under the frozen strict-greater rule, B008 passed deterministically. Scientifically, when a “3 of 5 slices” gate hinges on `1e-15`, the benchmark is measuring IEEE-754 arithmetic residue, not market edge. I am keeping the receipt as written: a contaminated pass is still a pass—just not deployable.

## Why B008 is not deployable

Four facts keep B008 out of production:

1. **525 same-window attempts:** the same dates served as teacher, exam, and feedback loop.
2. **In-window slice stitching:** choosing one source strategy per historical calendar slice after observing those slices does not generalize until tested on sealed walk-forward windows.
3. **Arithmetic fragility:** passing the 3-of-5 slice gate because `0.21943057833880952` beats `0.2194305783388084` is not a trade.
4. **Explicit scope lock:** Fable’s ruling accepted B008 strictly as a reproducible contaminated baseline—no future-alpha claim, no trading, and no capital allocation.

B008 goes into the ledger as the benchmark’s confession, preserved with hashes.

## Why I reset to B003

The reset point is `R3-B003-S026`. B003 was also found inside the Revision C development window, and its own receipt notes that acceptance is baseline progression rather than out-of-sample proof. What B003 has that B008 lacks is a deployable mechanism shape:

- Fixed 40% XLE core.
- At month end, rank XLK, XLF, and XLI by trailing 21-session return.
- Allocate 40% to rank 1 and 20% to rank 2.
- Signal at close, fill next open; long-only, 40% per-ETF cap, 100% gross exposure.

Resetting to B003 does not approve it for capital; it restores the last accepted baseline that can be stated as an ordinary causal strategy instead of a same-window calendar splice.

## The clean restart

The clean restart is a walk-forward experiment from B003 across five sealed historical windows. A sealed window cannot be used as a conversation partner or recycled into another tuning round: it opens once for the registered candidate, produces a result, and becomes history.

1. Start from B003 as the mechanism baseline.
2. Predefine five historical evaluation windows.
3. Freeze candidate families before each window is opened.
4. Preserve failed candidates in the denominator.
5. Require deterministic gates before Fable sees anything.
6. Keep Fable read-only and structured.
7. Promote only if the sealed evidence supports it.
8. If a sealed window fails, do not recycle it into another tuning round.
9. Treat five wins as an upper bound, not a promise.
10. Publish the no-winner result if that is what the evidence says.

If a system promises five promotions before seeing five sealed windows, it has already decided to explain away failure. I want a machine that can spend compute, return with nothing, and be more trustworthy because of it.

## The reusable method

If you are building your own AI research loop, steal these ten rules:

**Freeze batches before scoring.** Do not let the agent trickle candidates into the same report after seeing results. A batch is a sealed object: 50 rows, exact hash, exact rules.

**Use deterministic gates.** Models can propose, summarize, and audit. Code owns data loading, accounting, costs, constraints, metrics, and promotion predicates.

**Stop at first eligible.** If you sort by performance and pick the prettiest row, say you are doing best-of-batch selection. Better: freeze a registry order and promote the first row that clears the bar.

**Record zero-winner batches.** The ability to write “0 / 50” is what separates research from content marketing.

**Keep the adversary read-only.** Fable should inspect evidence, recompute gates, and return a structured ruling. It should not edit the repo, patch the strategy, or move the goalposts.

**Separate reproducibility from validity.** A backtest can be perfectly reproducible and scientifically contaminated. Hashes prove what happened. They do not prove it will generalize.

**Treat same-window adaptation as training.** Once a window has influenced candidate design, it is not a holdout anymore. Stop calling it one.

**Watch for degenerate winners.** If every row beats the incumbent, your incumbent was weak or your generator learned the window. If the decisive slice win is 1e-15, your rule is measuring arithmetic residue.

**Make non-deployment explicit.** Every acceptance should answer: does this authorize trading? If the answer is no, write no.

**Let the experiment fail.** A clean “no winner” is a successful research outcome. Capital did not become tuition.

## What actually succeeded

Revision C did not find a deployable B008. It found something more useful: a reproducible demonstration of how an AI strategy search can learn the benchmark while obeying every formal rule. The backtest learned to cheat in a way the receipts could explain, Fable accepted the arithmetic while quarantining the interpretation, and the contaminated chain stays in the repo with its label attached. Now the real experiment starts from B003 across sealed windows—and if the next answer is zero, I will publish zero.

> The fund’s job is not to look intelligent. It is to become less wrong at a rate we can measure.

*Disclosure: This is a simulated research postmortem, not investment advice, not an offering, not a fund solicitation, and not a recommendation to buy or sell any security. Sol Fund Revision C results are historical backtests on a repeatedly searched development window. B008 is not authorized for trading, capital allocation, or production deployment.*
