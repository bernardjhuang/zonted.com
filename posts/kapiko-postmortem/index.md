---
title: "Kapiko: a 10-day, $150 post-mortem"
author: "Bernard Huang"
date: "2026-05-30"
modified: "2026-05-30"
canonical: "https://zonted.com/posts/kapiko-postmortem/"
category: "Post-Mortems"
description: "Kapiko, an AI ambient-music YouTube channel, shipped in 10 days for ~$150. The pipeline worked; the Suno API does not exist. The autopsy, and what's reusable."
---

# Kapiko: a 10-day, $150 post-mortem

By Bernard Huang · 2026-05-30 · 5 min read

## TL;DR

AI music generation is solved; the moat is distribution and a real API, not track quality.

- **The build:** Shipped [Kapiko](https://kapiko.ai) — an autonomous ambient-music channel starring a capybara in headphones — end-to-end in 10 days for ~$150.
- **The scoreboard:** 57 YouTube videos, 3 subscribers, a 49-view top video, and 4 monthly Spotify listeners.
- **What killed it:** Suno has no public API. Every Suno automation pipeline reverse-engineers a web app whose auth and captcha flows break every 36 hours.
- **What survives:** The taste-filter engine — generating 50–100 candidates per run and having Gemini grade each MP3 against genre masterpieces before shipping only 9/10s.

## How Kapiko started

Three subscribers. Fifty-seven videos. Four monthly Spotify listeners. The pipeline worked. The audience did not arrive.

![The kapiko YouTube channel page showing 3 subscribers and 57 videos, with the capybara-in-headphones avatar.](https://img.zonted.com/resources/kapiko-postmortem/kapiko-channel.jpg)

*Three subscribers. One of them is me. Top video: 49 views, also probably me.*

The idea started on a long drive with Spotify’s Peaceful Piano playlist on shuffle — hours of Einaudi, Yiruma, and Tiersen. When I got home, the obvious question hit me: this is the exact sonic lane Suno nails.

I had just [benchmarked every AI music generator](https://zonted.com/posts/ai-music-generation-comparison/) — Suno, Udio, MiniMax Music — and Suno won outright. So the question wasn’t *can AI generate solo piano?* It was *can one operator with a taste filter run an autonomous music label?*

Kapiko was the ten-day, ~$150 test: a capybara in over-ear headphones (*“A capybara, a pair of headphones, and nowhere to be. Solo instruments. Gentle melodies.”*), a site at [kapiko.ai](https://kapiko.ai) ($80/yr domain), YouTube at `@kapiko-music`, DistroKid ($23/yr), a month of Suno Pro (~$10), plus Gemini, Nano Banana, and MiniMax tokens running on OpenClaw crons.

The tracks shipped to Spotify and Apple Music with AI-generated titles like *Whispers of November’s End*, *Porch Light Love*, and *Moonlit Petals Drift* — better names than I would have come up with myself.

![The kapiko Spotify artist page showing 4 monthly listeners and the top tracks: Whispers of November's End, Glimpse Through Frosted Pa..., Porch Light Love, Sunset's Gentle Invitation, Moonlit Petals Drift.](https://img.zonted.com/resources/kapiko-postmortem/spotify-kapiko.jpg)

*The other side of the receipts: kapiko on Spotify, 4 monthly listeners.*

## How the system worked

Kapiko operated like a one-person A&R scout: generate in bulk, grade against human masterpieces, and throw away 90% of the output.

### Step 1: pick a genre, write the prompts

We started with solo piano (neo-classical, jazz ballad, ambient, Japanese, lo-fi, classical nocturne), expanded to fingerstyle guitar, and queued handpan next. Each run generated 25–50 Suno prompts specifying recording texture, emotional direction, playing technique, tempo, and room feel. Human artist anchors shaped the prompt generator internally — Einaudi for piano; Don Ross, Andy McKee, and Lance Allen for guitar — without ever appearing in the prompt text, since Suno blocks named-artist strings.

### Step 2: generate the candidates

Prompts hit Suno v5 (`chirp-crow`) through a custom web wrapper that polled for completion, downloaded MP3s, and used NopeCHA to clear hCaptcha challenges. Because Suno returns two clips per prompt, each run produced 50–100 candidate tracks alongside a manifest logging the prompt, model version, timestamps, and file hashes.

### Step 3: score against the masterpieces

Raw AI music has a high variance problem. To filter out the slop, I uploaded every candidate MP3 to Gemini alongside human reference tracks.

**Piano** used Einaudi’s “Nuvole Bianche,” Yiruma’s “River Flows in You,” and Tiersen’s “Comptine d’un autre été” as the gold standard across five dimensions:

- **Playlist fit:** Would it sit on Spotify’s Peaceful Piano without triggering a skip?
- **Closest reference:** Which master track does it resemble, and why?
- **Quality gap:** What breaks if you play it immediately after the reference?
- **Production match:** Piano tone realism, room reverb, dynamic range, loudness, and digital artifacts.
- **Emotional authenticity:** Does the phrasing feel performed by a human or assembled by a grid?

Each track received a PASS, BORDERLINE, or FAIL verdict, weighted heavily toward playlist fit and production realism.

**Guitar** used a strict 8-dimension written rubric instead of reference MP3s — catching wrong-instrument hallucinations and penalizing full-band drift, vocals, drums, or synth leakage. Across 80 guitar clips, 21 scored 9/10 and 36 scored 8/10 (a 71% hit rate at 8+), performing best in percussive, flamenco, baroque, and Middle Eastern fusion while struggling in lullaby and post-rock, where Suno kept sneaking in full bands.

**Handpan** referenced Hang Massive (“Once Again”), Yuki Koshimoto, and Daniel Waples (“Hang in Balance”), graded across seven dimensions including resonance, rhythmic flow, and instrument authenticity.

Anything below 9/10 was deleted. Ties went to head-to-head re-grading until one winner per genre remained.

### Step 4: package the winner

Gemini listened to the winning MP3 and extracted mood, landscape, season, time of day, and color palette. Nano Banana rendered a 1920×1080 illustration of the capybara in that setting. Gemini then wrote a MiniMax image-to-video prompt with one strict constraint: locked camera, ambient motion only (drifting clouds, rippling water, swaying grass). FFmpeg looped the 6-second video to match the MP3 runtime, muxed the audio, burned in the title and Kapiko wordmark in Pacifico, and exported the final MP4.

### Step 5: distribute

YouTube uploads ran automatically via the official Data API under `kapiko-youtube-refresh-token` with the title format `“Song Name [Single - Solo Piano] - kapiko”`. DistroKid handled Spotify and Apple Music distribution manually.

## How Kapiko scored as a fully AI autonomous business

Barrier to entryLOW Low barrier sounds good. It is not. Suno plus a video model and anyone can ship. The same low barrier that lets me play lets every new operator compound on top of me weekly.   Channel durabilityHIGH YouTube as a surface will take years for AI to consume. Video is the slowest substrate to be replaced.   Market sizeHIGH YouTube keeps growing. Ambient and functional audio is a durable, multi-billion-hour annual demand pool.   Product durabilityHIGH Once a track ships, it’s evergreen. The fireplace clip is still earning a decade in.   GTM / marketingHIGH High *effort*, not high leverage. You have to grind for subscribers. This is where it’s hard.   Business modelMEDIUM 1,000 subscribers to enter the creator program. Pennies per view until a sticky niche locks in.

Every project I build (Tabiji, Veracity, Kapiko) gets graded on the same six-cell scorecard so I don’t fall in love with whichever pipeline I’m currently wiring up. AI collapsed the cost of generation, not distribution. Three cells here are green, two are red, and one is amber — and the two reds tell the same story: when the barrier to entry is near zero, distribution is the entire job. The rubric warned me before I wrote a line of code; I underweighted it because building the music-scouting engine was fun.

## The genre is real

Channel durability and market size aren’t hypothetical. Ambient and functional audio on YouTube and Spotify has been a quietly massive category for over a decade — four examples show the range:

**Trainers Warehouse meeting chime** — 161K views over 17 years, played in corporate workshops to call rooms back from break. Utility audio outlasts almost everything else on the platform.

![YouTube video of the Trainers Warehouse Meeting Chime sound, 161K views over 17 years.](https://img.zonted.com/resources/kapiko-postmortem/meeting-chime.jpg)

*Functional audio: 17 years old, still earning its keep one workshop at a time.*

**Complex’s 10-hour fireplace clip** — *Fireplace 10 hours full HD*, 156M+ views and reportedly $1M+ in ad revenue over a decade from a single upload.

![Reddit r/passive_income post about Complex's 10-hour YouTube fireplace video reportedly earning the creator over $1 million.](https://img.zonted.com/resources/kapiko-postmortem/fireplace-reddit.jpg)

*One upload, ten years, reportedly $1M+. The category has receipts.*

**Relax My Dog** — *15 HOURS of Deep Separation Anxiety Music for Dog Relaxation*, 66M+ views. Pet-calming audio is an entire economy I never would have guessed existed.

![YouTube search results for dog separation anxiety music; top result has 66 million views.](https://img.zonted.com/resources/kapiko-postmortem/dog-anxiety-music.jpg)

*Animal-calming audio: an entire sub-niche I’d never have surfaced without looking.*

And **Lofi Girl** — the category anchor at 15.8M subscribers across 407 videos.

![Lofi Girl YouTube channel header showing 15.8M subscribers and 407 videos.](https://img.zonted.com/resources/kapiko-postmortem/lofi-girl.jpg)

*Lofi Girl: the genre’s anchor tenant.*

Patient operators in functional audio do very well over multi-year horizons. So why did I pull the plug after ten days?

## Cause of death

Two things killed Kapiko: a brittle wrapper that made true cron automation impossible, and a distribution grind I wasn’t willing to do by hand.

Suno has no official API. Every automated Suno project reverse-engineers their web app, and that wrapper broke every 24 to 48 hours: auth tokens rotated, hCaptcha triggers shifted, endpoints moved, JSON schemas changed by a single field. On Saturday morning of week two, an auth change 401’d every download in flight. I patched it before coffee. It broke again Sunday night.

> You cannot cron a business that needs babysitting every 36 hours.

When anyone can spin up a competitor in a weekend, the only viable operating model is an unattended daily cron. Once you’re babysitting broken scrapers every other day, you aren’t running an autonomous system — you’re working a part-time ops job for four Spotify listeners.

Even if the wrapper had held, the distribution grind was waiting. In a zero-barrier category, getting discovered takes months of playlist pitching, shorts seeding, and community grinding. The brittle wrapper made me stop; the marketing grind would have made me stop anyway.

## What’s reusable

The music channel died, but the taste-filter engine underneath it survives.

What I actually built is a domain-agnostic quality loop: generate 50–100 candidates, grade each one against genre-defining human references using a multimodal model, and discard everything below 9/10. Point that same loop at recipe-blog photography with *Bon Appétit* and *Eater* feature spreads as the reference set, and it works the same way. Models improve every quarter; the grading rubric is the asset you keep.

## Next

Ten days and $150 bought a clean answer: yes, an AI pipeline can scout and package release-grade solo instrumentals; no, you can’t run it as a hands-off cron while the Suno API is a fiction. I’m taking the reference-grading loop to [the next surface](https://zonted.com/posts/ai-music-generation-comparison/) — where the API is real.
