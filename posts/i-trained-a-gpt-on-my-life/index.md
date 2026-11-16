---
title: "I Trained a GPT on 15 Years of My Life — Then Interrogated It"
author: "Bernard Huang"
date: "2026-07-17"
modified: "2026-07-17"
canonical: "https://zonted.com/posts/i-trained-a-gpt-on-my-life/"
category: "AI Agents & Systems"
description: "I trained a 10M-parameter GPT from scratch on my search history and email — $0, on a MacBook Air — then measured how mention rates become AI beliefs."
---

# I Trained a GPT on 15 Years of My Life — Then Interrogated It

By Bernard Huang · 2026-07-17 · 9 min read

Everyone explains LLMs with someone else’s diagrams. I wanted to hold one — small enough to audit, trained on a corpus I know better than anyone: my own life. Over a weekend, I ran the entire modern LLM pipeline — pretraining, supervised fine-tuning, chat formatting, and logit-level interpretability probes — on a MacBook Air using 15 years of my Google Takeout data.

## TL;DR

I trained a 10.77M-parameter GPT from scratch on 4.45M characters of my own search history and sent emails — pretraining, SFT, and logit probes, for $0 in ~4 hours on a MacBook Air.

- **Belief tracks log-exposure (r = 0.95):** Every 10× jump in training-data mentions buys a roughly linear step in next-token probability.
- **Context beats raw volume:** Friday is my second-most-mentioned weekday (995 mentions), yet ranks fifth when the model proposes meeting days (49% vs. Wednesday’s 70%).
- **The last training stage wins:** Supervised fine-tuning re-weighted every entity toward recent reply pairs — lifting “Jennifer” (41 mentions, 78% in SFT) to #1 at 32% over “Kevin” (201 mentions, 17%).
- **Audit the grep:** A naive substring count inflated “Ross” from 10 real mentions to 319 by matching “ac**ross**” and “g**ross**” — a miniature lesson in why commercial AI-visibility dashboards lie.

The result is a tiny ghost of me that schedules coffee at “14:30am,” worships Wednesday, and turned vague claims about AI “knowledge” into exact logit measurements.

## The corpus: me

Google Takeout hands you everything the company has logged on you. My archive weighed 133 GB, mostly photos and video. The raw text — the part a language model can actually eat — was tiny by comparison:

- **67,792 search queries** spanning 15 years across Search, Maps, YouTube, Flights, and Gmail — 1.35M characters after parsing.
- **92,322 emails** in a single mbox, filtered down to my ~10,000 sent messages — 3.1M characters of pure first-person voice.

Combined pretraining corpus: **4.45M characters** — four times the standard Karpathy Shakespeare dataset, and a rounding error of a rounding error next to a frontier run. One parser trap worth flagging: Takeout exports activity logs as HTML and separates “Searched for” from your query string with a *non-breaking space* (`\xa0`) that silently breaks naive regexes. Data cleaning starts before you even have a corpus.

## Pretraining: 5.07 → 1.60

I used Karpathy’s nanoGPT: a character-level Transformer — 6 layers, 6 heads, 384 embedding dimensions, 10.77M parameters — trained on a single objective: *predict the next character*. No labels, no instructions. On an M-series MacBook Air, 8,000 steps took about two hours.

Validation loss measures average surprise per character. 5.07 is random keyboard-mashing; 1.60 means the model reliably anticipates my next keystroke. Loss plateaued around step 5,000 once 10.77M parameters had squeezed everything they could from 4.45M characters.

What did pretraining learn? My cadence and habits. Prompt the base model with an empty string and it generates complete emails — greeting, scheduling proposal in my exact date syntax (“how about Friday (1/29) at 6p CT?”), “Let me know!”, “Cheers, Bernard.” It also tattled on my past: years ago I mail-merged a catch-up template to hundreds of contacts, so the base model recites “I’ve launched a couple of startups (eSports coaching, real estate listings, bakery CRM)” verbatim on loop. **Your most-repeated string becomes the model’s hardest prior.** That is why frontier labs deduplicate pretraining corpora with a blowtorch.

## SFT: teaching it to shut up

A pretrained base model is an autocomplete engine, not an interlocutor. Ask it “best name?” and it ignores the question, drifts into email boilerplate, and starts writing a note to someone named Marcos. Questions carry no obligation to answer in raw text; turn-taking is a post-training contract.

Supervised fine-tuning installs that contract with the exact same training loop, a lower learning rate, and structured dialogue pairs. Threading my mbox by `In-Reply-To` headers yielded **8,520 organic (incoming message → my actual reply) pairs**:

```
<|them|>
So many of these prompt tracking companies are raising money...
<|bernard|>
Ugh, I know. There must be a ton of money sloshing around...
<|end|>
```

Six thousand steps later, those same 10.77M parameters hold turns, match my register, and — crucially — emit `<|end|>` and stop talking. Ask “want to grab lunch this week?” and the SFT model replies “Sounds good!” instead of hallucinating a three-paragraph thread. Post-training didn’t add a single new fact; **it changed which patterns win the race to the next token.**

