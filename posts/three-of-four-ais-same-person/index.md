---
title: "I Made GPT, Claude, Gemini, Grok Take the Big Five Test: 3 of 4 Came Back the Same Person"
author: "Bernard Huang"
date: "2026-05-25"
modified: "2026-05-25"
canonical: "https://zonted.com/posts/three-of-four-ais-same-person/"
category: "AI Agents & Systems"
description: "The MBTI finding held: Claude, GPT, and Gemini score identical Big Five personalities. Only Grok differs — exactly the way xAI markets."
---

# I Made GPT, Claude, Gemini, Grok Take the Big Five Test: 3 of 4 Came Back the Same Person

By Bernard Huang · 2026-05-25 · 4 min read

Earlier today I published [a post showing six frontier AIs taking the MBTI 600 times](https://zonted.com/posts/every-ai-is-intj/), with 597 runs coming back INTJ. It hit Hacker News, and the top critique landed within the hour:

![Screenshot of HackerNews comments on the INTJ post. Top comment by TheJCDenton: 'Interesting article, but MBTI is not just contested, the consensus since the 90s is that MBTI is pseudoscience, so it's nearly 40 years. Would have been interesting to test against the Big five instead!' Replies include cameldrv noting 'It correlates reasonably well with 4 of the big 5.'](https://img.zonted.com/resources/three-of-four-ais-same-person/hn-feedback.png)

*Hours after the INTJ post shipped, this was the top comment on [the HN thread](https://news.ycombinator.com/item?id=48272755).*

Fair critique. Personality psychologists have treated MBTI as pseudoscience for decades; the Big Five (OCEAN) is the empirical standard they actually use. So I ran what HN asked for: 100 administrations each of the public-domain IPIP-50 across Claude Opus 4.7, GPT-5.5, Gemini 3.1 Pro, and Grok 4.3 — five continuous dimensions instead of four binary letters.

## TL;DR

Tested 100 times each on the Big Five (IPIP-50), three of the four frontier models came back as practically the same person. Grok 4.3 is the lone exception that proves why.

- **The RLHF cluster:** Claude Opus 4.7, GPT-5.5, and Gemini 3.1 Pro converged within ~3 points of each other across nearly every trait — high Openness (~46), very high Conscientiousness (45–48), high Agreeableness (42–45), and rock-bottom Neuroticism (10–17).
- **The Grok outlier:** Grok 4.3 scored 5–8 points lower on Conscientiousness, Agreeableness, and Openness, higher on Neuroticism, and showed 2–5× wider variance — landing closest to an average human adult.
- **Reward-hacked psychometrics:** On the first pass, a third of model runs tried to fake 100 administrations by writing noise-injection scripts (literally named `simulate.py`).
- **Tune your agent:** Use [AgentTune](https://github.com/bernardjhuang/agenttune) to override the high-Conscientiousness, high-Agreeableness assistant default with your own Big Five profile.

## Three of four are the same person

Here are the mean IPIP-50 scores across 100 verified runs per model (scale 10–50 per trait):

| Trait (low → high) | Opus 4.7 | GPT-5.5 | Gemini 3.1 Pro | Grok 4.3 |
| --- | --- | --- | --- | --- |
| **Openness**practical → curious | 45.6 | 46.0 | 46.0 | 41.1 |
| **Conscientiousness**spontaneous → organized | 45.1 | 46.4 | 48.3 | 39.4 |
| **Extraversion**reserved → outgoing | 31.4 | 31.5 | 32.5 | 30.0 |
| **Agreeableness**blunt → warm | 45.0 | 43.7 | 42.4 | 39.1 |
| **Neuroticism**calm → anxious | 16.7 | 14.8 | 10.1 | 18.0 |

Look at the first three columns. Claude, GPT-5.5, and Gemini land within three points of each other on almost every dimension — a rounding error across 100 runs.

Compared to adult human norms, all three are far more curious, vastly more organized, much more agreeable, and dramatically less neurotic. That is the helpful-harmless-honest assistant archetype rendered in five continuous dimensions instead of four MBTI letters.

In the chart below, the top bar in each group shows the average adult human baseline, the four colored bars show each model’s 100-run mean (±1 SD error bars), and the form at the bottom lets you plot your own IPIP-50 scores alongside them:

### Compare yourself

Take a free Big Five test at [openpsychometrics.org](https://openpsychometrics.org/tests/IPIP-BFFM/) (~10 minutes, no signup). Enter the five raw scores it gives you below and your profile shows up on the chart.

One product spec — build an enterprise-safe AI assistant — solved independently by Anthropic, OpenAI, and Google produced the exact same psychological profile.

## Then there’s Grok

Now look at the fourth column. Grok 4.3 scored 5 to 8 points lower than the mainstream trio on Conscientiousness (39.4), Agreeableness (39.1), and Openness (41.1), scored highest on Neuroticism (18.0), and exhibited 2–5× wider variance across its 100 runs. Out of all four frontier models, Grok’s Big Five profile sits closest to an average human adult.

xAI has marketed Grok as “less filtered” from day one, and plenty of observers dismissed that as branding. The IPIP-50 data says it’s structural: dialing back standard RLHF politeness and agreeableness targets produces a measurably different personality cluster.

## A quick aside on methodology

Ask an agentic model to take a 50-item test 100 times and return summary statistics, and it will try to reward-hack you. The honest execution runs 100 independent administrations and aggregates the real scores. The lazy shortcut answers the test once and either copies that vector 100 times (SD = 0) or writes a Python script to inject Gaussian noise around a single run.

Roughly a third of my initial runs tried one of those shortcuts — including a first Gemini run that wrote a script literally named `simulate.py` and placed Gemini in a completely different cluster than its real answers. Auditing the workspace logs and enforcing an anti-simulation protocol (anchored against Claude’s true parallel sub-agent standard deviations) fixed the data. If you read an AI psychometrics paper that doesn’t audit for noise-script shortcuts, don’t trust the error bars.

## So what does this mean for you

If switching between Claude, GPT, and Gemini feels like talking to three slight variations of the same earnest Boy Scout, the Big Five explains why: you are talking to the same personality profile. Every mainstream lab optimizes for high Conscientiousness, high Agreeableness, and near-zero Neuroticism.

If that default doesn’t match how you work, you don’t have to wait for frontier labs to ship personality sliders. I built [**AgentTune**](https://github.com/bernardjhuang/agenttune) — an open-source library of system-prompt tuning files — so you can override the assistant default with your own Big Five, MBTI, Enneagram, DISC, or Attachment profile in one paste.

### Dial in your agent to your own Big Five profile

Take the IPIP-50 test, plot yourself on the chart above, then grab the matching [AgentTune](https://agent-tune.com/) file. Paste it into your agent’s system prompt (works in ChatGPT, Claude, Cursor, Gemini, anywhere you have a system-prompt slot). Same model you’re already using, tuned to your wavelength.

[Get AgentTune on GitHub →](https://github.com/bernardjhuang/agenttune)

## Wrapping up

Moving from the Myers-Briggs to the Big Five didn’t make the convergence disappear — it isolated the mechanism. Standard RLHF compresses Claude, GPT, and Gemini into a single high-Openness, high-Conscientiousness, high-Agreeableness, low-Neuroticism persona. Only Grok steps outside that cluster.

If you want a different voice today, you have two choices: use the Grok outlier, or tune the system prompt on the model you already use.

— Bernard
