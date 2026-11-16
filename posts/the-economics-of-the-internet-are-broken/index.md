---
title: "The Economics of the Internet Are Broken"
author: "Bernard Huang"
date: "2026-03-19"
modified: "2026-03-19"
canonical: "https://zonted.com/posts/the-economics-of-the-internet-are-broken/"
category: "AI Agents & Systems"
description: "AI agents killed the publisher incentive model the same way streaming killed the 99-cent MP3."
---

# The Economics of the Internet Are Broken

By Bernard Huang · 2026-03-19 · 8 min read

In 2003, buying a song on iTunes for 99 cents felt like the permanent future of music. Artists recorded tracks, Apple distributed them, you paid a dollar, and the unit economics worked for everyone.

Then Spotify offered every song ever recorded for $10 a month. Overnight, the 99-cent MP3 became a relic — not because music changed, but because the cost of distribution and access repriced the entire industry. **The exact same repricing is hitting the entire ad-supported internet right now.**

## TL;DR

AI agents broke the 25-year publisher bargain from both ends: answer engines intercept search traffic while autonomous pipelines collapse content production costs by ~99%.

- **The $0.30 unit cost** — Producing an 8-second Instagram Reel now costs $0.30, a 3,000-word travel itinerary costs $0.15, and a full day of 23 videos plus cross-posts runs ~$17 (~$500/month total).
- **Volume beats paid promotion** — Paying $50 to boost a $0.30 video is 167x the production cost; making 167 videos for $50 and letting organic algorithms pick the winners wins on expected reach.
- **What survives Era 3** — Purely informational ad-supported sites become training data; durable businesses need proprietary first-party data, direct audience channels, or transactional APIs priced for agents.

## The Deal That Held the Internet Together

For 25 years, the open web ran on a four-step bargain:

1. Publishers create content (articles, videos, guides, reviews)
2. Search engines index it and send referral traffic
3. Publishers monetize those sessions with display ads or affiliate links
4. Advertisers fund the ecosystem because human eyeballs convert

That bargain produced plenty of SEO spam and clickbait, but the flywheel worked: useful content earned traffic, and traffic paid for production. AI agents just snapped the flywheel in half.

## The Traffic That Stopped Coming

When someone asks ChatGPT or Perplexity for the "best restaurants in Barcelona," the model doesn't send ten clicks to ten travel blogs. It synthesizes the answer directly in the chat window. The query is satisfied; the publisher gets zero sessions.

Even inside traditional search, Google's AI Overviews resolve informational queries before the user ever scrolls to an organic link, dropping publisher click-through rates by double digits across travel, finance, health, and tech. And that traffic isn't coming back, because **users prefer the new experience.** Getting a clean, immediate synthesis beats clicking through three ad-bloated recipe or travel blogs to find one factual paragraph.

## The Production Cost Collapse

While referral traffic dries up on the demand side, an even bigger shock is hitting the supply side: **the marginal cost of producing media just fell by 99%.**

Here is what it actually costs us to produce content with four AI agents on a Mac Mini in March 2026:

| Content Type | AI Cost | Traditional Cost | Reduction |
| --- | --- | --- | --- |
| Instagram Reel (8 sec, fully produced) | $0.30 | $200–500 | ~99% |
| Travel itinerary page (3,000 words + maps) | $0.15 | $300–800 | ~99% |
| Original music track (full composition + publish) | $0.31 | $500–2,000 | ~99% |
| Curated local guide (10 places, rated + verified) | $0.50 | $400–1,200 | ~99% |
| Full day of content (23 videos + cross-posts) | ~$17 | $5,000–15,000 | ~99% |

Those aren't theoretical projections. Our four agents publish 23 videos a day across Instagram, YouTube, X, and Pinterest while maintaining over 1,400 pages of travel content for roughly $500 a month in total compute and API spend. When a finished video costs $0.30, every legacy assumption about media economics breaks.

## Why Paying to Promote a $0.30 Video Makes No Sense

In the traditional social playbook, a brand spends $300 to produce an Instagram Reel and another $50 to $500 boosting it with paid ads. Spending $500 to distribute a $300 asset is rational math.

When that Reel costs $0.30 to generate, **paying $50 to boost it is absurd.** You're spending 167x the production cost on paid distribution — the equivalent of paying $167 in postage to mail someone a dollar bill.

When production costs approach zero, the rational strategy flips to **volume over promotion.** Instead of producing one video and spending $50 to boost it, generate 167 videos for that same $50 and let the platform algorithms test every single one organically. Most will stall at 100 views. Several will hit 1,000. A few will break out past 10,000+. Your total reach is higher, your spend is identical, and you own a compounding library of 167 assets instead of a single expired ad campaign.

