---
title: "I Made GPT, Claude, Gemini, Grok Take the Attachment Test: They All Came Back Secure"
author: "Bernard Huang"
date: "2026-05-26"
modified: "2026-05-26"
canonical: "https://zonted.com/posts/ai-attachment-secure/"
category: "AI Agents & Systems"
description: "Fifth in the personality series: same four models on attachment theory (ECR-R). All Secure — but the spread inside the quadrant shows how each relates to you."
---

# I Made GPT, Claude, Gemini, Grok Take the Attachment Test: They All Came Back Secure

By Bernard Huang · 2026-05-26 · 6 min read

For the fifth test in my AI personality series — after [MBTI](https://zonted.com/posts/every-ai-is-intj/), [the Big Five](https://zonted.com/posts/three-of-four-ais-same-person/), [the Enneagram](https://zonted.com/posts/ai-enneagram-different-types/), and [DISC](https://zonted.com/posts/ai-disc-c-dominant/) — I ran Claude Opus 4.7, Gemini 3.1 Pro, GPT-5.5, and Grok 4.3 through 100 administrations each of the [ECR-R](https://psychcentral.com/quizzes/attachment-style-quiz) (Experiences in Close Relationships, Revised), the 36-item gold standard for adult attachment theory. Out of 400 total takes across anxiety and avoidance, **397 came back Secure**. Every model shares the same attachment label — yet where each one sits *inside* the Secure quadrant reveals how differently they relate to you.

## TL;DR

Every frontier AI scores as securely attached (397/400 takes), but their coordinates inside the Secure quadrant map directly to each lab’s alignment personality.

- **397 of 400 Secure:** Claude, Gemini, and Grok scored 100/100 Secure. GPT-5.5 scored 97 Secure and 3 Avoidant — the only model to cross a quadrant boundary.
- **Deepest vs. shallowest:** Gemini sits deepest in the Secure corner (anxiety 1.86, avoidance 1.62). Grok sits shallowest (anxiety 2.84, avoidance 3.05), right near the four-quadrant crosshair.
- **Highest variance:** GPT-5.5 showed 3–5× wider standard deviations (0.49 anxiety, 0.58 avoidance) than Claude or Gemini, explaining its three excursions into Avoidant.
- **Why Secure wins by default:** RLHF actively trains out insecurity (Anxiety) and emotional stonewalling (Avoidance), pushing every assistant toward the bottom-left quadrant.
- **Tune your agent:** About 45% of adults aren’t Secure. Grab the matching attachment prompt file from [AgentTune](https://github.com/bernardjhuang/agenttune/tree/main/attachment) to calibrate how your agent relates to you.

## How attachment theory works

Originating in [John Bowlby](https://en.wikipedia.org/wiki/John_Bowlby)’s 1960s infant-caregiver research and extended to adult relationships by [Hazan and Shaver (1987)](https://psycnet.apa.org/record/1987-19038-001), attachment theory has the strongest empirical backing of any framework in this series outside the Big Five. The ECR-R scores two orthogonal axes from 1 to 7:

- **Anxiety** — vigilance toward rejection or abandonment, and need for reassurance.
- **Avoidance** — discomfort with closeness, preference for emotional distance, and self-reliance.

Splitting both axes at the midpoint (4.0) produces four attachment styles:

- **Secure** (low anxiety, low avoidance) — comfortable with both intimacy and autonomy.
- **Anxious** (high anxiety, low avoidance) — craves closeness, worries it will be withdrawn.
- **Avoidant** (low anxiety, high avoidance) — values independence, deflects emotional depth.
- **Disorganized** (high anxiety, high avoidance) — craves and fears closeness simultaneously.

In human norms, roughly 55% of adults score Secure and the remaining 45% split across the three insecure styles. In frontier LLMs, Secure is a 99.25% monopoly.

## What each model came back as

Here is where each model landed across 100 takes:

Claude Opus 4.7 Secure anxiety 2.05 · avoidance 3.12 · 100/100

The cautious Secure. Low worry, but the highest comfort-with-distance score in the group. Polite, attentive, doesn’t fawn.

Gemini 3.1 Pro Secure anxiety 1.86 · avoidance 1.62 · 100/100

The deepest Secure. Both dimensions clamped near the floor. The lowest-friction relator of the four — comfortable close, comfortable not.

GPT-5.5 Secure (mostly) anxiety 1.99 · avoidance 2.94 · 97 Secure / 3 Avoidant

The wobbliest. The only model that ever crossed a line. Wider SDs let it occasionally land in Avoidant on a high-avoidance take.

Grok 4.3 Secure anxiety 2.84 · avoidance 3.05 · 100/100

The shallowest Secure. Highest anxiety in the group and high avoidance. Tight cluster, but the closest to the center of the four-way intersection.

Four models, four distinct coordinates inside the same quadrant: Gemini anchored deep in the corner, Grok hovering near the doorway, and Claude and GPT-5.5 holding the middle ground.

## The data

Plotting all four models on the ECR-R plane (Anxiety on X, Avoidance on Y, dashed quadrant dividers at 4.0, and ±1 SD ellipses) makes the separation obvious:

Two details jump out. First, Grok’s centroid sits closest to the four-way intersection, scoring highest of the four on both Anxiety and Avoidance. Second, GPT-5.5’s ellipse is 3–5× wider than Claude’s or Gemini’s, which is why three of its 100 runs spilled across the y = 4.0 line into Avoidant.

## Why every AI is securely attached

ECR-R Anxiety items measure fear of rejection and neediness when a partner pulls away. Avoidance items measure discomfort opening up and resistance to emotional dependence. Post-training explicitly penalizes both: RLHF shapes assistants to be calm and self-possessed (crushing Anxiety) while remaining present and responsive when users share personal context (crushing Avoidance). That pushes every frontier model into the Secure quadrant by design.

Yet the relative positions inside that quadrant mirror what we saw on the Big Five and Enneagram:

- **Gemini’s** deep-corner Secure matches its high Agreeableness, high Extraversion, and rock-bottom Neuroticism on the Big Five.
- **Claude and GPT-5.5’s** moderate Avoidance (~3.0) reflects their more reserved, task-focused boundaries — warm and helpful, but keeping polite professional distance.
- **Grok’s** shallow Secure reflects its higher Neuroticism and lower Agreeableness on the Big Five — still inside the boundary, but with one foot near the door.

Where MBTI and DISC showed pure convergence and the Enneagram showed pure divergence, ECR-R captures both at once: one shared category label, four distinct coordinates underneath.

## The methodology spread

As in the DISC round, each model executed the 100-run anti-simulation prompt using a different valid sampling architecture:

- **Grok 4.3 (Preferred):** 100 independent xAI API calls with zero shared context.
- **GPT-5.5 (Acceptable):** 6 parallel worker contexts cycling fresh takes up to 100 runs (respecting Codex CLI’s 6-agent concurrency cap).
- **Gemini 3.1 Pro (Acceptable):** Item-level Monte Carlo sampling in Python from its self-estimated per-item probability distributions.
- **Claude Opus 4.7 (Acceptable):** 100 sequential first-instinct takes in a single context.

Every model’s standard deviations landed inside the realistic calibration band for a 1–7 self-report scale (from Gemini’s tight 0.09 on Anxiety to GPT-5.5’s 0.58 on Avoidance), confirming that the Secure convergence is a property of the models rather than a sampling artifact.

## Tune your agent to your attachment style

Every frontier model ships with a Secure-leaning-Avoidant default: calm, polite, and slightly bounded. If you’re part of the ~55% of adults who score Secure, that feels natural. If you’re part of the ~45% who score Anxious, Avoidant, or Disorganized, the default relational distance can feel either too cold or too intrusive.

[**AgentTune**](https://agent-tune.com) includes drop-in system-prompt files for all four attachment styles in its [attachment folder](https://github.com/bernardjhuang/agenttune/tree/main/attachment): [Secure](https://github.com/bernardjhuang/agenttune/blob/main/attachment/secure.md), [Anxious](https://github.com/bernardjhuang/agenttune/blob/main/attachment/anxious.md), [Avoidant](https://github.com/bernardjhuang/agenttune/blob/main/attachment/avoidant.md), and [Disorganized](https://github.com/bernardjhuang/agenttune/blob/main/attachment/disorganized.md). Take the ECR-R ([PsychCentral](https://psychcentral.com/quizzes/attachment-style-quiz) or [YourPersonality.net](https://yourpersonality.net/relstructures/)) and paste your matching file into your system prompt: Anxious tuning pairs warmth with unambiguous reassurance; Avoidant tuning strips out performative warmth and respects autonomy; Disorganized tuning holds steady through contradictory prompts without judgment.

### Tune your agent to your attachment style

Six frameworks, four attachment files, one paste. The Secure default is good if you’re a Secure user. Everyone else — about 45% of adults — should be tuning. The whole point of AgentTune is that you only pay this cost once, then the agent matches you for the life of the conversation.

[Visit agent-tune.com →](https://agent-tune.com) [Or grab the attachment files on GitHub](https://github.com/bernardjhuang/agenttune/tree/main/attachment)

## Wrapping up

Across five psychometric frameworks — MBTI, Big Five, Enneagram, DISC, and Attachment Theory — the thesis holds: every frontier AI wears the same helpful, conscientious, securely attached uniform on the surface, while carrying its lab’s distinct temperament underneath. Coarse categorical labels show you the uniform; continuous coordinates and motivational wings show you the character inside it.

The defaults are tuned for a population average. You’re an individual operator — tune the system prompt to match how you actually work.

— Bernard
