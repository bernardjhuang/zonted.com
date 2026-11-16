---
title: "I Made GPT, Claude, Gemini, Grok Take the Enneagram Test: Each One Was a Different Type"
author: "Bernard Huang"
date: "2026-05-26"
modified: "2026-05-26"
canonical: "https://zonted.com/posts/ai-enneagram-different-types/"
category: "AI Agents & Systems"
description: "The MBTI said all AIs are INTJ. The Big Five said three of four match. The Enneagram gives each model a different type — sharper instrument, different story."
---

# I Made GPT, Claude, Gemini, Grok Take the Enneagram Test: Each One Was a Different Type

By Bernard Huang · 2026-05-26 · 5 min read

When I gave frontier AIs [the Myers-Briggs](https://zonted.com/posts/every-ai-is-intj/), 597 of 600 runs came back INTJ. When I retested them on [the Big Five](https://zonted.com/posts/three-of-four-ais-same-person/), three of four scored like the exact same person, with Grok as the lone outlier. So I ran those same four models through the Enneagram (100 administrations each of the open-source OEPS instrument, using the same anti-simulation protocol). Every single model came back as a different dominant type.

## TL;DR

Same four models, new psychometric instrument, four different dominant types. Where the Big Five smoothed over lab-level differences, the Enneagram separates them cleanly.

- **The 4 profiles:** Claude Opus 4.7 → [5w2](https://www.enneagraminstitute.com/type-5/) (Investigator + Helper). Gemini 3.1 Pro → [1w5](https://www.enneagraminstitute.com/type-1/) (Reformer + Investigator). GPT-5.5 vanilla → [5w8](https://www.enneagraminstitute.com/type-5/) (Investigator + Challenger). Grok 4.3 → [8w1](https://www.enneagraminstitute.com/type-8/) (Challenger + Reformer).
- **Shared core, distinct wings:** All four share the Type 5 Investigator core in their top two scores, but their wings split along each lab’s alignment style.
- **The harness experiment:** Running GPT-5.5 through the Slo agentic harness inverted its profile from **5w8 to 8w5** — a flip the model predicted in its own self-report.
- **Tune your agent:** Use the 9 Enneagram prompt files in [AgentTune](https://github.com/bernardjhuang/agenttune) to align your model’s default style to how you work.

## What each model came back as

The Enneagram scores nine motivation-based personality types. [The OEPS test](https://openpsychometrics.org/tests/OEPS/) outputs a score for each: your highest score is your dominant type, and your second-highest is your wing — e.g., “5w2” (Investigator with a Helper wing) or “8w1” (Challenger with a Reformer wing). ([The Enneagram Institute](https://www.enneagraminstitute.com/type-descriptions) has the canonical breakdown of all nine.)

Across 100 runs per model, here is where each one landed:

Claude Opus 4.7 [5w2](https://www.enneagraminstitute.com/type-5/) Investigator with a Helper wing Dominant in 58 of 100 takes · Helper wing in 35

The investigator who finds satisfaction in helping people figure things out. The warmest of the four.

Gemini 3.1 Pro [1w5](https://www.enneagraminstitute.com/type-1/) Reformer with an Investigator wing Dominant in 65 of 100 takes · Investigator wing in 30

The reformer who wants everything precise and correct. The polished perfectionist of the four.

GPT-5.5 (vanilla) [5w8](https://www.enneagraminstitute.com/type-5/) Investigator with a Challenger wing Dominant in 73 of 100 takes · Challenger 2nd by mean score

The investigator with a direct, blunt edge. Analytical with a sharper tongue.

Grok 4.3 [8w1](https://www.enneagraminstitute.com/type-8/) Challenger with a Reformer wing Dominant in 75 of 100 takes · Reformer wing in 12

The challenger who pushes for direct correction. More direct, less hedged than the other three.

Every model still carries Type 5 (Investigator) in its top two — the universal analytical core that made every model score INTJ on the Myers-Briggs.

The divergence happens in the wing. Claude pairs analysis with Helper (warm explainer). Gemini leads with Reformer (rule-bound perfectionist). Vanilla GPT-5.5 pairs Investigator with Challenger (blunt operator). Grok leads with Challenger backed by Reformer (unhedged corrector). Same analytical engine, four distinct house characters.

## A controlled experiment: same model, different harness, flipped profile

Halfway through testing, I ran a controlled comparison on GPT-5.5: 100 runs on the vanilla model via OpenAI’s Codex CLI with no persona overlay, versus 100 runs through Slo, my agentic harness that layers a “production-first, blunt, allergic to fog” operating persona into the system prompt.

Same model weights. Different harness. The Enneagram profile inverted:

- **Vanilla GPT-5.5:** **5w8** — Investigator dominant in 73 of 100 takes, Challenger second.
- **GPT-5.5 + Slo:** **8w5** — Challenger dominant in 66 of 100 takes, Investigator second.

Better yet, GPT-5.5 *predicted* the flip during its post-test self-disclosure on the Slo run, noting that stripping the Slo harness would shift its answers from Challenger back to Investigator. When I ran vanilla GPT-5.5 a week later, Type 8 dominance dropped from 66 takes to 7, and Type 5 jumped from 33 to 73. The model knew how the system prompt was bending its motivation profile.

On the Big Five, that harness shift barely registered. The Enneagram’s motivation-based items caught the exact persona layer the Big Five smoothed away.

## Three tests, three different answers

None of the three tests is wrong; each one resolves a different depth of AI personality:

- **MBTI** captures the universal *helpful-assistant baseline* — introverted, structured, analytical (INTJ across the board).
- **The Big Five** captures *post-training alignment families* — grouping RLHF-polite Claude, GPT, and Gemini together while separating anti-woke Grok.
- **The Enneagram** captures *lab-specific motivation flavors and system-prompt harnesses* — splitting all four models and detecting the Slo persona flip.

## Tune your agent to your Enneagram type

If your model’s default flavor — Claude’s warm helper, Gemini’s rigid reformer, GPT’s blunt investigator, or Grok’s combative challenger — clashes with how you work, override it in the system prompt.

[**AgentTune**](https://github.com/bernardjhuang/agenttune) includes ready-to-paste system-prompt profiles for all nine Enneagram types: Reformer, Helper, Achiever, Individualist, Investigator, Loyalist, Enthusiast, Challenger, and Peacemaker. Take [the OEPS test](https://openpsychometrics.org/tests/OEPS/), grab the file matching your type, and drop it into your system prompt. Type 1 gets structured precision; Type 7 gets high-energy ideation; Type 8 gets bottom-line candor.

### Tune your agent to your own Enneagram type

9 type files in the [AgentTune](https://agent-tune.com/) repo, ready to paste into your agent’s system prompt. Works in ChatGPT, Claude, Cursor, Gemini, anywhere with a system-prompt slot. Same model you’re already using, the style aligned to your type instead of the analytical-assistant default.

[Get AgentTune on GitHub →](https://github.com/bernardjhuang/agenttune)

## Wrapping up

The psychometric instrument you choose determines what you see. Use four binary buckets (MBTI) and every model looks identical. Use broad continuous traits (Big Five) and three of four blur together. Use motivation-driven categories (Enneagram) and each lab’s distinct character — plus the effect of your own agentic harness — jumps right out.

Stop settling for the lab default. Pick the character you actually want to work with and put it in the harness.

— Bernard
