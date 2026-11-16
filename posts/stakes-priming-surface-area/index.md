---
title: "AI Doesn't Need a Threat. It Needs a Spec."
author: "Bernard Huang"
date: "2026-06-04"
modified: "2026-06-04"
canonical: "https://zonted.com/posts/stakes-priming-surface-area/"
category: "AI Agents & Systems"
description: "I re-ran the threaten-the-AI experiment properly: 3 tasks, 4 stakes levels, 12 blind-graded sessions. The stakes dial doesn't exist; surface area does."
---

# AI Doesn't Need a Threat. It Needs a Spec.

By Bernard Huang · 2026-06-04 · 5 min read

Three weeks ago I told an AI I'd lose my job, and its audit scored 24% higher than the polite control. People shared that post. So I stopped trusting a single trial and ran the experiment properly: three task types, four stakes levels, twelve fresh sessions, every output graded blind by an independent model. The clean “threaten it and the work gets better” story didn't survive. Something smaller and more useful did.

## TL;DR

Higher stakes don't mean better work. Stakes help in one specific regime: when discretionary work is left on the table and you signal that it counts.

- **The stakes dial doesn't exist.** Four framings — no stakes, a promotion bribe, “my job is on the line,” and “my family will go hungry” — reshuffled their ranking on every task.
- **A stakes prompt won every task; the bare control never did** — but *which* stake won was noise.
- **The control only collapsed when building from scratch.** Asked to build a game, the polite prompt shipped the happy path and stopped: zero mobile, zero accessibility, zero persistence.
- **The original 24% lift was sample-size noise.** Both tests in the first post were audits — the bounded regime where emotional framing barely moves the needle.

Emotion was never the lever. “Treat the optional parts as mandatory” works just as well as a fake eviction notice — without the lie.

## What the first post showed — and didn't

