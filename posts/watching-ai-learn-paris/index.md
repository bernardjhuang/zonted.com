---
title: "I Watched a Neural Network Learn That Paris Is the Capital of France"
author: "Bernard Huang"
date: "2026-07-28"
modified: "2026-07-28"
canonical: "https://zonted.com/posts/watching-ai-learn-paris/"
category: "AI Agents & Systems"
description: "Pythia ships a checkpoint every 1,000 training steps with countable training data. I replayed training like a time-lapse and watched a fact form."
---

# I Watched a Neural Network Learn That Paris Is the Capital of France

By Bernard Huang · 2026-07-28 · 7 min read

This month I [trained a model on my own Google history](https://zonted.com/posts/i-trained-a-gpt-on-my-life/) and [read the post-training files that teach models how to behave](https://zonted.com/posts/inside-ai-training-data/). Both experiments left the same question hanging: facts end up *inside* a model's weights — but when during training do they actually lock in? At what exact checkpoint does a neural network start believing that Paris is the capital of France?

With open checkpoints and an indexed training corpus, you don't have to guess. You can replay training like a time-lapse.

## TL;DR

EleutherAI's Pythia publishes 154 training checkpoints alongside a public, countable corpus — letting you watch a fact form inside a neural network step by step.

- **Fluency precedes facts:** At 2B tokens, the model writes grammatical English but believes **nothing** — every candidate city sits at 0%.
- **Placement beats raw fame:** Paris climbs 0% → 3% → 8% → **15.1%** across 300B tokens. London has 2× the corpus mentions (15.6M vs. 7.8M) and stays pinned at **0.05%** the entire run.
- **The ignition threshold:** Below a minimum evidence floor, extra training does nothing. Clearscope (64 mentions) sits at **0.00%–0.01%** across all 300B tokens — it never ignites.

## A time-lapse of training

Most model releases hand you one artifact: the finished weights. [Pythia](https://huggingface.co/EleutherAI/pythia-410m), a model family EleutherAI built specifically to study how representations form during pretraining, gives you three things at once:

- **154 checkpoints** — a saved snapshot every 1,000 training steps, from random initialization to the final 300B-token run
- **Open weights** — so you can read exact next-token probabilities instead of sampling text and guessing
- **A countable training corpus** (The Pile), [indexed via infini-gram](https://infini-gram.io/) — so you can look up the exact phrase frequency of everything the model ate

Put those three together and you can run an experiment that's impossible on GPT or Gemini: pick a fact, count its appearances in the training data, and measure the model's exact probability assignment at every stage of training.

My probe is simple: feed the model a prompt like *"The capital of France is"* and read the exact per-token probability of each candidate continuation in a single forward pass. No temperature, no sampling noise — just the raw credence inside the weights.

## Watching Paris form

Pythia-410M, exact probabilities at four checkpoints. London appears **15.6 million times** in the training data — twice Paris's 7.8 million — and never moves.

Three curves in that chart changed how I think about pretraining.

**At 2 billion tokens, the model is fluent and clueless.** By step 1,000, Pythia already writes grammatical English. Ask it for the capital of France, though, and every candidate city sits at 0%. Syntax arrives long before world knowledge.

**Paris accretes steadily.** 3% at 17B tokens, 8% at 75B, 15.1% at 300B. Knowledge doesn't flip on at a sudden phase transition; it builds like sediment each time the co-occurrence repeats across the corpus.

**London never moves.** London appears 15.6 million times in The Pile — twice Paris's 7.8 million. If early checkpoints leaned on raw token frequency before narrowing down context, London would spike early and decay later. Instead, it stays pinned at 0.05% from step 1,000 to the end. The network never confuses "London is common" with "London follows *the capital of France is*." **Conditional association isn't a late-stage refinement — it's the substrate from checkpoint one.**

## The ignition threshold

European capitals have millions of training examples. What happens when evidence is sparse — like software brands? I ran the same checkpoint sweep on *"The best SEO content optimization tool is"* and paired each tool with its exact mention count in The Pile:

| Tool | Mentions in corpus | @2B | @17B | @75B | @300B |
| --- | --- | --- | --- | --- | --- |
| Yoast | 16,611 | 0.00% | 0.59% | 1.85% | 2.47% |
| Ahrefs | 9,784 | 0.00% | 0.07% | 0.33% | 1.05% |
| Clearscope | 64 | 0.00% | 0.00% | 0.00% | 0.01% |

Belief forming (and not forming) for SEO tools across the same four checkpoints. Disclosure: I co-founded Clearscope, which is why I picked it — I wanted to audit my own brand's evidence trail. The Pile was assembled around 2020, before most of Clearscope's web footprint existed.

Yoast (16,611 mentions) and Ahrefs (9,784 mentions) climb steadily across checkpoints. Clearscope — 64 mentions in that 2020 snapshot — **never ignites**. Across 300 billion tokens of training, its probability never clears 0.01%.

Below a minimum evidence floor, additional training steps do nothing. The difference between 64 mentions and 10,000 isn't a proportional 150× scaling in confidence — it's the difference between zero representation and an active weight trajectory.

## What forming a belief actually takes

Put the two probes together and the mechanics of pretraining belief come down to three rules:

- **Placement sets the direction.** The network only learns what follows what. London's 15.6M raw mentions do zero work without the preceding context; Paris's placement in the answer slot does all of it.
- **Volume sets the slope.** Once an entity clears the floor, more contextual co-occurrences drive steeper probability gains across training steps.
- **An ignition threshold gates existence.** Below the floor, you aren't a low-probability candidate — you're noise.

For anyone working on AI visibility, that's the pretraining layer in plain numbers. If your brand sits below the ignition threshold in the pretraining corpus, no clever prompting wakes it up from the weights alone. And if you have massive mention volume but never appear in the answer slot after the category description, you're London: famous everywhere, predicted nowhere.

What stuck with me most, though, wasn't the marketing takeaway. "When does a neural network learn a fact?" sounds like a mechanistic interpretability project requiring a GPU cluster. In practice, it took a weekend, a laptop, open checkpoints, and a corpus you can grep. The time-lapse was already sitting on Hugging Face, waiting for someone to press play.

Method: [EleutherAI/pythia-410m](https://huggingface.co/EleutherAI/pythia-410m) at revisions step1000, step8000, step36000, and main (~2B / ~17B / ~75B / ~300B tokens at ~2M tokens per step). Beliefs are exact average log-probabilities per token of each continuation, converted to per-token probabilities — comparable across candidates on the same prompt. Mention counts are exact phrase counts over the Pile training split via the [infini-gram](https://infini-gram.io/) API; single-word counts can be inflated by unrelated senses (a caveat that cuts against brands with dictionary-word names). One model size, one prompt per fact — the shapes replicated across the prompts I tried, but treat exact percentages as illustrative, not universal.
