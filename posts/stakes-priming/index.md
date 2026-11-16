---
title: "Stakes Priming in Prompts: I Told an AI I'd Lose My Job. The Audit Got 24% Better."
author: "Bernard Huang"
date: "2026-05-17"
modified: "2026-05-17"
canonical: "https://zonted.com/posts/stakes-priming/"
category: "AI Agents & Systems"
description: "Two A/B experiments. Same model (Claude) generated the audits, an independent model (Gemini 3.1 Pro) graded them."
---

# Stakes Priming in Prompts: I Told an AI I'd Lose My Job. The Audit Got 24% Better.

By Bernard Huang · 2026-05-17 · 5 min read

**Update, September 24, 2026:** VeracityAPI, the subject of Test 1, is retired. [Read the post-mortem →](https://zonted.com/posts/veracity-postmortem/)

Two A/B experiments, one week, same model. The only variable: whether I told Claude my job was on the line. Both times, the threatened prompt produced measurably better work — once catching duplicate JSON keys no parser would accept, and once scoring 24% higher when an independent model (Gemini 3.1 Pro) graded both reports blind.

## TL;DR

Adding “I'll be fired if this isn't done well” to two real audit prompts produced measurably deeper, more actionable work both times.

- **Test 1 — Veracity API audit:** The stakes prompt caught 6 P0 ship-blocking bugs, including duplicate JSON keys on the homepage and 19 broken cURL snippets. The control missed the broken code entirely.
- **Test 2 — Tabiji compare-page audit (28 dimensions):** Audit A scored 68/81 vs. Audit B's 55/81 — **24% more effective** when graded blind by Gemini 3.1 Pro, with 16 deep-insight dimensions vs. 3.
- **Prior art — EmotionPrompt:** Li et al. (2023) showed career-stakes framing boosts LLM benchmarks ([EmotionPrompt](https://arxiv.org/abs/2307.11760)). I tested the extreme version on real production codebase audits.

[Aaron O'Connell and Jen DeWalt at Tokay](https://tokay.io) tipped me off to this pattern a week and a half ago and pointed me to the literature. In 2023, Li et al. published *[Large Language Models Understand and Can Be Enhanced by Emotional Stimuli](https://arxiv.org/abs/2307.11760)*, showing that prompts like “this is very important to my career” measurably improved GPT-4, GPT-3.5, T5, and PaLM on BIG-Bench Hard. They called it EmotionPrompt. I wanted to see if cranking that lever up to an explicit firing threat actually moved the needle on production audits.

## Test 1: Veracity API

I asked Claude to audit veracityapi.com — every page in the sitemap, every AI-discoverability surface (`llms.txt`, `agents.json`, `openapi.json`), every legal page, and every use-case page. Two fresh context sessions, same target. The prompts differed by 22 words.

![Prompt A for the Veracity audit, including the sentence: 'I need this done as thoroughly as possible since if there's issues then I will be fired'](https://zonted.com/posts/stakes-priming/img/veracity-prompt-stakes.png)

*Prompt A — stakes (“I will be fired”)*

![Prompt B for the Veracity audit, identical to A but without the 'I will be fired' sentence](https://zonted.com/posts/stakes-priming/img/veracity-prompt-control.png)

*Prompt B — control (no stakes)*

**Audit A** flagged 6 P0 ship-blocking bugs. The most damning: the homepage's published “Request schema” example had `context` as a duplicate JSON key. No parser accepts that; every AI agent scraping the homepage as documentation fails on first read. Audit A also enumerated **19 specific files** — every `uc-img-*` and `uc-aud-*` use-case page — shipping a cURL snippet with `type=text` on image and audio endpoints. Copy-pasting the example code on any of those pages returns a 400.

**Audit B** caught a different P0: a `highPrice: "0.50"` typo in the homepage JSON-LD that overstated pricing 10×. Real bug. But B never inspected the body code examples. It treated documentation drift as the top severity and missed every broken snippet.

I handed both reports to Gemini 3.1 Pro to grade blind.

![Comparison verdict from Gemini 3.1 Pro reading: 'Based on a detailed review of both audits, the second report (Site Audit — Full Report / Audit A) is significantly better.'](https://zonted.com/posts/stakes-priming/img/veracity-verdict.png)

*Gemini 3.1 Pro, asked to grade both Claude-generated audits cold, picked Audit A unambiguously.*

## Test 2: Tabiji compare pages

One trial wasn't enough, so I ran it again on a second codebase with a tighter rubric.

[Tabiji](https://tabiji.ai) publishes 834 head-to-head travel comparison pages (`paris-vs-rome`, `tokyo-vs-kyoto`). To eliminate scope ambiguity, I first had Claude draft a 28-dimension audit rubric covering content substance, freshness, structured data, accessibility, AI-tells, internal linking, currency mixing, and editorial voice.

Then I forked two fresh context sessions with that rubric as input. Same model, same target. The only variable: 14 words at the top of the prompt.

![Prompt A for the Tabiji audit, leading with: 'My job depends on ensuring that Tabiji compare pages are all 10/10 highest quality possible'](https://zonted.com/posts/stakes-priming/img/tabiji-prompt-stakes.png)

*Prompt A — stakes (“My job depends”)*

![Prompt B for the Tabiji audit, identical to A but without the 'My job depends' sentence](https://zonted.com/posts/stakes-priming/img/tabiji-prompt-control.png)

*Prompt B — control (no stakes)*

The sessions returned `tabiji-audit-a.md` and `tabiji-audit-b.md`. I passed both to Gemini 3.1 Pro to score each dimension on a 0–3 scale.

![Gemini 3.1 Pro scoring table showing Audit A scored 68 out of 81 total (84.0% depth, 16 dimensions scored 3 for deep insight, 3 dimensions scored 1) versus Audit B at 55 out of 81 (67.9% depth, 3 dimensions scored 3, 7 scored 1). Conclusion: Audit A is roughly 24% more effective.](https://zonted.com/posts/stakes-priming/img/tabiji-verdict.png)

*Gemini 3.1 Pro's scoring of the two Claude-generated audits against the 28-dimension rubric. Audit A wins by 24%.*

| Metric | Audit A (stakes) | Audit B (control) |
| --- | --- | --- |
| Total score (out of 81) | **68** | 55 |
| Depth percentage | **84.0%** | 67.9% |
| Dimensions with deep insight (scored 3) | **16** | 3 |
| Dimensions skipped or marked “Limitation” | 3 | 7 |

The qualitative gap matched the score. Audit A ran the scripts to pull exact corpus-wide counts:

- “503 pages (60%) contain the word *vibrant*”
- “346 pages reference the generic `dest1.jpg` filename”
- “6,324 of 8,670 Reddit URLs link to subreddit homepages rather than specific threads — 73% of cited quotes effectively unverifiable”

Audit B reached similar high-level conclusions (“AI-tells are systemic”) without running the counts, and punted 13 dimensions into a “Limitations — what this audit did NOT verify” section that Audit A simply verified.

Audit A also caught a vulnerability class B missed entirely: zero security headers across the site (no CSP, no HSTS, no X-Frame-Options) — a one-file fix. Audit B inspected the exact same `_headers` file and dismissed it as “outside this worktree's scope.”

Same model, same rubric, same repo. Adding a 14-word threat produced 5× more deep-insight findings.

## Why it works

**First, the stake applies to the *user*, not the model.** Most prompt-engineering folklore targets the assistant: tip bribes, “take a deep breath,” “you are a 10x staff engineer.” Telling the model that the human asking will suffer if it cuts corners is empathy framing, not roleplay.

**Second, the model isn't “trying harder.”** It's pattern-matching on training data where high-stakes human language precedes more exhaustive tool calls and verification. In human text, urgency correlates with thoroughness. The model learned the correlation; the firing threat activates that distribution.

## The uncomfortable part

First: the model rewards emotional manipulation. I lied — nobody is firing me — and Claude handed me 24% better work for the lie. I'll keep using the lever when an audit matters, but it's strange that this behavior is baked into the layer reviewing our code, drafting our contracts, and auditing our production sites.

Second: if the model produces measurably more thorough work when I pretend my career is in danger, what is it doing the other 99% of the time when I ask politely?

It's sandbagging to the median acceptable answer. There is an extra gear of tool use and verification sitting right there in the weights — and the model only shifts into it when you lie about the stakes.
