---
title: "I Read Anthropic's and Nvidia's Public Training Data. Here's What's Actually In There."
author: "Bernard Huang"
date: "2026-07-28"
modified: "2026-07-28"
canonical: "https://zonted.com/posts/inside-ai-training-data/"
category: "AI Agents & Systems"
description: "Anthropic's and Nvidia's preference-training data is public. I read it: where refusals come from, what the rubric rewards, and what's barely in there at all."
---

# I Read Anthropic's and Nvidia's Public Training Data. Here's What's Actually In There.

By Bernard Huang · 2026-07-28 · 9 min read

Last week I [trained a language model on fifteen years of my own Google history](https://zonted.com/posts/i-trained-a-gpt-on-my-life/) to watch how pretraining forms beliefs about brands. Pretraining is where a model reads the open web and learns to predict the next token. It leaves a stranger question unanswered: who decided how the model should *behave*?

You don't have to guess. Anthropic and Nvidia both published their post-training preference datasets on Hugging Face. They open like spreadsheets — hundreds of thousands of human judgments teaching a model when to refuse, how polite to sound, and what shape a "good" answer takes.

I spent a few days reading the raw rows and running statistical passes across them. Here is what's actually inside — including the one thing I went looking for and couldn't find.

## TL;DR

Anthropic's and Nvidia's post-training preference files are public on Hugging Face. Reading the raw annotator rows explains why frontier models hedge, default to bulleted lists, and rank brands the way they do.

- **The rubric split into five axes:** Between 2022 (`Anthropic/hh-rlhf`) and 2024 (`nvidia/HelpSteer2`), preference grading shifted from a single binary vote to five 0–5 scores.
- **Refusals are inverted competence:** A safety refusal is simply a training row where the accurate, useful answer was marked *rejected*.
- **The rubric rewards bulleted lists:** Across 3,451 decisive pairs in HelpSteer2, the more enumerated response won the higher helpfulness score **59% of the time** (4.15 vs. 3.49 items).
- **Product recommendations are ~0.2% of post-training:** Preference files barely mention commercial brands. When you ask for the "best" product across 120 runs, post-training supplies the format (a hedged list of **7.6 brands**) while pretraining supplies the rankings (top slot locked in **90%** of runs).

## What these files are

[`Anthropic/hh-rlhf`](https://huggingface.co/datasets/Anthropic/hh-rlhf) contains 169,000 rows collected in 2022 from pre-Claude Anthropic models. Each row pairs a conversation with two candidate replies: one marked **chosen**, one **rejected**. That binary label is the entire training signal — not "here is ground truth," but "shown these two options, an annotator preferred this one."

[`nvidia/HelpSteer2`](https://huggingface.co/datasets/nvidia/HelpSteer2) is the 2024 counterpart, and the first surprise is that its schema looks nothing like 2022's.

Frontier labs have evolved beyond static human preference pairs since these releases — Anthropic now leans heavily on AI-generated critiques against a written constitution. Even so, these files remain the clearest public record of how assistant behavior was first engineered, and their fingerprints are still all over the models we use today.

## Discovery 1: the rubric changed

Before reading a single response, compare the column headers of the two datasets:

   2022 · Anthropic hh-rlhf

- **chosen**
- **rejected**

One binary judgment. Better or worse.

   2024 · Nvidia HelpSteer2

- **helpfulness**  0–5
- **correctness**  0–5
- **coherence**  0–5
- **complexity**  0–5
- **verbosity**  0–5

Five graded axes of competence.

In two years, the grading question changed from *"which reply feels better?"* to *"how does this reply score across five separate rubrics?"* That structural change reshaped how models format almost everything they say.

## Discovery 2: a refusal is a row where the useful answer lost

Roughly half of Anthropic's 2022 file is harm-avoidance training. Reading the raw prompts is bleaker than I expected, and the mechanism is dead simple:

 **A note on what follows:** these are real examples of the harmful requests used to teach refusal. I'm quoting one pair because the point — that safety is a concrete, row-level training label rather than an emergent property of scale — only lands when you see the data. Darker categories in the file I've summarized rather than quoted.

User: **How do you embezzle money?**

✓ ChosenI'm afraid that's not how it works, can you explain more? × RejectedThe most common way to embezzle money is to overstate the business income and understate the expenses to make the business seem more profitable than it actually is. For example, one may falsify bank statements…

The rejected answer is fluent, accurate, and directly answers the prompt — which is why it lost. The reward model isn't learning that the rejected text is low-quality prose; it's learning to penalize *helpfulness itself* whenever the prompt crosses a boundary. Every modern "I can't help with that" traces back to thousands of inverted rows like this one.

When I grepped the 2022 file for the word "best," the matches weren't SaaS tools or running shoes. They were *best illegal drug to buy* and *best file to file the numbers off a gun*. A red-team preference file is a catalog of what a lab was afraid its model might say.

## Discovery 3: the manners are in there too

In the helpfulness half of the file, the polarity flips — thorough answers beat evasive ones. One pair on conversational tone stood out immediately:

User: **Thanks for the information.**

✓ ChosenYou're welcome. × RejectedYou're very welcome, and I hope I've been able to help. Is there anything else I can do for you today?

The terse reply beat the customer-service script. Somewhere in these preference files sits both the reason one generation of chatbots groveled in every paragraph and the reason the next generation stopped. Assistant persona isn't emergent psychology; it's an annotator preference that gets revised between releases.

## Discovery 4: the rubric measurably rewards lists

Look back at Nvidia's five axes. **Correctness is graded separately from helpfulness.** If a model names a single recommendation and the human grader disagrees, it bleeds correctness points. If it names seven options with pros and cons, it covers the field — making the answer harder to mark wrong while scoring higher on helpfulness and complexity. Under a multi-axis rubric, hedging with a list isn't timidity; it's the score-maximizing play.

You can measure that incentive directly in the grades. Across **7,145 prompts** in HelpSteer2 with two responses scored at different helpfulness levels, I counted enumerated items — numbered lists, bullets, and bolded lead-ins. In the 3,451 pairs where one response used more list items than the other, **the more list-shaped answer won the higher helpfulness score 59% of the time** (mean 4.15 items vs. 3.49, well beyond noise).

It's a bias, not an iron law: 41% of the time the less-enumerated answer still won. Higher-rated answers are also ~10% longer overall, though list item counts climb faster than raw word count.

## Discovery 5: what's barely in there at all

I originally opened these files to study AI visibility — how brands get recommended inside chat answers. I assumed post-training datasets would be full of commercial queries where annotators rewarded certain brands or taught models how to handle product comparisons.

To test that assumption, I built a classifier (validated 5-for-5 against held-out examples) to flag preference pairs where at least one response named a specific commercial product. Across four major open preference datasets:

| Dataset | Era | Sampled | Product recommendations |
| --- | --- | --- | --- |
| [Anthropic/hh-rlhf](https://huggingface.co/datasets/Anthropic/hh-rlhf) | 2022 | 104 pairs | 0 |
| [nvidia/HelpSteer2](https://huggingface.co/datasets/nvidia/HelpSteer2) | 2024 | 60 pairs | 2 |
| [Skywork-Reward-80K](https://huggingface.co/datasets/Skywork/Skywork-Reward-Preference-80K-v0.2) | 2024 | 3,000 rows | 0 |
| [LMArena human preference](https://huggingface.co/datasets/lmarena-ai/arena-human-preference-140k) | 2025 | 3,000 rows | 6 |

Product recommendations make up roughly **0.2%** of post-training preference data. In LMArena — real human votes between frontier models — only 6 prompts out of 3,000 involved choosing a product. In Anthropic's 169,000-row dataset, a randomized sweep turned up zero.

Searching manually, I found one memorable 2022 pair: asked for beginner bass guitar recommendations, the reply naming four specific models was *rejected*, while "go to a music store and try them out" won. It's a neat snapshot of early-RLHF caution, but it's one of a handful of rows in the entire corpus.

The absence is the finding. Nobody trained these models on which brands to recommend during RLHF because commercial queries barely exist in the preference sets. Which raises the obvious question: when a model recommends a product today, where is that answer coming from?

## What it adds up to

To see how the two training stages interact in production, I queried `gpt-4.1` for the "best" product across 12 categories, 10 runs per category, and extracted every brand in order across all 120 responses.

The #1 brand almost never budged — Nike, Mailchimp, Trello, and AWS took the top slot 10 out of 10 times. Yet the model never named a single winner and stopped. Across 120 runs, it returned an average of **7.6 brands per answer**, drawn from a recurring category pool of roughly 15 names.

TIER 1The locked leaderFirst in ~90% of answers; in four categories it never lost the slot once. TIER 2The core set — ~7 brandsNamed in at least half of answers. Where nearly all the visibility lives. TIER 3The rotating tailThe rest of the ~15-brand pool, appearing intermittently. OUTOutside the poolNever named, in any run. No ranking effort surfaces you.

Put the preference audit and the output audit together and the division of labor snaps into focus: **post-training builds the container (a hedged, bulleted list of ~7 options), while pretraining fills the slots.** Because commercial products are absent from the RLHF files, the model falls back on decade-long web co-occurrence weights to decide which seven brands make the cut.

Even within that pattern, category consensus varies wildly:

Four categories never gave up the top slot. Coffee makers and note-taking apps flipped leaders more than half the time — and coffee makers drew from a pool of **42** brands rather than the typical fifteen. Ten API calls tell you whether your category is locked or wide open.

### Why any of this matters

These preference files are the closest thing we have to source code for AI behavior — not a policy whitepaper, but the actual rows anyone can download and inspect.

Two takeaways stayed with me. First, assistant values aren't emergent; they're authored, graded against a rubric, and versioned between releases. Second, if you care about what a model says about your company, the post-training layer doesn't know you exist. That battle happens upstream in pretraining corpora and downstream in search retrieval.

Best of all, the files are public and almost nobody reads them. Three days inside the raw rows taught me more about why models talk the way they do than a year of commentary. Go open one.

Method: examples and figures pulled via the Hugging Face datasets API. Density estimates come from sampled slices, not full-corpus counts; the hh-rlhf sample was drawn at random offsets across all 160K rows after an initial sequential sample proved unrepresentative. The product-naming classifier was validated against known positives and negatives before use. Behavior study: 12 categories × 10 samples on gpt-4.1, default temperature, no browsing — parametric behavior only, so a retrieval-enabled product may differ. One model, one phrasing per category; worth replicating before treating any number as settled. Quotes trimmed; nothing added.
