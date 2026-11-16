---
title: "Why AI Slop Is Necessary"
author: "Bernard Huang"
date: "2026-03-18"
modified: "2026-03-18"
canonical: "https://zonted.com/posts/slop-iterate-curate-ai-content/"
category: "Production"
description: "The goal isn't to avoid AI slop — it's to slop on purpose, learn from what fails, and curate what works."
---

# Why AI Slop Is Necessary

By Bernard Huang · 2026-03-18 · 7 min read

Conventional wisdom on AI content is simple: don't make *slop*. Polish everything before you publish. Prioritize quality over quantity. That advice sounds responsible — and skips the most important stage of building an AI media pipeline.

Over six weeks, we scaled [tabiji.ai](https://tabiji.ai) from zero to 700+ destination pages, 386 local guides, 324 itineraries, an open API serving 1,428 JSON files, and 200+ short-form videos across Instagram, YouTube, and X (now shipping 21 videos a day across 10 active formats). None of it started good. **All of it started as deliberate slop.**

## TL;DR

When AI drops production cost to $0.30 per video, the fastest path to quality is shipping deliberate slop across 15+ formats, killing the losers in days, and enriching the winners into a moat.

- **R&D for $15** — Testing and killing 6 failed Instagram Reel formats cost ~$15 and a few hours of compute, versus $5,000 and three weeks for a traditional video team.
- **What actually won** — Aesthetic "POV" reels died at 9–134 views; high-utility formats like Scam Alerts (2,461 avg views) and Tourist Mistakes (865 avg views, 31 saves, 39 shares) scaled.
- **Slop → Iterate → Curate** — Version 1 of our written guides was pure LLM slop; Version 4 pairs Reddit quotes, live Google Places data across 3,755 venues, and JSON-LD schema.

## The Case for Deliberate Slop

In AI content production, **you cannot know what works until you ship what doesn't.**

Traditional content marketing front-loads planning — audience personas, algorithm teardowns, weeks of pre-production — because each asset costs $500 and two weeks of human labor. When AI drops marginal production cost to $0.30 per piece, that math inverts. Planning is expensive; shipping is cheap. Instead of theorizing in a doc, you ship 15 distinct formats, measure real retention and save rates, and kill the bottom 70%.

## The Graveyard: Formats We Killed

We tested over 15 Instagram Reel formats in a single month and killed most of them. Here is the graveyard, with screenshots from the actual axed posts:

[

![Killed format: natural attractions slideshow — Iceland Landmannalaugar](https://img.zonted.com/resources/slop-iterate-curate/killed-natural-attractions.png)
](https://www.instagram.com/p/DWAPOcnFdZm/) Natural Attractions Not interesting enough + copyrighted music   [

![Killed format: Vintage POV — Berlin 1961 Brandenburg Gate](https://img.zonted.com/resources/slop-iterate-curate/killed-vintage-pov.png)
](https://www.instagram.com/p/DV9wbdCDB1Q/) Vintage POV Not interesting enough   [

![Killed format: POV destination — Cappadocia hot air balloons](https://img.zonted.com/resources/slop-iterate-curate/killed-pov-destination.png)
](https://www.instagram.com/p/DVrqVgujwS-/) POV: Destination Too generic   [

![Killed format: Countries as Personalities — If Countries Were People in Your Friend Group](https://img.zonted.com/resources/slop-iterate-curate/killed-countries-as-personalities.png)
](https://www.instagram.com/p/DWFdgmQCoMY/) Countries as Personalities Not enough engagement   [

![Killed format: One thing you can't miss — Hanoi](https://img.zonted.com/resources/slop-iterate-curate/killed-one-thing.png)
](https://www.instagram.com/p/DVtLoCygdDQ/) One Thing You Can't Miss Too generic   [

![Killed format: Tourists vs Locals — Saigon Tân Định Market](https://img.zonted.com/resources/slop-iterate-curate/killed-tourists-vs-locals.png)
](https://www.instagram.com/p/DVv2JMDiu4b/) Tourists vs Locals Questionable attraction selection

Every one of these looked convincing in review: sunrise hot air balloons over Cappadocia, 1961 Berlin in 8mm grain, Iceland's highlands with clean typography. They all *looked* like winners — and proved that visual polish without a hook is a trap.

Killed — too generic

### "POV: Destination" & "One Thing You Can't Miss"

Clean footage and sharp text overlays, averaging a dismal 9–134 views with zero saves or shares. When a clip looks indistinguishable from every other travel account and offers zero concrete utility, it's just digital wallpaper.

Killed — aesthetics does not equal engagement

### "Vintage POV" & "Natural Attractions" Reels

8mm-style historical city footage stalled at 110–134 views, while Natural Attractions added copyright takedown risk from commercial audio. Pretty visuals without tension never trigger the saves and DM shares that drive Instagram distribution.

Killed — selection problem

### "Tourists vs Locals" Reels

Contrasting tourist traps with local haunts works in theory, but unenriched LLMs terrible at picking authentic local spots. Without Reddit-sourced ground truth, the "local" picks felt just as touristy as the traps.

Killed — not enough engagement

### "Countries as Personalities" Reels

"If Countries Were People in Your Friend Group" packed six country stereotypes into a single Ken Burns slideshow. Packing six reveals into one reel diluted the hook and tanked retention compared to single-tension formats.

At ~$0.30 and 4 minutes of compute per test clip, learning that all six formats were dead ends cost ~$15 in total R&D. A traditional social team would have burned $5,000 and three weeks to learn the exact same lesson.

## The Survivors: What Slop Taught Us

While the aesthetic formats flatlined, three utility-driven formats broke out immediately:

Scaled — 2,461 avg views

### "Scam Alert" Reels

Warning travelers about specific street scams by city became our #1 format. Loss aversion drives saves and shares: viewers bookmark them for upcoming trips and DM them to friends. One Paris bracelet scam Reel passed 3,100+ views on an account with under 500 followers.

Scaled — 865 avg views, best engagement

### "Tourist Mistake" Reels

"#1 Mistake Tourists Make in [City]" pairs the mistake clip with what locals do instead. That two-beat before/after arc drives our highest engagement ratio — 31 saves and 39 shares per Reel on average — and now runs 3x/day.

Evolved — 3 iterations deep

### "Budget Breakdown" Reels

"What $30/day gets you in Bangkok" started as a static image and evolved into a 5-clip stair-stepping sequence where each item costs more than the last before the final tally. It now runs 2x/day across a 50+ city queue.

## The Pattern: Slop Reveals Direction

Shipping 200+ videos exposed three rules we never would have guessed on a whiteboard:

1. **Utility beats aesthetics.** Viewers save a reel that spares them a $200 street scam; they scroll right past a pretty sunset. Saves and shares — not passive impressions — unlock algorithmic distribution.
2. **Specificity beats generality.** "Avoid tourist restaurants" gets ignored. "The string-bracelet scam on the Champs-Élysées steps" gets bookmarked. Real Reddit-sourced mechanics beat generic model advice every time.
3. **Structure beats pixel quality.** A two-clip before/after rendered on a $0.27 [MiniMax](https://platform.minimax.io/subscribe/token-plan?code=B8atrcvv5N&source=link) clip crushes a $4.50 cinematic [Veo 3](https://zonted.com/posts/veo3-vs-hailuo-minimax/) render with no narrative arc.

## The Same Pattern Holds for Written Content

Our written SEO and AEO guides followed the exact same trajectory. Version 1 of our popular-picks pages was pure LLM slop — clean, plausible "best restaurants in Tokyo" listicles that ranked for nothing. Shipping them revealed every missing layer:

- **Iteration 1:** Inject verbatim Reddit quotes with specific dishes, prices, and "what to order" callouts that models cannot hallucinate from weights.
- **Iteration 2:** Enrich every venue via the Google Places API — live star ratings, review counts, opening hours, and direct Maps links.
- **Iteration 3:** Embed JSON-LD structured data so Google surfaces rich star ratings directly in SERPs.
- **Iteration 4:** Publish a free static API exposing all 3,755 enriched venues so developers and external AI agents can query our dataset directly.

Within 30 days, those 166 popular-picks pages generated **837 Google impressions** across 26 indexed guides — with Ho Chi Minh rooftop bars (102 impressions, position 14.8), Le Marais cheap restaurants (96 impressions, position 10.7), and Marrakech street food (65 impressions, position 9.7) already pulling organic clicks. Version 1 was slop; Version 4 is a data moat.

## The Same Pattern, Again: AEO Content

Our early Answer Engine Optimization (AEO) articles were generic "Best AI Travel Planners" listicles that earned zero citations. Iterating in public showed us what answer engines actually cite:

- **Hard unit-cost receipts** ("$0.27/clip vs $4.50/clip") get cited because LLMs can't synthesize proprietary benchmarks from pre-training.
- **Embedded proof** (side-by-side video renders and billing screenshots) beats abstract commentary.
- **Head-to-head "X vs Y" comparisons** match both how humans search and how answer engines structure synthesis.

Over the last 30 days, 13 of our 50+ destination comparison pages generated **308 Google Search impressions** on queries like "greece vs italy" (59 impressions), "croatia vs montenegro" (40 impressions), "seoul vs tokyo" (30 impressions), and "vietnam vs philippines" (30 impressions), with several already on page one.

At the same time, answer engines became a measurable referral channel: **ChatGPT now sends 61 sessions per month** to tabiji.ai (our 5th largest traffic source, ahead of Pinterest and YouTube). Reddit referrals drive 86 sessions at a 35% bounce rate, while Pinterest's 17 sessions post a **12% bounce rate** — our stickiest cohort on the site.

## The Key Insight: Not "Don't Slop" — "Slop to Learn How Not to Slop"

Stop trying to skip the messy phase. The operator playbook is three steps:

1. **Slop.** Ship fast across 15 video formats, 10 article angles, and 5 content types. At $0.30 per asset, failed experiments are nearly free.
2. **Iterate.** Measure saves, shares, search impressions, and LLM citations. Kill dead formats in under two weeks; triple daily volume on winners like Tourist Mistake the day the signal appears.
3. **Curate.** Pour your real budget into the survivors — [API data enrichment](https://zonted.com/posts/true-cost-of-ai-content-production/), JSON-LD schemas, and ground-truth verification that turn raw generation into a defensible asset.

> Slop is not the enemy. Slop that stays slop is the enemy.

The operators winning with AI aren't the ones avoiding slop out of pride. They use cheap volume as a discovery sensor, kill losers without sentimentality, and compound their curation budget into the winners.