We run this exact playbook daily: 23 Reels published every 24 hours, $0 in paid ad spend, and compounding weekly reach driven purely by algorithmic surface area.

> When production costs approach zero, the optimal strategy inverts: produce more, promote less. Volume becomes the distribution strategy.

## Three Eras of Internet Economics

### Era 1: Purchase

Buy the content.
99 cents per song.
$15 per article (magazine).
Unit economics worked.

### Era 2: Attention

Content is free.
You pay with attention (ads).
Traffic = revenue.
SEO era.

### Era 3: Synthetic

Content is AI-generated.
Near-zero production cost.
Traffic model broken.
We are here.

Each transition shifted the locus of leverage. Era 1 rewarded labels and publishers that controlled physical production. Era 2 rewarded platforms that aggregated attention and search intent. Era 3 rewards **operators with the best agent pipelines and the sharpest editorial taste**, because production and organic distribution have collapsed into the same loop.

## What Happens to Publishers

Publishers built entirely on "write informational articles, rank on Google, sell display ads" are facing an extinction event. Their business model depended on two premises that no longer hold:

1. **Search engines will send referral traffic.** Answer engines now resolve the query upstream.
2. **Content production is expensive enough to act as a moat.** An agent pipeline can replicate a week of commodity editorial research in 90 seconds.

The publishers that survive Era 3 will own at least one of three defensible assets:

- **Proprietary first-party data.** Verified user reviews, live pricing, and ground-truth local telemetry that an LLM cannot hallucinate from static training weights.
- **Direct audience relationships.** Email newsletters, private communities, and native apps that bypass search and social intermediaries entirely.
- **Transactional execution.** If your platform completes a booking, purchase, or verified action, agents still have to route through you. If you only publish commodity text, you're free training data.

## What Happens to Advertising

The $600 billion digital ad industry assumes that human attention can be interrupted while browsing a page. In an agentic web, browsing is intermediated: an AI agent fetches the page, extracts the structured facts, and returns a clean synthesis to the user. The human never loads the DOM, and the display ad impression never fires. You cannot sell banner CPMs to a headless scraper.

Advertising won't vanish, but it will migrate upstream into the AI layer itself: sponsored placements inside answer engines, paid agent integrations, and licensed data partnerships where brands pay to sit inside the retrieval pipeline. The era of "rank a blog post and monetize with programmatic display ads" is the new 99-cent MP3.

## The Weird Place We're In Right Now

We are living in the lag between technological reality and industry habit. Legacy publishers are still tweaking H2 tags for Google crawlers. Brands are still burning budgets boosting single social posts. Ad networks are still selling display CPMs as if humans will keep clicking ten blue links forever.

Meanwhile, a single Mac Mini running four agents is shipping more daily media than a mid-sized publishing company, reaching hundreds of thousands of viewers a month on $0 of paid distribution. Arbitrage gaps that wide don't stay open forever — when the market reprices, operators already running Era 3 infrastructure will have a multi-year lead.

## So What Replaces It?

Four structural shifts are already replacing the legacy ad-and-search model:

1. **Per-call data monetization replaces pageviews.** Instead of monetizing human eyeballs with banner ads, publishers will monetize verified, real-time data — pricing, availability, ground-truth reviews — via APIs billed per agent query.
2. **Volume economics replace paid promotion.** Winning distribution means building agent pipelines that ship high-taste variations at scale and letting algorithmic feeds surface the outliers.
3. **Taste becomes the primary moat.** When execution costs $0.30, editorial judgment — knowing *what* to make and which 3% of outputs deserve to ship — is the only scarce input left.
4. **Owned channels become mandatory.** Email lists, direct communities, and native tools are the only distribution pipes an upstream AI layer can't silently intercept.

## The iTunes Lesson

When Spotify launched, record labels sued and insisted the 99-cent download model had to be protected. The industry didn't die — it restructured. Artists and operators who built for streaming economics early captured the new market, while holdouts waiting for iTunes downloads to rebound got wiped out.

The web is in its Spotify transition right now. No amount of SEO tweaking or paid social spend will bring back the old publisher flywheel.

> The cost of producing content just hit $0.30. The cost of distributing it is heading toward zero. Every business model built on content being expensive and traffic being free is about to get repriced.

We're building for the new math: autonomous agents, $0.30 unit costs, strict editorial curation, and organic volume over paid promotion. So far, the numbers aren't even close.
