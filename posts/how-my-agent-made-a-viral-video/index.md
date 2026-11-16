---
title: "How My Agent Produced a 3.9M-View Viral Video"
author: "Bernard Huang"
date: "2026-05-31"
modified: "2026-05-31"
canonical: "https://zonted.com/posts/how-my-agent-made-a-viral-video/"
category: "Production"
description: "Teardown of one autonomous AI video: the Tulum spare-tire scam reel that hit 3.9M views — real queue JSON, exact Seedance prompt, FFmpeg overlay code."
---

# How My Agent Produced a 3.9M-View Viral Video

By Bernard Huang · 2026-05-31 · 5 min read

## TL;DR

One JSON scam concept goes into a queue. An autonomous pipeline turns it into a documentary-style reel and publishes it to four platforms. This run hit 3.9 million views.

- **The reel:** The **Tulum spare-tire rental scam** — **3,943,661 views**, 100% from non-followers, 986 shares. Zero cameras, actors, or human editors.
- **The pipeline:** Queue JSON → Seedance prompt → WaveSpeed video generation → FFmpeg dynamic text overlay → multi-platform fan-out.
- **Why it survived as a cron:** WaveSpeed exposes a real, authenticated REST API — unlike the brittle wrapper hacks that [killed Kapiko](https://zonted.com/posts/kapiko-postmortem/).
- **The bigger picture:** How the channel reached [18 million views in 90 days](https://zonted.com/posts/tabiji-18m-views/) is the companion post; this is the anatomy of a single breakout reel.

## The video

This is a ten-second clip of a couple at a Cancun airport rental counter, a pushy agent fixated on the spare tire, and — days later — a different employee claiming the tire is gone while reaching for a card machine. It is a real scam. None of it was filmed. The footage, the people, the garage, and the luggage carts are all generated.

> [View this reel on Instagram](https://www.instagram.com/p/DXRxyemE8Bs/)

Here are the Instagram insights from that single run:

![Instagram insights for the Tulum spare-tire scam reel: 3,943,661 views, 100% non-followers, 1,847,095 accounts reached, 2,622 likes, 406 comments, 518 saves, 986 shares, 5,265 accounts engaged.](https://img.zonted.com/resources/how-my-agent-made-a-viral-video/reel-insights.jpg)

*3,943,661 views, 100% non-followers, 1.85M accounts reached — and 986 shares against 518 saves and 2,622 likes.*

Two numbers matter more than the view count. First, **100% non-followers** — pure cold algorithmic distribution. Second, **986 shares**, outnumbering the 518 saves and running unusually high against 2,622 likes. Viewers didn’t just double-tap this clip; they DM’d it to the friend flying to Mexico next month.

## The pipeline, in one line

One agent skill runs five steps end-to-end with no human in the loop:

**concept (JSON) → documentary prompt → WaveSpeed Seedance clip → FFmpeg overlay → publish to four platforms.**

The reason this pipeline runs reliably on a cron is that [WaveSpeed](https://wavespeed.ai/?ref=zonted) exposes a real, authenticated API. Unlike the unofficial Suno wrappers that [killed Kapiko](https://zonted.com/posts/kapiko-postmortem/), nothing here is reverse-engineered or breaking every 36 hours. The API key lives in the macOS Keychain, the request is a standard POST, and the job runs unattended.

## Step 1: the concept is data, not a script

Every reel starts as a structured queue item — a compact JSON object defining the city, the setup, the camera blocking, and the five lower-third story beats:

data/queue.json — the Tulum item

```
{
"id": "tulum-car-rental-spare-tire-scam",
"destination": "Tulum",
"country": "Mexico",
"scam_name": "Spare Tire Rental Scam",
"location_context": "At Cancun Airport rental counters feeding Tulum
road trips, inside bright garages and return lanes packed with carts.",
"concept": "The pickup agent makes a big show of the spare tire, then at
return another employee claims it is missing and charges hundreds.",
"prompt_anchors": ["airport rental garage", "open trunk",
"spare tire close-up", "clipboard inspection",
"different employee at return", "credit card machine"],
"tourist_blocking": "A couple stands at the open trunk as the pickup agent
points hard at the spare tire and tools like it matters most.",
"scammer_blocking": "Days later, a different employee at return bends into
the same trunk, straightens up, and announces the spare is gone.",
"beats": [
"Pickup fixates on the spare tire",
"The trunk gets extra attention",
"Return day feels routine at first",
"Then the tire is suddenly missing",
"The charge hits before you can react"
],
"hashtags": ["tulum", "mexico", "travelscam", "rentalcar",
"sparetire", "travelsafety", "cancunairport", "tabiji"]
}
```

The concept isn’t invented; it’s transcribed from an upvoted travel-scam thread where a tourist got burned and wrote down the details. As I covered in the [account-level post](https://zonted.com/posts/tabiji-18m-views/), mining Reddit means starting with validated demand. The `beats` array does the heavy lifting: those five lines become the lower-third captions and follow a deliberate threat-then-fix arc.

## Step 2: concept → documentary prompt

Next, `generate_prompt.py` flattens that JSON into a single Seedance prompt — stitching the setting, opening visual, character blocking, reveal, and visual anchors into one paragraph, capped with a fixed clause enforcing handheld documentary realism:

Generated Seedance prompt

```
Photorealistic documentary-style travel footage in Tulum, Mexico. At
Cancun Airport rental counters feeding Tulum road trips, inside bright
garages and return lanes packed with luggage carts. A bright rental
garage hums with rolling suitcases, cars pulling out, and staff guiding
tired arrivals into inspection lanes. A couple stands at the open trunk
as the pickup agent points hard at the spare tire and tools like it
matters more than anything else. Days later, a different employee at
return bends into the same trunk, straightens up, and announces the
spare is gone while holding a payment terminal. [...] Visual anchors to
preserve: airport rental garage, open trunk, spare tire close-up,
clipboard inspection, different employee at return, credit card machine.
Natural handheld camera movement, subtle zoom or push-in only when it
helps the social tension, realistic pacing, overlapping background
motion, authentic tourist behavior, grounded travel realism, no
stylization, no subtitles, no on-screen text.
```

Two rules do quiet work here. First, **“no subtitles, no on-screen text”** — video models mangle text and immediately break the documentary illusion, so all typography is burned in later via FFmpeg. Second, the script runs a string-replacement pass so scam prompts clear Seedance’s safety filter without losing the physical action:

generate_prompt.py — moderation softening

```
replacements = {
' aggressive ':   ' pressuring ',
' aggressively ': ' insistently ',
' threatens ':    ' warns about ',
' threat ':       ' warning ',
' extortion ':    ' fake fine ',
}
```

“Pressuring” renders the exact same body language as “aggressive” while sailing past moderation.

## Step 3: generate the clip

The prompt goes to WaveSpeed running ByteDance’s Seedance 2.0 (vertical 9:16, ten seconds, 480p):

run_queue_item.py — submit to WaveSpeed

```
BASE  = 'https://api.wavespeed.ai/api/v3'
MODEL = 'bytedance/seedance-2.0/text-to-video'

payload = {
'prompt': prompt,
'duration': 10,
'aspect_ratio': '9:16',
'resolution': '480p',
}
# POST, then poll /predictions/{id}/result every 8s until the
# status flips to completed, then stream the mp4 to disk.
```

Each generation costs $0.30 to $2 depending on duration and resolution. Once the raw 480p vertical MP4 lands on disk, it moves to the only step that renders human-readable text.

## Step 4: burn the overlay

Every piece of text on screen — the country flag, the crimson headline, and the five sequential beats — is burned in after generation with FFmpeg. Rather than assuming a fixed canvas, `render_overlay.py` inspects the actual frame with `ffprobe`, then dynamically wraps and shrinks the font until every line fits inside safe margins:

render_overlay.py — measure, wrap, fit

```
# measured from the actual rendered frame, not a fixed 1080x1920
max_headline_width = int(w * 0.78)
max_beat_width     = int(w * 0.76)

def fit_wrapped(text, font_path, start_size, max_width, max_lines, min_size):
size = start_size
while size >= min_size:
lines = wrap_text(text, font((font_path, size)), max_width)
if len(lines) <= max_lines:
return size, lines
size = max(min_size, math.floor(size * 0.92))  # shrink 8%, retry
return min_size, wrap_text(text, font((font_path, min_size)), max_width)
```

The five beats reveal in sequence across the ten-second clip — one lower-third caption at a time, fading in over a translucent black box, with the final beat rendered in crimson:

render_overlay.py — beat timing

```
beat_start = 0.9
segment = max(1.1, (duration - beat_start) / max(len(beats), 1))
# beat i appears at beat_start + i*segment, behind a translucent
# black box, drawn with an alpha ramp so it fades in cleanly.
```

The output is the finished vertical MP4 embedded above — untouched by human hands.

## Step 5: publish everywhere at once

Next, `build_config.py` turns the queue item into platform-specific captions. The Instagram caption reuses the five story beats, adds a two-line explanation of the psychological hook, and closes with the *“Save this”* prompt:

build_config.py — generated Instagram caption

```
The Spare Tire Rental Scam in Tulum, Mexico 🇲🇽

Pickup fixates on the spare tire
The trunk gets extra attention
Return day feels routine at first
Then the tire is suddenly missing
The charge hits before you can react

The spare tire rental scam works by making the trunk part of the
story from the beginning, so the final accusation feels pre-scripted.

Save this before your next trip. 📌

#tulum #mexico #travelscam #rentalcar #sparetire #travelsafety
#cancunairport #tabiji
```

Finally, `publish-video.py` handles the fan-out: it stages the file in temporary storage, publishes the Instagram Reel, uploads the YouTube Short, posts the Facebook Reel, pushes to TikTok, extracts a 1-second thumbnail for each, and cleans up. On this run, Instagram, YouTube, and TikTok succeeded immediately; Facebook hit a rate limit and queued for retry.

## Why this one hit 3.9 million

The pipeline ships a reel like this every day. Most do fine; this one detonated. Look at the engagement ratios again: **986 shares, 518 saves, 2,622 likes**. On typical reels, likes dwarf everything else. Here, shares topped a third of total likes and nearly doubled saves — the unmistakable signature of a warning people forward to a friend.

A named scam at a specific airport counter creates an obligation to warn anyone you know flying to Cancun or Tulum. The five on-screen beats establish the trap in ten seconds, and the caption provides the defense. Because Instagram heavily weights DM shares when testing a reel on cold audiences, those 986 shares propelled a tiny account’s video to 1.85 million strangers.

## The takeaway

A structured JSON object entered a queue and came out the other side with 3.9 million views, with zero human editing in between. The production line is solved. What automation doesn’t solve is predicting which concept will detonate and which will stall at 4,000 views.

The machine renders the video. Picking the right raw material — and keeping the queue fed — is the job. One in fifty hits 3.9 million. The pipeline’s job is making the other forty-nine cost a dollar each.
