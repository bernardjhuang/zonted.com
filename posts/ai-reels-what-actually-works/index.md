---
title: "AI Reels: What Actually Works"
author: "Bernard Huang"
date: "2026-03-11"
modified: "2026-03-11"
canonical: "https://zonted.com/posts/ai-reels-what-actually-works/"
category: "Production"
description: "We tested 100% AI-generated Instagram Reels, YouTube Shorts, and X posts using Veo 3, Nano Banana 2, and FFmpeg."
---

# AI Reels: What Actually Works

By Bernard Huang · 2026-03-11 · 14 min read

To grow [tabiji.ai](https://tabiji.ai/) without burning budget on studio production or paid social ads, we built a 100% autonomous short-form video pipeline. Cron jobs on a Mac Mini pull destinations from a queue, generate scripts and visuals via API, composite text overlays with FFmpeg, and publish directly to Instagram Reels, YouTube Shorts, and X — zero stock footage, zero human editors.

Here is the raw 48-hour dataset across 80+ published videos and 8 distinct Reel formats: which hooks broke 3,000+ views on a brand-new account, which formats wasted compute, and why the exact same video performs 27x differently depending on where you post it.

## TL;DR

Across 80+ autonomous AI travel Reels published in 48 hours (~$0.06–$0.12 per Reel), loss-aversion hooks ("Scam Alert" and "Tourist Mistake") hit 2,000–3,188 views while aesthetic "vibe" formats stalled under 150.

- **Fear and utility win on IG** — "Scam Alert" (Prague: 3,188 views) and "Tourist Mistake" (Koh Phi Phi: 2,175 views, 22 shares, 9 saves) dominated because viewers bookmark warnings for upcoming trips.
- **Platform split is 27x** — "Vintage POV" (1962 Paris 16mm style) died on Instagram (119 views, 0 saves) but hit a 1.7% like rate on YouTube Shorts (746 views, 13 likes); X cross-posts got 0–12 views.
- **Hook > pixels** — The same AI video models (Veo 3, Nano Banana 2, MiniMax) produce 100 views with a generic "One Thing You Can't Miss" hook and 3,000+ views with a specific scam warning.

## The Experiment

Our core product at [tabiji.ai](https://tabiji.ai/) builds personalized travel itineraries grounded in Reddit recommendations and real traveler data. To test organic social acquisition, we wired up cron jobs that run throughout the day: each job selects a city and format from our queue, renders the video end-to-end, publishes to Instagram, and cross-posts the file to YouTube Shorts and X.

Over a 48-hour window, we tested eight formats in live production:

- **Tourist Mistake** — "#1 Mistake Tourists Make in [City]"
- **Scam Alert** — "Every Tourist Falls for This Scam in [City]"
- **Vintage POV** — AI footage styled as 1960s–70s archival 16mm travel film
- **One Thing You Can't Miss** — "[City]'s Most Underrated Attraction"
- **This vs That** — "Tourists Go HERE, Locals Go HERE"
- **Budget Reel** — "What $50/Day Gets You in [City]"
- **POV** — First-person destination walkthroughs
- **Countdown / Top 5** — Top 5 things to do in a destination

## The Tech Stack

Every Reel is assembled without human intervention by chaining six tools:

- **Video generation:** [Veo 3](https://zonted.com/posts/veo3-vs-hailuo-minimax/) (Google DeepMind) — 8-second cinematic clips in 9:16 portrait
- **Image generation:** [Nano Banana 2](https://zonted.com/posts/ai-image-generation-comparison/) (Gemini 3.1 Flash) — base frames and still-image formats
- **Music:** [MiniMax](https://platform.minimax.io/subscribe/token-plan?code=B8atrcvv5N&source=link) — instrumental background tracks matched to destination mood
- **Text overlays:** FFmpeg — burns hooks, subtitles, and branding onto the video
- **Publishing:** Instagram Graph API → YouTube Data API → X API v2
- **Orchestration:** Shell scripts + cron jobs running on a local Mac Mini

Marginal API cost runs ~$0.06–$0.12 per Reel depending on the format. All the real engineering cost sits in the orchestration scripts and prompt templates.

## What's Working

### 1. Tourist Mistake — The Clear Winner

✅ Strong Performer

Consistently breaks 500+ views on IG, 700+ on YouTube. The format that generates the most saves and shares by far.

The "#1 Mistake Tourists Make in [City]" format outperformed everything else on save and share velocity:

| Reel | IG Views | IG Shares | IG Saves | YT Views |
| --- | --- | --- | --- | --- |
| #1 Mistake — Koh Phi Phi | 2,175 | 22 | 9 | 828 |
| #1 Mistake — Hoi An | 2,020 | — | 13 | 784 |
| #1 Mistake — Bangkok | 533 | — | — | — |

   2,175Peak IG Views 22Shares (Koh Phi Phi) 1.9%Engagement Rate 828Peak YT Views

[Embedded media](https://www.youtube.com/embed/E3fNepjCCdU)

On a cold account with almost zero followers, Koh Phi Phi posted a 1.9% save-plus-share rate (22 shares, 9 saves on 2,175 views), while Hoi An pulled 13 saves on 2,020 views. Viewers bookmark these warnings to reference before their trip and DM them to travel partners — and unlike most formats, Tourist Mistake works on both Instagram and YouTube Shorts simultaneously.

### 2. Scam Alert — IG's Biggest Number, Strong on YouTube

✅ Strong Performer

Prague hit 3,188 views — the highest single Reel we've published. Marrakech followed at 2,139. Strong on YouTube as well, essentially interchangeable with Tourist Mistake.

| Reel | IG Views | YT Views |
| --- | --- | --- |
| Scam Alert — Prague | 3,188 | 750 |
| Scam Alert — Marrakech | 2,139 | — |
| Scam Alert — Cairo | 180 | 846 |

[Embedded media](https://www.youtube.com/embed/EkhLYvs-dDY)

Prague Scam Alert is our single highest-reach Reel at 3,188 Instagram views (plus 750 on YouTube), while Cairo Scam Alert set our YouTube Shorts record at 846 views despite lagging at 180 on Instagram. Algorithmically, Scam Alert and Tourist Mistake tap the exact same loss-aversion reflex.

### 3. Vintage POV — YouTube's Sleeper Hit

📊 Platform-Dependent

Surprisingly strong on YouTube with the best engagement ratio of any format. Essentially dead on Instagram. Worth running — but YouTube-only.

| Reel | IG Views | YT Views | YT Likes | YT Comments |
| --- | --- | --- | --- | --- |
| Vintage POV — Paris 1962 | 119 | 746 | 13 | 1 |
| Vintage POV — Tokyo | 134 | 168 | — | — |
| Vintage POV — Kyoto | 110 | 60 | — | — |

[Embedded media](https://www.youtube.com/embed/lZDnB2sWvA8)

Paris 1962 exposes how sharply platform algorithms diverge. On Instagram, it died at 119 views, zero saves, and zero shares. On YouTube Shorts, the exact same 16mm-styled clip hit 746 views, 13 likes (a 1.7% like rate, our highest on YT), and a comment. YouTube's Shorts feed rewards full-clip watch time on nostalgic, atmospheric footage; Instagram's Reels feed demands actionable utility that triggers a save or DM share. Lesson: route Vintage POV exclusively to YouTube.

## What's Not Working

### 1. "One Thing You Can't Miss" — Weakest Format Overall

❌ Kill It

Every single Reel in this format is under 150 views. Zero saves across 6+ published Reels. Zero shares. We're pausing this format immediately.

| Reel | IG Views | Saves | Shares |
| --- | --- | --- | --- |
| One Thing — Hanoi #1 | 142 | 0 | 0 |
| One Thing — Hanoi #2 | 133 | 0 | 0 |
| One Thing — Hanoi #3 | 123 | 0 | 0 |
| One Thing — Hanoi #4 | 122 | 0 | 0 |
| One Thing — Hanoi #5 | 119 | 0 | 0 |
| One Thing — Hanoi #6 | 115 | 0 | 0 |
| One Thing — Hanoi #7 (newest) | 9 | 0 | 0 |

Two failures compounded here. First, "One Thing You Can't Miss" is a toothless hook with zero urgency or stakes. Second, our queue bug shipped seven Hanoi reels inside 48 hours, and the monotonic decay (142 → 133 → 123 → 122 → 119 → 115 → 9) shows Instagram suppressing repetitive topic clusters. We killed the format and enforced destination deduplication in the scheduler.

### 2. "This vs That" — The Conceptually Sound Failure

❌ Pause

The concept is solid. The execution — AI-generated video — can't deliver what the format promises. People want to see the contrast, not read about it.

| Reel | IG Views | Likes | Saves |
| --- | --- | --- | --- |
| This vs That — Saigon #1 | 132 | 1 | 0 |
| This vs That — Saigon #2 | 130 | 0 | 0 |
| This vs That — Saigon #3 | 127 | 0 | 0 |

"Tourists go to Ben Thanh Market; locals go to Binh Tay Market" is solid advice, but the format requires instant visual contrast between a chaotic tourist trap and an authentic local market. Current AI video generators flatten both prompts into similar-looking Southeast Asian market b-roll. When the text promises contrast and the pixels look interchangeable, viewers swipe.

### 3. Budget Reels — Useful but Forgettable

📊 Middling

115–131 views consistently. One save across four Reels total. People watch but don't save or share because there's no emotional hook — just information.

| Reel | IG Views | YT Views | Saves |
| --- | --- | --- | --- |
| Budget — Vienna ($50/day) | 117 | 2 | 0 |
| Budget — Leipzig ($40/day) | 117 | — | 0 |
| Budget — Ghent ($45/day) | 118 | 240 | 0 |
| Budget — Marseille ($50/day) | 131 | — | 1 |

Neutral daily-cost breakdowns ("Vienna on $50/day") get watched and immediately forgotten — 117–131 IG views and a single save across four reels. Without a loss-aversion hook or a multi-clip escalation arc, cost facts alone don't trigger bookmarks (though Ghent hit 240 views on YouTube Shorts).

### 4. Generic POV — Don't Bother

❌ Dead Format

Cappadocia: 116 views, 0 likes, 0 saves, 0 shares. A format with no differentiation gets no algorithm love.

An unhooked first-person glide over Cappadocia hot air balloons pulled 116 views and zero engagement. Cold algorithmic feeds do not distribute "pretty vibes" from unknown accounts.

## Platform-by-Platform Breakdown

Posting identical files simultaneously to three networks exposed how differently each recommendation engine scores short-form video.

### Instagram: Fear and Utility Win

Instagram's Reels algorithm weights **saves and DM shares** far above passive completion rate. Negative-framed utility (scams, mistakes, warnings) gives viewers a concrete reason to bookmark a post for a future trip or forward it to a friend.

| Format | IG Performance | Saves/Shares |
| --- | --- | --- |
| Scam Alert | 2,139–3,188 views | High |
| Tourist Mistake | 533–2,175 views | High |
| Budget | 117–131 views | Minimal |
| Vintage POV | 110–134 views | Zero |
| One Thing | 9–142 views | Zero |
| This vs That | 127–132 views | Zero |
| Generic POV | 116 views | Zero |

### YouTube Shorts: The Algorithm Rewards Nostalgia and Information

YouTube Shorts weights **average percentage viewed** much more heavily than saves. If viewers hold through an 8-second clip, YouTube keeps pushing it — which is why Scam Alert and Tourist Mistake (750–846 views) perform alongside nostalgic 16mm Vintage POV clips like Paris 1962 (746 views, 13 likes).

### X/Twitter: Basically Zero

On X, automated video cross-posting to a fresh account was a complete zero:

| Platform | Typical Range | Best Result | Likes |
| --- | --- | --- | --- |
| X (@tabijiai) | 0–12 views | 12 views | 0 |

The exact same videos hitting 2,000–3,188 views on Instagram got 0–12 impressions on X (@tabijiai). Unlike Instagram Reels and YouTube Shorts, which test cold uploads against interest graphs regardless of follower count, X does not distribute native video from zero-follower accounts without reply-guy distribution or paid boosts.

## The Psychology Behind the Hooks

Every winning format in our dataset exploits three behavioral mechanics:

### Negative Framing Outperforms Positive Framing

"The #1 Mistake Tourists Make in Koh Phi Phi" beat "One Thing You Can't Miss in Hanoi" by more than 15x. Travelers can find "top attractions" anywhere; avoiding an embarrassing or expensive mistake requires specific local knowledge. Loss aversion stops the scroll.

### Saves Signal Trip Planning Intent

On Instagram, a save is deferred action: *"I'm not in Koh Phi Phi today, but I need this before I land."* For a travel product like tabiji, saves are a direct proxy for high-intent trip planners rather than passive armchair scrollers.

### Specificity Creates Credibility

"Mistakes tourists make in Thailand" sounds like generic blog spam. "The #1 Mistake Tourists Make in Koh Phi Phi" signals narrow local expertise, earning trust in the first 1.5 seconds even when the underlying script is synthesized from aggregated Reddit threads.

### Fear > Curiosity > Information > Inspiration

Ranked by cold-account distribution across our 80-video sample:

1. **Fear** (scams, mistakes, warnings) — highest reach, highest save/share rate
2. **Curiosity** (secrets, underrated spots) — moderate reach, low saves
3. **Information** (daily budgets, logistics) — watched passively, rarely bookmarked
4. **Inspiration** (cinematic walkthroughs, nostalgia) — dead on IG, viable on YouTube Shorts

## Where We Go From Here

### Scale What's Working

- **Tourist Mistake and Scam Alert:** Increase cron cadence and expand the destination queue globally.
- **Vintage POV (YouTube-only):** Strip it from the Instagram cross-poster and run it as a dedicated YouTube Shorts format.

### Kill What Isn't

- **"One Thing You Can't Miss":** Retired permanently, alongside a hard destination-cooldown rule in the queue.
- **"This vs That":** Paused until our image-to-video pipeline can enforce unmistakable visual contrast between tourist and local scenes.
- **Generic POV:** Killed.

### Open Questions

- Does Tourist Mistake hold its 2,000+ view baseline in tier-2 cities, or is it carried by high-volume hubs like Koh Phi Phi and Hoi An?
- Can we rescue Budget Reels by reframing them around loss aversion (e.g., "How Tourists Get Ripped Off on $50/Day in Vienna")?
- Can Vintage POV work on Instagram if we pair the 16mm aesthetic with a tactical warning overlay?

## What This Means for AI-Generated Content

### AI Video Still Struggles With Side-by-Side Visual Contrast

Our "This vs That" flop highlights a real model limitation: prompting Veo 3 for a "crowded tourist market" vs. an "authentic local market" yields two clips with nearly identical lighting, camera motion, and crowd density. Without human curation or reference-image grounding, text-to-video models regress toward a visual mean that blurs side-by-side comparisons.

### Platform-Native Routing Beats Blind Cross-Posting

We built the pipeline assuming "render once, publish everywhere" was free leverage. Paris 1962 proved otherwise: a format that thrives on YouTube watch-time mechanics can tank your account's engagement ratio on Instagram. Routing formats by platform algorithm is a one-line config change that prevents dead-on-arrival uploads.

> The best performing AI content isn't the most beautiful or the most creative — it's the most useful, packaged with the right emotional trigger.

Shipping 80+ Reels across 8 formats in 48 hours cost less than $10 in total API spend — an A/B testing velocity that would have taken a traditional social agency months and thousands of dollars to run.