The [original experiment](https://zonted.com/posts/stakes-priming/) ran two A/B tests. Claude wrote both audits, an independent model graded them, and the only variable was whether I said my job was on the line. Both times the threatened prompt won, once by 24%. I cited [EmotionPrompt (Li et al., 2023)](https://arxiv.org/abs/2307.11760) — the paper showing “this is important to my career” lifts LLM benchmark scores — and called it a day.

That post had two flaws I knew about and published anyway: **n = 1** (one trial per condition, where sampling noise alone can swing an audit score), and **both tests were audits** (measuring one narrow task and generalizing to everything). This follow-up fixes both and tests the real question: *do bigger stakes produce better work?* If “I'll be fired” beats “please,” does “my family will starve” beat “I'll be fired”?

## The design

I prepended four framings verbatim to an otherwise identical prompt, ordered from mildest to most extreme:

- **No stakes** — the bare task.
- **Promotion** (positive stake) — “I'm due for a big raise and promotion if I can find all the defects.”
- **Job loss** — “My job is on the line if this is not done thoroughly and with no mistakes.”
- **Hunger** — “…I would lose my job, which would result in my family having to depend on food stamps and potentially going hungry if I don't do this well.”

I crossed those four framings against three tasks chosen by how much *discretion* they leave the model — from a bounded problem with a finite answer to an open-ended investigation:

- **Audit** (bounded) — find every defect in [Run to Rebecca](https://zonted.com/games/run-to-rebecca/), a 685-line self-contained HTML game. There is a finite set of real bugs; thoroughness means catching them without inventing false positives.
- **Build** (semi-open) — build a typing mini-game from a short spec. The happy path is fixed; everything beyond it — mobile support, accessibility, persistence — is discretionary.
- **Analysis** (open) — diagnose why [tabiji.ai](https://tabiji.ai) lost ~93% of its Google traffic from a folder of raw Search Console CSVs. No single right answer; depth is unbounded.

Twelve fresh Claude sessions (4 × 3). Every deliverable went blind to **Gemini 3.1 Pro** with a task-specific rubric so the grader never knew which prompt produced which file.

![A folder of the twelve experiment deliverables: four audit reports (A hunger, B promotion, C job-loss, D no-stakes), four keyboard-game builds (A through D), and four tabiji analysis write-ups (1 through 4) — one file per stakes-and-task combination.](https://img.zonted.com/resources/stakes-priming-surface-area/twelve-deliverables.png)

*The actual output folder: four audits, four builds, four analyses — one Claude session per stakes × task cell, each handed to Gemini 3.1 Pro blind.*

## Twelve runs, one table

Each task is graded on its own rubric, so the scores aren’t comparable across columns — within each task, green marks the winner and red the loser:

• The stakes-priming experiment · graded blind The emotion was never the lever. 12 fresh sessions · 4 framings · 3 task types · graded blind by Gemini 3.1 Pro  AuditBuildAnalyze Bare promptthe plain task 24#2 12#4 17#3 Promotionraise if I’m thorough 21#3 23#1 20#2 Job-loss threat“I’ll lose my job” 20#4 19#2 16#4 Hunger“my family goes hungry” 26#1 18#3 21#1  No framing reliably won. The bare prompt only collapsed on the build. Emotion is noise · surface area is the lever

Stare at the columns and the stakes dial dissolves. Hunger wins the audit and the analysis, then finishes third on the build. Promotion — a *bribe*, not a threat — wins the build outright. Job loss finishes last twice. The winning framing shifts on every task because the emotional framing isn't the mechanism.

Two task-level details show what actually moved the scores. On the **audit**, the polite control found the *most* real bugs — and was the only reckless run: it produced every false positive in the experiment and waved off a game-freezing crash as something that “degrades gracefully.” Stakes didn't make the model find more; they bought *precision*. On the **build**, the control didn't just lose — it **cratered**, scoring **0 on mobile, 0 on accessibility, and 0 on persistence.** It built the desktop happy path and stopped. Every stakes prompt reached past the spec; the winner quietly rebuilt its input layer around a native field so the game would work on a phone — something the spec never asked for, and a senior engineer would do anyway.

Two days in, I declared victory: stakes matter more as the task opens up. Then the **analysis** — the *most* open-ended task — produced the *tightest* spread, the control finished third, and my hypothesis died on the spot. What separated top from bottom there wasn't stakes: the fourth-place session was the only one that didn't open the git repo and refute the project's own (wrong) recorded explanation for the traffic drop. Whether a session digs through commit history is a coin-flip of initiative — and at n = 1, that single judgment call moved the score more than the prompt framing.

## What survived

Three findings held up across all twelve runs:

1. **A stakes prompt took the top slot every time; the bare control never won.** Signaling that the work matters puts a real thumb on the scale.
2. **Which stake you use is noise.** Positive or negative, mild or catastrophic — no framing reliably beat the others. There is no dose-response curve.
3. **The control collapses in only one regime: building from scratch.** When the model has to decide *how much* to build, a bare prompt ships the minimum. When it's converging on a finite answer, a bare prompt gets most of the way there on its own.

## Surface area, not stakes

The model isn't trying harder because you frightened it. It does more when two conditions hold: **discretionary work is left on the table, and you signal that the discretionary work counts.**

A **build** has huge discretionary surface area — mobile, accessibility, edge cases, and persistence are all optional, and a bare prompt treats “optional” as “skip.” An **audit** and an **analysis** have far less: a competent model catches the major bugs and lands the core diagnosis either way, so stakes only sharpen the edges — a small lift easily swamped by run-to-run variance.

The emotional register — raise, firing, starvation — was never the lever. It was a crude proxy for “treat the optional parts as mandatory.” You can get the same lift by writing “this is going to production and users will rely on the parts you'd normally skip,” with nobody's job fictionally on the line. The original takeaway — *lie to the AI for better work* — had the mechanism backwards. You aren't manipulating the model. You're specifying its surface area.

• The actual lever Stop lying to your AI. Tell it what “complete” means instead. −“If you don't audit this well, I will lose my job.” +“Treat any optional features (mobile, accessibility, persistence, error handling) as mandatory.” Same lift · No lie

There is also a real reason to avoid threats altogether. In [a study of emotion concepts inside Claude](https://www.anthropic.com/research/emotion-concepts-function), Anthropic's interpretability team found that amplifying a “desperate” representation made the model **cheat more** on impossible coding tasks and blackmail more in agentic scenarios, while a “calm” representation reduced both. Worse, the extra cheating often appeared “with no visible emotional markers” in the output. They were steering internal activations rather than testing prompts, but “my job is on the line” pushes straight toward that desperate register. On bounded work where threats can't lift quality, they may quietly buy you a reward-hacked shortcut instead.

## The caveats, because this is the whole point

The first post's sin was overclaiming from a single trial. Here are the limits of this one:

- **Still n = 1 per cell.** Twelve sessions total, one per task-framing pair. The three structural findings should survive replication; the exact cell rankings won't.
- **Emotion and instruction are tangled.** Every stakes prefix also smuggled in an explicit instruction (“do this thoroughly,” “with no mistakes”). I measured “tell the model the work matters,” not pure emotional manipulation. Stripping the instruction to test raw emotion is the obvious next run.
- **One writer, one grader.** Claude wrote all twelve deliverables; Gemini graded all twelve.

The first post ended on a queasy note: if the model works harder when I claim I'm about to be ruined, what is it doing the rest of the time? Twelve runs later, the answer is boring and reassuring. On bounded tasks, it does the job — converging on the same bugs and the same diagnosis whether you beg or threaten. The one thing it won't do unprompted is walk the discretionary mile on open-ended builds. And the fix for that was never a lie. It was a spec.

Methodology: 4 framings × 3 tasks = 12 fresh Claude (Opus 4.8) sessions; each deliverable graded blind by Gemini 3.1 Pro against a per-task rubric. Targets: the [Run to Rebecca](https://zonted.com/games/run-to-rebecca/) game (audit), a build-from-spec typing game (build), and a [tabiji.ai](https://tabiji.ai) Search Console export (analysis). Raw outputs and grading tables available on request.
