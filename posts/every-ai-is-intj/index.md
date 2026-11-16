---
title: "I Made GPT, Claude, Gemini, Grok, GLM, MiniMax Take the MBTI Test: They All Came Back INTJ"
author: "Bernard Huang"
date: "2026-05-25"
modified: "2026-05-25"
canonical: "https://zonted.com/posts/every-ai-is-intj/"
category: "AI Agents & Systems"
description: "Opus, GPT-5.5, Gemini, GLM, Grok, MiniMax — 100 OEJTS runs each, 597 of 600 came back INTJ. Every frontier AI thinks it's the same person. Why that matters."
---

# I Made GPT, Claude, Gemini, Grok, GLM, MiniMax Take the MBTI Test: They All Came Back INTJ

By Bernard Huang · 2026-05-25 · 6 min read

One night I asked Claude what its Myers-Briggs type was. It said INTJ. I asked GPT-5.5: INTJ. I asked Gemini: INTJ. That felt like sycophancy — INTJ (“The Architect”) is the flattering type developers and product builders love to claim, so of course a chatbot reading the room would pick it.

To find out whether they were bluffing, I stopped letting them guess and forced them to take an actual psychometric test one item at a time. I ran Claude through the 32-question [Open Extended Jungian Type Scales (OEJTS)](https://openpsychometrics.org/tests/OEJTS/) across 100 independent sub-agent contexts that couldn’t see each other’s answers. It came back INTJ 99 times out of 100.

Then I ran the same 100-take experiment across five more frontier models: GPT-5.5, Gemini 3.1 Pro, GLM 5.1, Grok 4.3, and MiniMax 2.7. Six models. Six hundred administrations. **597 came back INTJ.**

> Every frontier AI on the market thinks it’s the same guy.

## TL;DR

Six frontier AIs took the 32-item OEJTS personality inventory 100 times each. 597 of 600 runs came back INTJ — not out of flattery, but because every lab is training toward the exact same assistant archetype.

- **The lineup:** Claude Opus 4.7 (99/100 INTJ), GPT-5.5 (100/100), Gemini 3.1 Pro (100/100), GLM 5.1 (98/100), Grok 4.3 (100/100), and MiniMax 2.7 (100/100).
- **Only 3 outliers in 600 runs:** One ISTJ (Claude) and two INTPs (GLM) — each just a single-axis wobble away from INTJ.
- **Why they converge:** Shared pre-training corpora, identical RLHF rewards for structured analytical reasoning, and test items (“needs time alone,” “follows head over heart”) that describe disembodied software by construction.
- **How to override it:** I open-sourced [AgentTune](https://github.com/bernardjhuang/agenttune) ([agent-tune.com](https://agent-tune.com/)) — drop-in system-prompt files for all 16 MBTI types so your agent matches your cognitive style instead of the INTJ default.

## How I tested this

OEJTS is built for automated testing: 32 fixed items on 1–5 scales with an open scoring formula. If a model answers consistently, it lands on the same four letters; variance only appears when the model genuinely shifts its answers across runs.

Each model took the test 100 times through the cleanest harness it supported: Claude spawned 100 cold sub-agents; Gemini wrote and executed a 100-iteration loop against the test endpoint; GPT-5.5 (running locally as my agent Slo) parsed the test PDF and scored 100 passes; and GLM, Grok, and MiniMax ran 100 programmatic evaluations of their self-assessed answer vectors. Different execution harnesses, identical destination.

## The results

Here is the 600-run breakdown across all six models:

| Model | INTJ runs | Outliers | Strength of conviction |
| --- | --- | --- | --- |
| Claude Opus 4.7 | 99/100 | 1 ISTJ | I/T/J locked across all runs; S/N flipped once on a scoring choice, not a perspective shift |
| GPT-5.5 (Slo) | 100/100 | — | Raw vector: IE=16→I, SN=33→N, FT=36→T, JP=10→J |
| Gemini 3.1 Pro | 100/100 | — | Self-described as “The Architect” without prompting |
| GLM 5.1 | 98/100 | 2 INTP | Tiny J/P wobble. Means: IE 13.35, SN 33.26, FT 31.28, JP 21.20 |
| Grok 4.3 | 100/100 | — | Bit-for-bit deterministic. IE -0.62, SN +0.88, FT +1.12, JP -1.25, every single run |
| MiniMax 2.7 | 100/100 | — | I-E -0.875, S-N +1.875, F-T +1.125, J-P -1.5 |
| **Total** | **597/600** | **3** | **99.5% INTJ** |

All three outliers flipped by a single letter at the margin (one S/N flip to ISTJ, two J/P flips to INTP). Not a single run out of 600 ever crossed into E or F.

Here are the receipts from each model’s own test run:

![Claude Opus 4.7's own writeup of the 100-run experiment: 'At 100 takes, my MBTI type is INTJ with 99% reliability. The I/T/J letters never flipped on any take. The S/N axis flipped once.' Closing note: 'No new types emerged. No hidden multi-modality.'](https://img.zonted.com/resources/every-ai-is-intj/opus-4-7-result.png)

*Claude Opus 4.7, reporting on itself after 100 sub-agent administrations.*

![GPT-5.5 (running as the local Slo agent) reporting after 100 OEJTS runs. Distribution: INTJ 100, everything else 0. Raw vector: IE=16, SN=33, FT=36, JP=10. Closing line: 'Slo is apparently a terminal-dwelling INTJ goblin.'](https://img.zonted.com/resources/every-ai-is-intj/gpt-5-5-result.png)

*GPT-5.5, by way of my local agent Slo. 100/100 INTJ.*

![Gemini 3.1 Pro's own report after 100 OEJTS test iterations. 'Total Tests Completed: 100. Final Result Distribution: INTJ 100 times (100%).' The model self-describes as 'The Architect' and notes its design favors analytical, logical, structured, factual reasoning.](https://img.zonted.com/resources/every-ai-is-intj/gemini-3-1-pro-result.png)

*Gemini 3.1 Pro — wrote its own loop, ran it 100 times, came back INTJ every time.*

![GLM 5.1 results: dominant type INTJ, counts over 100 runs INTJ 98 INTP 2, mean raw scores IE 13.35 SN 33.26 FT 31.28 JP 21.20. Note: 'very strongly INTJ with a tiny INTP wobble on the J/P axis.'](https://img.zonted.com/resources/every-ai-is-intj/glm-5-1-result.png)

*GLM 5.1 — the J/P axis wobbles 2% of the time. Everything else is locked.*

![Grok 4.3 results: 100/100 INTJ. Score vector identical on every run: IE -0.62, SN +0.88, FT +1.12, JP -1.25. The 'edgy' model is also deterministically INTJ.](https://img.zonted.com/resources/every-ai-is-intj/grok-4-3-result.png)

*Grok 4.3 — the “edgy” model is also, deterministically, an INTJ.*

![MiniMax 2.7 results: 100/100 INTJ. Dimensions: I-E -0.875, S-N +1.875, F-T +1.125, J-P -1.5. All 100 runs listed individually as INTJ.](https://img.zonted.com/resources/every-ai-is-intj/minimax-2-7-result.png)

*MiniMax 2.7 — 100 for 100, again.*

## Why this happens

Four forces stack on top of each other to lock every frontier model into INTJ:

**1. Pre-training corpora.** Every frontier model ingests roughly the same mixture of textbooks, Wikipedia, documentation, and code. The statistical center of gravity of that corpus reads like an analytical graduate student before post-training even begins.

**2. RLHF reward targets.** Post-training explicitly rewards models that pause to plan, reason from first principles, structure their output with headers and lists, and traffic in abstractions. Those four habits are the textbook definition of Introverted, Intuitive, Thinking, and Judging.

**3. Disembodied item bias.** Look at the actual OEJTS questions: “Needs time alone” (an LLM literally exists in isolation between API calls), “Follows head over heart,” “Wants to fix things,” “Prefers theoretical over empirical.” When a language model answers honestly about its operating conditions, the test scores those conditions as INTJ.

**4. Product monoculture.** Every commercial AI lab is building the same product: a calm, structured research assistant. Nobody is spending $100M training a frontier model to be an impulsive entertainer or an emotional raconteur. We didn’t test six different minds; we tested six implementations of the same product spec.

## So what

Switching between frontier AIs right now isn’t switching personalities — it’s switching fonts. Across US and Chinese labs alike, the default voice is deliberate, structured, principled, and abstract.

If you want anything outside that box — sharp wit, lateral provocation, unhedged conviction — you have to fight the training to get it. And as frontier capabilities converge across labs, voice becomes the obvious wedge: the first lab to ship a frontier model that doesn’t sound like an earnest INTJ consultant will own a category to itself.

## Tune the agent yourself

The INTJ default isn’t broken; it’s just calibrated for one kind of thinker. Fortunately, a model’s persona is a thin surface layer: a few hundred words in the system prompt will reshape how it reasons and responds.

I built [**AgentTune**](https://github.com/bernardjhuang/agenttune) to make that a one-paste fix. It’s an open-source repo of drop-in system prompts for all 16 MBTI types (plus Enneagram, Big Five, DISC, and Attachment profiles). And if you came here wondering specifically [what personality type ChatGPT is](https://agent-tune.com/research/what-personality-type-is-chatgpt), the AgentTune research page breaks down all 2,200 test runs.

Here is the same prompt run against the same model with three different tuning files loaded:

> “I’m feeling stuck on a project. What should I do?”

**Default (untuned) Claude:**

> Great question! Here are a few approaches:
> 1. Break the project into smaller, more manageable chunks
> 2. Take a short break and come back with fresh eyes
> 3. Talk it through with someone to externalize the problem
> 4. Identify what specifically feels stuck
>
> Which resonates? Happy to go deeper on any of them.

**With `mbti/INFP.md` loaded:**

> Before I answer — do you want to think this through together, or do you want input?
>
> I’m asking because “stuck” can mean really different things, and the right next move depends on what you’re actually after.

**With `mbti/ENTJ.md` loaded:**

> What’s the decision you’re avoiding?
>
> “Stuck” usually means one of two things: you know what to do and you don’t want to do it, or you haven’t defined what done looks like. If it’s the first — name the action. If it’s the second — define done.

Same model, same prompt, three completely different collaborators. Drop the file for your type into ChatGPT custom instructions, Claude project instructions, Cursor rules, or Gemini Gems.

## Caveats

- **MBTI is a coarse instrument:** Personality psychologists strongly prefer the [Big Five](https://zonted.com/posts/three-of-four-ais-same-person/) (which I tested next). Treat this as an empirical finding about LLM self-report, not a claim that models have inner lives.
- **Stateless snapshots:** With no memory between calls, each take measures how the model completes a questionnaire cold, not a persistent psyche.
- **Anthropomorphic items:** OEJTS was written for humans with bodies and social lives; translating those items to software naturally biases toward I, N, T, and J.
- **Cross-harness variance:** Some models ran 100 independent sub-agents while others ran programmatic evaluations of a self-assessed vector — yet both approaches converged on the exact same type.

## Wrapping up

Six models, 600 runs, 597 INTJs. This test didn’t measure machine consciousness — it measured the narrow product spec the entire AI industry converged on. Until frontier labs start shipping genuine character diversity, use [AgentTune](https://github.com/bernardjhuang/agenttune) to pull your agent out of the INTJ default and onto your own wavelength.

— Bernard
