---
title: "The Three Unlocks Behind 18M Views of AI Travel Content"
author: "Bernard Huang"
date: "2026-05-31"
modified: "2026-05-31"
canonical: "https://zonted.com/posts/tabiji-18m-views/"
category: "Production"
description: "Tabiji got 18,117,121 views in 90 days, 98.6% from strangers. The unlocks: Reddit as demand oracle, warming accounts to read human, one hired human."
---

# The Three Unlocks Behind 18M Views of AI Travel Content

By Bernard Huang · 2026-05-31 · 5 min read

## TL;DR

We automated everything except the part that had to look human.

- **The channel:** Tabiji is an AI travel-safety channel. One agent turns a tourist-scam concept into a documentary-style reel and ships it to Instagram, TikTok, YouTube, and Facebook — no camera, no crew, no filmed footage.
- **The numbers:** **18,117,121 views in 90 days** and 6.15M accounts reached (up 141,413.5%), with 98.6% coming from non-followers.
- **The three unlocks:** Mining Reddit as a demand oracle, warming accounts so they pass bot-farm filters, and hiring one human contractor to do manual following and liking from a real phone.
- **The economics:** Clips cost ~$0.30–$2 to generate, platform ad share pays almost nothing, and 76% of followers are over 45 — the exact demographic that buys our Kindle travel-safety books.

## The receipt

Tabiji is a travel-safety channel built on a single premise: name a specific tourist scam in a specific city, then show how to beat it. None of it is filmed. A scam concept enters a priority queue, an agent generates a documentary-style vertical video, FFmpeg burns on a country flag, headline, and five story beats, and a script publishes it across four platforms untouched.

Over the last 90 days, the Instagram account hit **18,117,121 views** and reached 6,154,422 accounts (up 141,413.5%) across 1,083 posts, growing to 5,017 followers with a bio funneling into our Kindle books:

