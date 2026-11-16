---
title: "AEO Is Not SEO — Here's the Playbook"
author: "Bernard Huang"
date: "2026-04-15"
modified: "2026-04-15"
canonical: "https://zonted.com/posts/aeo-answer-engine-optimization/"
category: "AEO & Search"
description: "Traffic is declining and it's not coming back. The new game isn't ranking — it's influencing what AI says about you. Here's the AEO playbook I've been testing."
---

# AEO Is Not SEO — Here's the Playbook

By Bernard Huang · 2026-04-15 · 8 min read

Three years after ChatGPT launched, the search funnel has inverted. Google replaced ten blue links with AI Overviews; impressions in Search Console keep climbing while click-through rates slide. Informational queries get answered inline before a user ever visits a publisher. The game is no longer ranking #1 for a keyword — it’s controlling what the model says about your brand when it synthesizes the answer.

Google still claims that “good GEO is just good SEO.” On technical fundamentals, sure. On query targeting and attribution, they are completely different games. Here is the AEO (Answer Engine Optimization) playbook I’ve been running in production.

## TL;DR

AEO is not keyword SEO with a new coat of paint — it is intercepting the zero-volume fan-out queries that AI agents run during runtime RAG validation.

- **Target the validation layer** — Pre-training weights take 12–18 months to refresh; runtime web-search validation lets you win citations immediately.
- **Optimize for fan-out queries, not human search volume** — AI agents issue long, entity-dense verification queries (exposed via Google AI Studio grounding) that register zero monthly human searches.
- **Patch sentiment on cited URLs** — Audit which pages ChatGPT and Gemini cite, query the models for your brand’s perceived weaknesses, and address those exact objections on the cited pages.

[Embedded media](https://www.youtube.com/embed/2Ldce9z_ZuM)

*Video companion: the AEO playbook walkthrough.*

## Traffic Is Gone

Top-of-funnel organic traffic is in structural decline. AI Overviews answer simple queries directly on the SERP, and Google routes multi-constraint prompts (“plan a 3-day indoor family itinerary in Kyoto”) straight into AI Mode. The 20-year contract of trading content for ten-blue-link clicks is broken.

Executives are demanding an AEO strategy while still grading marketing teams on sessions and clicks. Conversational search doesn’t send discovery clicks the way keyword search did; it compresses the research funnel inside the chat window and only sends high-intent users at the end.

## The Three Layers of an AI Response

Every AI answer is assembled from three distinct layers:

### 1. Training Data

The pre-trained weights. Frontier models ingest web text, books, code, and Wikipedia up to a hard knowledge cutoff (for example, January 2025 on recent Gemini weights). Because frontier training runs cost hundreds of millions of dollars, there is a 6-to-18-month lag between publishing a page and seeing it reflected in base weights.

Winning in the base weights depends on classic **domain and topic authority** plus **entity co-occurrence** — how consistently your brand appears alongside the category terms you want to own across Reddit threads, G2, Capterra, Wikipedia, and industry press.

### 2. Research and Validation

Runtime RAG (Retrieval-Augmented Generation). Before answering a time-sensitive or specific prompt, the agent fires background web searches to verify facts, bridge the gap since its training cutoff, and suppress hallucinations.

That’s why ChatGPT or Gemini answers evergreen prompts from memory but triggers a live search the moment you ask about current pricing, API specs, or product comparisons.

### 3. Memory and Context

The user-specific context window: system instructions, past chat history, and saved user preferences. It shapes the final ranking but remains opaque to publishers.

## The Fastest Lever: The Validation Layer

Waiting 18 months for the next pre-training cutoff is not an operating strategy. The runtime validation layer is the lever you can pull today.

When an AI agent fires a background search to ground its answer, it retrieves the most entity-relevant, clearly structured documents it can find in milliseconds. **AEO is intercepting the agent during that validation fetch.**

## AI Web Searches Look Nothing Like Human Searches

Traditional SEO starts with human search volume: you pull Ahrefs or Semrush data, filter by monthly searches and keyword difficulty, and build hub-and-spoke clusters around what people type into a search bar.

In AEO, you target the synthetic queries that *LLMs generate* when decomposing a user’s prompt.

When a user asks an AI, *“How can I optimize content for SEO?”*, the model fans out into multiple background searches. Some look human (`SEO content optimization best practices`). Others look completely synthetic (`content quality and E-E-A-T in SEO`) — formal, entity-packed strings that show zero monthly search volume in keyword tools because no human types them.

That changes the ranking physics in three ways:

- **Zero-volume queries carry real traffic.** Traditional SEOs ignore these strings because keyword tools report zero volume, leaving the SERP wide open.
- **User click signals don’t exist.** Agents fetch the raw HTML or snippet without generating human dwell-time or pogo-sticking signals.
- **Entity density and semantic structure win.** Without behavioral click data, retrieval rankers fall back almost entirely on topical authority and explicit entity coverage.

## The AEO Playbook

### Step 1: Audit Your AI Topic Model

Prompt ChatGPT, Claude, and Gemini directly: *“What are the core topics, use cases, and competitors associated with [brand]?”* Compare the model’s mental map against the categories you actually want to own. The missing associations are your content roadmap.

### Step 2: Track Agent Fan-Out Queries (Not Just Keywords)

Run your target buyer prompts through Google AI Studio with Search Grounding enabled (or inspect the search payloads in Perplexity and ChatGPT). Extract the exact fan-out queries the model fires under the hood.

When an agent decomposes one prompt into five sub-queries, publishing dedicated, structured answers for all five sub-queries multiplies your probability of being cited in the synthesized response. Pair those fan-out strings with Google Autocomplete and “People Also Ask” trees to map the full question graph.

### Step 3: Publish Entity-Dense Validation Pages

Write pages engineered for retrieval parsers: clear definitions, comparison tables, explicit pricing, and unambiguous entity relationships that directly answer the agent’s fan-out queries.

### Step 4: Patch Sentiment on Cited Pages

Once your pages start earning citations in AI answers, close the feedback loop:

1. **Map which URLs get cited** across ChatGPT, Gemini, and Perplexity for your money prompts.
2. **Audit model sentiment:** ask the models what trade-offs, limitations, or complaints are associated with your product.
3. **Rebut those weaknesses directly on the cited URLs.** If Gemini tells buyers your tool is “expensive and overkill for small teams,” add an explicit FAQ or pricing tier breakdown on the exact page Gemini already retrieves for pricing queries.

Because runtime citations feed post-training evaluation sets, winning the validation layer today helps bake your framing into the next generation of model weights.

## How to Track AEO

Stop grading AEO on organic session growth. Track the pipeline in order of signal maturity:

1. **Search Console impressions on long-tail queries** — proof that retrieval bots are pulling your pages during query fan-out.
2. **Citation share** — how often your domain is linked as a source in AI responses across your tracked prompt set.
3. **Unprompted brand mentions** — how often the model recommends your product by name in category prompts.
4. **Branded search volume** — the lagging revenue indicator: buyers researching you in ChatGPT, then typing your brand name directly into Google to sign up.

In the AI-search era, raw informational traffic is a vanity metric. Branded search and direct signups are where the ROI lands.

## The Play

AEO right now looks like SEO in 2005: the synthetic fan-out queries that drive recommendations have almost zero intentional competition because legacy teams are still filtering their roadmaps by human search volume.

Audit what the models currently believe about your brand, extract the background queries they run when researching your category, publish entity-dense pages that answer those exact queries, and patch negative sentiment on the URLs the models already cite.
