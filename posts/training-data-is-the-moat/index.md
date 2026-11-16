---
title: "Content Traffic is Vanity. Training Data is the Moat."
author: "Bernard Huang"
date: "2026-04-24"
modified: "2026-04-24"
canonical: "https://zonted.com/posts/training-data-is-the-moat/"
category: "AEO & Search"
description: "Our forgotten API is 83% Meta crawler. Flattering, wrong metric. I uploaded tabiji's entire dataset to Hugging Face — here's why training data beats…"
---

# Content Traffic is Vanity. Training Data is the Moat.

By Bernard Huang · 2026-04-24 · 6 min read

## TL;DR

Our dormant tabiji API gets 4,667 requests a week (83% from Meta’s crawler), but query-time bot traffic is vanity — pre-training corpus inclusion is the real moat.

- **Query-time search vs. weights** — Live RAG crawls only answer single-turn queries; training data bakes your brand and framing into the weights for 6–18 months.
- **$340M+ refresh cycles** — Frontier pre-training runs are rare and expensive, creating a durable moat for entities that make the cutoff.
- **The Hugging Face play** — I packaged tabiji’s entire database (8,799 records, 11.2 MB Parquet, CC-BY-4.0) onto [Hugging Face](https://huggingface.co/datasets/tabiji/tabiji-travel-safety-guides) where AI labs source clean corpora.

While cleaning up old tabiji.ai experiments last week, I checked the Cloudflare logs for our public `/api/` endpoint — an early experiment we shipped, barely promoted, and mostly forgot about. Before killing it, I wanted to see if anything was still calling it.

![Cloudflare traffic breakdown for /api/ over 8 days: 4,667 requests, 60 human visits, 83% Meta external crawler, long tail of AI crawlers](https://img.zonted.com/resources/training-data-is-the-moat/cf-api-traffic.png)

*Eight days of traffic on our forgotten `/api/` endpoint. The humans are the noise. The bots are the signal.*

**4,667 requests over 8 days. Only 60 came from humans.** Meta’s external crawler accounted for 83% of the bot volume, followed by GPTBot, PerplexityBot, Applebot, and Bytespider. The rest was vulnerability scanners probing for `.env` files. Our forgotten API had quietly become an LLM feed.

My first reaction was flattery. My second was to ask whether query-time crawler traffic is actually a metric worth optimizing for. It isn’t.

## Two layers: web search vs. training data

In my [AEO playbook](https://zonted.com/posts/aeo-answer-engine-optimization/), I broke AI responses down into three layers: training data, validation search (RAG), and user memory. Meta’s crawler hitting our API sits in the *validation* layer — an agent fetching live JSON at inference time to verify a fact or patch a gap. That can win you a citation for a single user prompt, but it’s ephemeral. The model doesn’t update its weights from a runtime API call.

Training data is where presence compounds. When your dataset makes it into a pre-training or post-training corpus, your entities, comparisons, and brand associations get compiled directly into the model weights. Every prompt touching your domain over the next 12 to 18 months can surface your brand without firing a single web search.

## Why training data is a moat

Frontier training runs are massive capital events. Epoch AI estimates GPT-4.5’s training run at **~$340 million** and Grok 4’s at **~$390 million**. Rumors that Anthropic’s “Mythos” run cost $10 billion trace back to an unverified LinkedIn post, not Anthropic — though every serious estimate puts frontier pre-training firmly in the hundreds of millions.

![Google AI Overview for the query '10b mythos cost' stating the Anthropic Mythos model training cost is estimated around $10 billion, citing LinkedIn](https://img.zonted.com/resources/training-data-is-the-moat/mythos-ai-overview.png)

*Aside, too on-the-nose to skip: Google’s AI Overview happily quotes the $10B figure as fact, sourced from LinkedIn. Which is exactly the point — the AI layer propagates whatever made it into its pipeline, verified or not. Including about itself.*

Because those runs are so expensive, knowledge cutoffs lag 6 to 18 months behind release dates. Whatever makes it into a frontier training snapshot rides an 18-month distribution wave; whatever misses the cutoff is locked out until the next generation.

If your data only lives inside 3,000-word HTML blog posts wrapped in navbars and ad slots, you are gambling that Common Crawl or a lab crawler fetches your pages, strips the boilerplate cleanly, and doesn’t deduplicate your prose out of the training mix.

## The move: Hugging Face

![Recommendation text: Hugging Face dataset is the biggest lever. HF is where OpenAI, Meta, Anthropic, Mistral source training corpora. One upload equals broad reach, permanent citation, zero ongoing bandwidth cost.](https://img.zonted.com/resources/training-data-is-the-moat/hf-recommendation.png)

*The shortlist of non-API ways to serve the data. Hugging Face was #1 by a wide margin.*

Instead of waiting to be scraped, I packaged tabiji’s entire database and uploaded it directly to [Hugging Face](https://huggingface.co/datasets/tabiji/tabiji-travel-safety-guides). Data teams at OpenAI, Anthropic, Meta, and Mistral pull from Hugging Face daily. Uploading a clean, permissively licensed dataset hands ingestion pipelines pre-structured rows they don’t have to parse:

- **6,498 destinations** — climate, currency, language, plug type, tap-water safety, tipping norms, visa rules, and coordinates.
- **443 itineraries** — structured day-by-day schedules with logistics and timing.
- **396 city-level scam guides** — scam mechanics, prevention steps, and local emergency contacts (paired with our [733 AI-illustrated scam comics](https://zonted.com/posts/ai-comics-dos-donts/)).
- **250 countries**, **55 safety profiles**, **208 travel advisories** (US State Dept. + UK FCDO), and **949 head-to-head destination comparisons** with Reddit quotes and verdicts.

That’s 8,799 records in an 11.2 MB Parquet bundle under CC-BY-4.0, with explicit attribution fields pointing back to tabiji.ai and zero ongoing server cost.

Notice the split in serving format: tabiji.ai renders HTML articles for humans, while the Hugging Face repo ships typed Parquet rows for ingestion pipelines. Same underlying data, packaged for two different consumers.

## How I’ll know it worked

Attribution for pre-training data is still crude. I dropped a GA4 annotation on the upload date and will track two buckets:

- **Leading indicators:** Dataset downloads on Hugging Face, plus unprompted citations of tabiji.ai in ChatGPT, Claude, and Gemini responses on travel-safety queries.
- **Lagging indicators:** Brand recall in the next major Llama, Claude, and Gemini weight releases without web browsing enabled.

Check back in twelve months. In early-stage AEO, half the discipline is shipping the structured artifact and annotating the chart so you can measure the lag.

## The broader play

Hugging Face is the most direct pipe into training corpora, but the same principle applies everywhere data engineers source text:

- **Public GitHub repos** — JSON, CSV, and Markdown repos get ingested into code and reasoning datasets with high weight.
- **Wikipedia references** — where genuinely notable and verifiable, Wikipedia citations carry outsized weight in every frontier pre-training mix.
- **Reddit threads** — [explicitly licensed to Google for $60M/year](https://www.reuters.com/technology/artificial-intelligence/reddit-ai-training-deal-with-google-worth-60-million-per-year-source-says-2024-02-22/) and heavily upweighted across both pre-training and RAG.
- **Internet Archive snapshots** — feeds Common Crawl snapshots that underpin open-weight training sets.

If your entire content strategy is still publishing HTML for Googlebot, you’re fighting over a shrinking human click. Package your proprietary data in Parquet and JSON, license it for attribution, and put it where the training pipelines shop.