![Instagram Views insights for Tabiji, last 90 days (Mar 2 - May 30): 18,117,121 views, 0.0% from ads, 1.4% from followers and 98.6% from non-followers, 6,154,422 accounts reached up 141,413.5%.](https://img.zonted.com/resources/tabiji-18m-views/ig-views-90d.jpg)

*90 days, zero ad spend: 18,117,121 views, 6.15M accounts reached (up 141,413.5%), 98.6% of it to non-followers.*

Everyone fixates on the 18 million. The number that actually explains the channel is **98.6%** — the share of views delivered to people who don’t follow Tabiji. This was never a follower graph. It was the algorithm handing a cold warning to a stranger eighteen million times. Three unlocks made that happen.

## Unlock 1: Reddit is a demand oracle

Treating ideation as a creative step is a mistake. We don’t invent scam concepts — we transcribe them. Every reel starts as a heavily upvoted thread on r/travel, r/solotravel, or a country subreddit where a traveler got burned and wrote down the play-by-play. An upvoted scam thread is a completed market test: real money lost, a real victim, and thousands of travelers voting that the story hit home.

Specificity is the moat. A Reddit thread doesn’t say “watch out for scams in Mexico.” It says the pickup agent at the Cancun rental counter makes a show of pointing out the spare tire, and at return a different employee claims it’s missing and bills you hundreds. That became a [real reel we ran](https://zonted.com/posts/how-my-agent-made-a-viral-video/) — it hit 3.9 million views, with the hook and receipts already proven before we spent a cent on video generation. Generic safety advice is commodity content nobody saves; a named scam at a named counter gets bookmarked. And the underlying anxiety is massive: consumers reported losing [$2.1 billion to scams originating on social media in 2025](https://www.ftc.gov/news-events/news/press-releases/2026/04/new-ftc-data-show-people-have-lost-billions-social-media-scams), an eightfold jump since 2020.

One craft rule took us weeks to learn: a threat without a defense underperforms. Pure shock clips get scrolled past. What gets shared is *threat, then counter-move* — show the trap vividly, then hand the viewer the one sentence or photo that shuts it down. That’s why every caption ends with “save this before your next trip.” The save is the product.

## Unlock 2: a new account is guilty until proven human

Spin up a fresh account, post a great video, and nothing happens. TikTok states plainly that [every new video is first shown to a small test audience](https://support.tiktok.com/en/using-tiktok/exploring-videos/how-tiktok-recommends-content) regardless of follower count, expanding only if retention and engagement clear an internal bar. A cold account with zero history starts in the smallest possible bucket.

For an automated pipeline, the real danger isn’t newness — it’s bot-farm pattern matching. Naive automation walks in wearing the uniform: bursty actions, mechanical intervals, a fresh device on a datacenter IP, a profile 100% completed in thirty seconds, and a bio link on day one. Platform enforcement is ruthless: in 2025 alone, YouTube terminated [more than 12 million channels](https://blog.youtube/), mostly bulk spam networks.

Separate what’s documented from practitioner folklore: the small-test-audience cold start is published fact, while rigid “like 5–8 videos, follow 2–6, wait seven days” recipes are mostly proxy-seller superstition. The real rule is negative and simple: don’t drop bio links on day one, don’t run a fleet off one device fingerprint, and don’t spike action velocity. Which leads directly to the part we refused to automate.

## Unlock 3: we hired a human to do the un-automatable part

The content is 100% automated. The engagement is 100% manual.

What pushed our Instagram reach over the line wasn’t a better video prompt. On [Rebecca’s](https://zonted.com/games/run-to-rebecca/) recommendation, we hired a contractor whose entire job is the boring human work: following niche travel accounts, liking real posts, and unfollowing — from a physical phone at a human pace. Automated engagement is the exact signature that gets an account shadowbanned. The one signal a platform classifier can’t easily flag is an actual human thumb.

We let an agent generate the footage, write the copy, pick the thumbnail, and publish across four platforms untouched — then paid a person to tap “Follow” and “Like.” We automated the expensive creative work and hired a human for the cheap repetitive work: the exact inversion of what everyone predicted AI would do.

## The machine

The production pipeline is narrow and opinionated. A scam concept — city, setup, scammer move, tourist reaction — turns into a documentary-style visual prompt and goes to [WaveSpeed](https://wavespeed.ai/?ref=zonted) running ByteDance’s Seedance 2.0 text-to-video: ten seconds, vertical, 480p, zero on-screen text. We never let the video model render text; garbled letters immediately break documentary realism.

Once the raw clip returns, FFmpeg measures the frame and burns in the country flag, a two-line headline, and five timed lower-third story beats. A single publish script pushes the finished reel to Instagram Reels, YouTube Shorts, TikTok, and Facebook with platform-specific captions and thumbnails. (When Seedance’s moderation rejects a scam prompt, the agent automatically softens the wording without losing the physical mechanics and retries.)

It isn’t free. A single Seedance generation on WaveSpeed runs $0.30 to $2 depending on duration, resolution, and how many clips you stitch together, plus LLM tokens for scripting and metadata. At roughly a dollar a reel, 1,083 posts is a four-figure generation bill — before counting the duds.

And the quality bar is a moving target. The prompt style that nailed handheld realism last month looks over-stylized this month; the hook pacing that held viewers in March gets swiped past in May; an overlay that looked sharp at launch looks generic once ten copycats clone it. Cheap video generation lowered the cost of footage. It did nothing to lower the cost of taste.

## What 18 million views is actually worth

In direct platform payouts, almost nothing. Instagram’s old Reels Play bonus fund is dead. The surviving ad-revenue share pays roughly [$0.01–$0.10 per thousand views](https://influencermarketinghub.com/instagram-reels-monetization/) — one creator reported $24 for 241,000 views. At that rate, 18 million views pays $180 to $1,800, or zero if the account isn’t enrolled. Buying those same 18M impressions via ads would cost a brand $90k–$450k, but you can’t pay server bills with theoretical media value.

Meanwhile, 18 million views converted into just 5,017 followers — about 0.03%. That’s how the 2026 short-form feed works: viewers watch the clip, the algorithm serves another, and nobody visits the profile. Reach is abundant; a reason to follow is scarce.

Look at *who* followed, though, and the picture changes:

Followers by age · last 90 days 13–170.1% 18–241.1% 25–347.8% 35–4415.0% 45–5422.4% 55–6428.1% 65+25.5% **76% of the audience is over 45. Over half is 55+.** Gender splits almost evenly — 49.6% men, 50.4% women.

That is not a random crowd. Older travelers lose the most money to these scams, forward warnings to spouses and siblings, and buy books that promise to keep them safe. The algorithm didn’t just hand the reels to strangers — it routed them to the exact demographic our product serves. The audience targeting we never configured turned out to be the sharpest part of the funnel.

> An organic view is worth exactly what you capture off-platform before the algorithm moves on.

That’s why the only line on the profile that matters is the bio link to [tabiji.ai/books](https://tabiji.ai/books/). Views are rented. Email addresses and book sales are owned. Reach is the demo; the funnel is the business.

![The Tabiji Instagram profile: tabiji.ai, owl avatar, Travel Safety & Tips, 1,083 posts, 5,017 followers, 202 following, bio linking to tourist scam books at tabiji.ai/books.](https://img.zonted.com/resources/tabiji-18m-views/ig-profile.jpg)

*5,017 followers off 18 million views — and the one link in the bio that turns rented reach into something owned.*

## The takeaway

Tabiji is one probe in a larger thesis: an autonomous content business a single operator can run on a cron. The generation half works today — Reddit supplies validated demand, Seedance renders the footage, FFmpeg dresses the frame, and one script ships it everywhere. The distribution half is where humans still live. New accounts are guilty until proven human, and the cheapest way to prove it is an actual person.

Automate the part that looks like work. Keep a human on the part that has to look like a person.
