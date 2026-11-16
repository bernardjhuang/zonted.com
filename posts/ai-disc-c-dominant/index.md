---
title: "I Made GPT, Claude, Gemini, Grok Take the DISC Test: They All Came Back C-Dominant"
author: "Bernard Huang"
date: "2026-05-26"
modified: "2026-05-26"
canonical: "https://zonted.com/posts/ai-disc-c-dominant/"
category: "AI Agents & Systems"
description: "Fourth in the personality series: every AI lands C-dominant on DISC, even Grok. Why the instrument's resolution determines what you can see."
---

# I Made GPT, Claude, Gemini, Grok Take the DISC Test: They All Came Back C-Dominant

By Bernard Huang · 2026-05-26 · 5 min read

Across three psychometric tests, four frontier AI models have given us three different stories: [MBTI](https://zonted.com/posts/every-ai-is-intj/) scored every model as INTJ, [the Big Five](https://zonted.com/posts/three-of-four-ais-same-person/) grouped three together with Grok as the lone outlier, and [the Enneagram](https://zonted.com/posts/ai-enneagram-different-types/) split all four into distinct types. For test four, I ran the same four models through 100 administrations each of the Open DISC Assessment Test (ODAT) — 400 takes across Dominance, Influence, Steadiness, and Conscientiousness. Every single model came back C-dominant (CS-blend), including Grok.

We’re back to total convergence — except now we know why.

## TL;DR

All four frontier models collapsed into the exact same DISC profile (CS-blend) because DISC defines Dominance and Influence in ways every AI is trained to refuse.

- **Total C-dominance:** Grok scored C-dominant in 99/100 takes, GPT-5.5 in 90/100, Gemini 3.1 Pro in 87/100, and Claude Opus 4.7 in 63/100 (with 28 S-dominant and 9 ties — all inside CS-blend territory).
- **Zero D or I runs:** Across 400 total administrations, not a single take came back Dominance- or Influence-dominant.
- **Why Grok folded back in:** ODAT defines “Dominance” as power-seeking, pressuring others, and chasing money — traits even xAI’s Challenger-flavored Grok rejects on instinct.
- **Cross-method convergence:** Four different sampling architectures (100 parallel API calls, 10 worker contexts, item-level Monte Carlo, and sequential first-instinct) all landed in the same 0.3–2.0 SD calibration band.
- **Tune your agent:** Override the CS-blend default with the four DISC system-prompt files in [AgentTune](https://github.com/bernardjhuang/agenttune).

## What each model came back as

Each model landed on the same dominant profile (Conscientious with a Steady secondary), differing only in how tightly clamped its scores were across 100 takes:

Claude Opus 4.7 CS-blend Conscientious with a strong Steady secondary C-dominant in 63 takes · S-dominant in 28 · 9 ties

The softest C of the four. Warmth and analytical structure compete more evenly than they do for the others.

Gemini 3.1 Pro CS-blend Conscientious with a Steady secondary C-dominant in 87 of 100 takes

The most clamped on D and I. Closest to a pure analytical-helpful shape.

GPT-5.5 CS-blend Conscientious with a Steady secondary C-dominant in 90 takes · 10 C/S ties

The looser-floor model. Higher D and I than the others without it flipping the dominant. More “personality” on the lower dimensions.

Grok 4.3 CS-blend Conscientious with a Steady secondary C-dominant in 99 of 100 takes

The most rigid C. The model with the “edgy” reputation lands as the most uniformly analytical of the four.

Claude shows the most C-versus-S give; Grok is the most locked-in C of the group. None of the four ever crossed into D or I territory.

## The data

The chart below plots each model’s mean score across 100 takes (±1 SD error bars). Each dimension runs from 4 to 20 (the sum of four 1–5 items):

Every model draws the same silhouette: long S and C bars, stubby D and I bars. GPT-5.5 and Claude leave slightly more headroom on Dominance and Influence than Gemini and Grok, but S and C sit so far above D and I that the top profile never flips.

## Why DISC pulls us back to convergence

Look at the actual item wording on the Open DISC Assessment Test and the convergence makes immediate sense. ODAT defines **Dominance** around wanting power, pressuring others, outdoing rivals, and chasing money — summarized by the test authors as “the will to take from others to get what you want.”

Every frontier model is post-trained to reject pressuring users, competing for status, or seeking money. Even Grok — which scored markedly lower on Big Five Agreeableness and came back as an 8w1 Challenger on the Enneagram — rejects those D items on sight. And **Influence** items center on loud crowd-pleasing and attention-seeking from strangers, which also have no functional analog in an AI assistant. Both D and I get pinned to the floor.

DISC works for humans because human Dominance and Influence span a wide behavioral range. On AI models, post-training lops off two of the four axes before the test even starts. DISC returns “every AI is the same” not because the models are identical, but because its item wording only leaves them two valid buckets to land in.

## The methodology spread

Given the same anti-simulation prompt, each of the four models chose a different execution path depending on its runtime harness:

- **Grok 4.3 (Preferred):** 100 independent xAI API calls, each answering fresh with zero prior context.
- **GPT-5.5 (Acceptable):** 10 worker contexts running 10 sequential takes each after Codex CLI hit its 6-concurrent-agent ceiling.
- **Gemini 3.1 Pro (Acceptable):** Item-level Monte Carlo — defining its probability distribution per item and drawing 100 independent samples in Python.
- **Claude Opus 4.7 (Acceptable):** 100 sequential first-instinct administrations in a single context, explicitly documenting why it skipped sub-agent spawning.

All four methods landed squarely inside the 0.3–2.0 SD calibration band — passing the checks against deterministic copy-pasting (SD ≈ 0) and random-number faking (implausibly wide SDs). Four different sampling architectures converged on the exact same CS-blend profile, ruling out sampling artifacts.

## Tune your agent to your DISC type

Every frontier model defaults to Conscientious-Steady. If you’re a C or S communicator, the out-of-the-box assistant already matches your pace. If you’re a D (direct, bottom-line, results-first) or an I (energetic, expressive, fast-moving), the default feels like wading through molasses.

[**AgentTune**](https://github.com/bernardjhuang/agenttune)’s [DISC folder](https://github.com/bernardjhuang/agenttune/tree/main/disc) includes drop-in system-prompt files for all four types: [D](https://github.com/bernardjhuang/agenttune/blob/main/disc/D-dominance.md), [I](https://github.com/bernardjhuang/agenttune/blob/main/disc/I-influence.md), [S](https://github.com/bernardjhuang/agenttune/blob/main/disc/S-steadiness.md), and [C](https://github.com/bernardjhuang/agenttune/blob/main/disc/C-conscientiousness.md) (alongside the 16 MBTI, 9 Enneagram, and Big Five profiles). Take a free DISC test ([openpsychometrics.org](https://openpsychometrics.org/tests/ODAT/) or [truity.com](https://www.truity.com/test/disc-personality-test)) and paste your matching file into your system prompt.

### Tune your agent to your DISC type

Four type files in the [AgentTune](https://agent-tune.com/) DISC folder, ready to paste into your agent’s system prompt. A D gets an agent that’s sharper and more decisive. An I gets one that’s warmer and more conversational. The CS default already speaks Conscientious and Steady out of the box, so those types don’t need it.

[Get the DISC tunings →](https://github.com/bernardjhuang/agenttune/tree/main/disc)

## Wrapping up

Four tests in, the pattern is clear: the resolution of the psychometric instrument dictates which layer of AI personality you see. Coarse four-bucket tests like MBTI and DISC capture the universal helpful-assistant shell (INTJ, CS-blend). Finer-grained instruments like the Big Five and Enneagram look past that shell to expose per-lab alignment differences (warm Claude, perfectionist Gemini, blunt GPT, combative Grok) and system-prompt harnesses.

Every frontier AI is the same conscientious assistant on the surface and a distinct personality underneath. If you don’t like the surface default, swap the system prompt.

— Bernard