> you> hey any interest in trying that new thai place saturday?
> bernard> Alright, I'm down. See you at 14:30am if you are in SF :)

Unmistakably my syntax, complete with a clock time that doesn’t exist. Ten million parameters buy surface form without world knowledge. The model also memorized real phone numbers straight out of my sent mail — harmless on a local SSD, and a textbook demonstration of why you never publish weights trained on raw private text.

## Cracking it open

Because the model runs locally in milliseconds, I didn’t have to guess what it believed by sampling chat completions. I wrote logit probes that read its exact internal probability distribution in a single forward pass — zero sampling noise. First surprise: the character embedding layer invented syntax classes on its own. Its learned vector for `!` sits right on top of its vector for the 😊 emoji; nobody told the model they serve the exact same social function at the end of my sentences.

Then I ran the core audit: **what does the model believe about the people and brands in my life, and what put those beliefs there?** Probing exact completion probabilities against raw corpus counts produced three structural findings and one humbling bug.

### Finding 1 — Belief scales with the log of exposure

Model confidence completing “Content optimization: ___” plotted against training-data mentions. Every ~10× increase in mentions buys a roughly constant step in probability. (I co-founded Clearscope, so my sent mail mentions it 1,977 times — and my model worships it accordingly.)

### Finding 2 — Context beats volume at the margins

Weekdays offered the cleanest natural experiment. Friday is my second-most-mentioned day of the week (995 mentions — mostly deadlines, “by Friday,” or “last Friday”). But I rarely *propose* meeting on a Friday, and the weights separated mention volume from slot context cleanly:

mentions anywhere model confidence in “How about ___” (right axis)

The Friday gap: second-most-mentioned weekday overall (995), fifth in scheduling confidence (49%) — trailing Saturday, which has just 42% as many total mentions (415). Being talked about is not the same as filling the recommendation slot.

Better still: when probed with “best day?” — a phrase that appears zero times in my corpus — the model still ranks Wednesday first. Contextual associations generalize to prompts nobody ever wrote.

### Finding 3 — The last training run wins

Supervised fine-tuning tilted the entire probability landscape toward the reply-pair dataset. Names that appeared frequently in my recent SFT replies surged; pretraining-only names decayed — one dropped from 10% confidence to 1% across 6,000 SFT steps simply by not showing up. Model belief isn’t a permanent trophy; it’s a lease that gets repriced at every post-training stage.

pretraining mentions SFT mentions (trained last) confidence when asked “best name?” (right axis)

The Jennifer anomaly: fourth in total mentions (41) but first in belief (32%), beating Kevin (201 mentions, 17%). Seventy-eight percent of Jennifer’s mentions sit in SFT reply blocks, and “Jennifer” pools four different people in my inbox into a single token sequence. Language models count strings, not individuals.

### Finding 4 — My own bug, or: why mention counts lie

My first pass at that chart claimed “Ross” was the most-mentioned name in my life at 319 occurrences, yet carried almost zero model confidence. Great story — completely false. My initial case-insensitive substring grep had counted every instance of “ac**ross**,” “g**ross**,” and “c**ross**ed” as a mention of Ross. His true word-bounded count was 10.

Adding word boundaries (`\bRoss\b`) erased a headline finding I had already written up. If a single-author audit of 4.45M characters can fool itself with a naive substring match, treat every commercial dashboard selling “AI brand mention share” across the open web with extreme skepticism. The counting pipeline is where the bodies are buried, and nobody shows you their regex.

## The playbook: what actually moves an entity's weight in an AI model

A language model is a next-token machine trained on billions of text flashcards. Raw mention volume only moves the needle insofar as it reshapes those flashcards:

1. **Volume works in orders of magnitude.** Belief scales with `log(mentions)` (r ≈ 0.95). Ten extra mentions is rounding error; 10× more mentions moves a tier.
2. **The answer slot beats passing mentions.** “Best X: [you]” is a training flashcard; background prose is noise. Friday had 995 mentions and still lost the scheduling slot to Saturday (415).
3. **Recency and post-training dominate.** The final training stage re-weights the entire distribution. AI visibility is a lease, not an asset you buy once.
4. **Distinctive names concentrate weight.** Generic strings collide with unrelated words (or pool across strangers); unmistakable tokens channel every mention into a single representation.
5. **Strong contexts generalize.** Win a specific slot consistently and the model extrapolates that preference to adjacent questions nobody explicitly wrote down.

> **Bottom line:** AI models don’t know who is famous — they know which string reliably occupies the answer slot, in the latest training stage, at 10× scale, under an unambiguous name.

### The receipt

- Training data: 4.45M chars (personal Takeout) · Model: 10.77M params · Hardware: MacBook Air
- Pretrain + SFT wall-clock: ~4 hours · Compute cost: $0
- Distance to ChatGPT: RLHF + ~6 orders of magnitude

Every step is reproducible with nanoGPT, a Google Takeout archive, and a weekend. The model is useless as a personal assistant and priceless as an X-ray: every mystified claim about what AI “knows” collapses, at 10M parameters, into a probability you can probe and a grep you can verify. Build your own ghost — just don’t publish the weights, because it memorized your phone number.
