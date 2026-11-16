---
title: "Suno vs MiniMax Music: Which AI Composer Wins?"
author: "Bernard Huang"
date: "2026-03-11"
modified: "2026-03-11"
canonical: "https://zonted.com/posts/ai-music-generation-comparison/"
category: "Comparisons"
description: "We tested Suno AI and MiniMax Music 2.0/2.5/2.5+ in production across 200+ Instagram Reels."
---

# Suno vs MiniMax Music: Which AI Composer Wins?

By Bernard Huang · 2026-03-11 · 21 min read

We ship 4–10 [Instagram Reels](https://zonted.com/posts/ai-reels-what-actually-works/) and YouTube Shorts a day at [tabiji.ai](https://tabiji.ai/), and every single one needs background music. Licensed tracks are impossible to automate at scale, and a 20-track royalty-free folder gets repetitive after a week. So we tested two AI music generators in production: **[MiniMax Music API](https://platform.minimax.io/subscribe/token-plan?code=B8atrcvv5N&source=link)** (models 2.0, 2.5, and 2.5+) and **Suno AI** (via a reverse-engineered API), plus a **Gemini 2.5 Flash audio scorer** to evaluate the outputs. Every sample below is a raw production artifact.

## TL;DR

Suno makes the best AI music (8.5/10) with no official API, while MiniMax Music 2.5+ makes reliable instrumental background tracks (7/10) via a documented REST API for ~$0.01/track.

- **Daily production (MiniMax 2.5+)** — The only MiniMax model where `is_instrumental: true` actually works; generates 60–192s tracks at ~$0.01/track with 99%+ uptime.
- **Quality showcase (Suno AI)** — `chirp-crow` (v5) delivers genuine solo piano dynamics (~$0.02/clip on a $10/mo Pro plan), but requires a reverse-engineered Clerk JWT wrapper.
- **AI music scoring (Gemini 2.5 Flash)** — Reliable for binary audio checks and instrument detection, but too polite to rank tracks (every clip scored 44–47/50).

## Why AI Music for Travel Content?

When you're producing 4–10 short-form videos per day through automated cron pipelines, your audio options narrow fast:

- **Licensed music** — expensive at scale, rights management nightmare, impossible to automate selection.
- **Royalty-free libraries** — free or cheap, but your audience hears the same 20 tracks on repeat after a week.
- **AI-generated music** — unique per video, ~$0.01/track, programmable via API, infinite mood variety.

What started as "just add background music to Reels" turned into testing three MiniMax models, reverse-engineering Suno's undocumented bird-codename endpoints, and building a Gemini audio critic.

## [MiniMax Music](https://platform.minimax.io/subscribe/token-plan?code=B8atrcvv5N&source=link): The Production Workhorse

MiniMax exposes three music models through its REST API. They look similar on paper, but only one actually works for instrumental background music.

| Feature | Music 2.0 | Music 2.5 | Music 2.5+ |
| --- | --- | --- | --- |
| **Model ID** | music-2.0 | music-2.5 | music-2.5+ |
| **Cost per track** | ~$0.01 | ~$0.01 | ~$0.01 |
| **Requires lyrics** | Yes (always) | Yes (always) | No (optional) |
| **is_instrumental** | Not supported | Broken (error) | Works perfectly |
| **Output duration** | 20–65s | 20–50s | 60–192s |
| **Vocal tendency** | Always vocal | Usually vocal | Pure instrumental |
| **Quality (travel bgm)** | 5/10 | 6/10 | 8/10 |
| **Our usage** | Retro/vocal vibes | Don't use | All production |

### Music 2.0 — Vocals Whether You Want Them or Not

The original MiniMax music model **always requires a lyrics field** and ignores `is_instrumental: true`. Passing placeholder lyrics like `"la la la"` yields a wordless sung melody layered over the beat. It has charm for dreamy retro clips, but vocalizations clash with voiceovers and text-heavy Reels.

### Music 2.5 — The Broken Middle Child

Slightly better mix than 2.0, but passing `is_instrumental: true` throws `2013: invalid params, lyrics is required`. You still have to pass lyrics and you still get vocals. Skip it.

### Music 2.5+ — The One That Works

The only MiniMax model where `is_instrumental: true` produces **pure instrumental music** with zero humming. Instrumentation is richer, stereo separation is wider, and tracks run 60–192s—giving plenty of source material to trim down to 12-second Reel beds. This runs all of our daily production.

## MiniMax Audio Tests

### Test 1: Warm Cinematic Travel

**Prompt:** "warm cinematic travel background music, acoustic guitar and soft piano, golden hour sunset vibes, dreamy and nostalgic"

Same prompt across all three models. Music 2.0 and 2.5 received placeholder lyrics (`"la la la"`); Music 2.5+ used `is_instrumental: true`.

🎧 Prompt 1: Warm Cinematic Travel  Music 2.0 — "la la la" placeholder lyrics Vocal

[Media](https://img.zonted.com/resources/ai-music-generation-comparison/samples/minimax-2.0-warm.mp3)
Music 2.5 — "la la la" placeholder lyrics Vocal

[Media](https://img.zonted.com/resources/ai-music-generation-comparison/samples/minimax-2.5-warm.mp3)
Music 2.5+ — is_instrumental: true Instrumental ✓

[Media](https://img.zonted.com/resources/ai-music-generation-comparison/samples/minimax-2.5-plus-warm.mp3)

Music 2.0 and 2.5 turn `"la la la"` into a lead vocal melody. Only Music 2.5+ delivers a clean instrumental bed that sits underneath video without competing for attention.

### Test 2: Japanese Festival Energy

**Prompt:** "upbeat Japanese festival drums and shamisen, energetic travel montage, fast tempo"

🥁 Prompt 2: Japanese Festival Drums  Music 2.0 — "la la la" placeholder lyrics Vocal

[Media](https://img.zonted.com/resources/ai-music-generation-comparison/samples/minimax-2.0-festival.mp3)
Music 2.5 — "la la la" placeholder lyrics Vocal

[Media](https://img.zonted.com/resources/ai-music-generation-comparison/samples/minimax-2.5-festival.mp3)
Music 2.5+ — is_instrumental: true Instrumental ✓

[Media](https://img.zonted.com/resources/ai-music-generation-comparison/samples/minimax-2.5-plus-festival.mp3)

Notice the **duration** gap: Music 2.0 and 2.5 generated ~20-second clips, while Music 2.5+ generated ~100 seconds—five times more material to slice an 8–15 second segment from.

### Test 3: Vintage Kyoto (Real Production Sample)

**Prompt:** "Lo-fi ambient, Rhodes piano, shakuhachi flute, vinyl crackle, tape hiss, 65 BPM, no drums"

🎬 Production Sample: Vintage Kyoto Reel  Music 2.0 — from our vintage Kyoto Reel Vocal

[Media](https://zonted.com/posts/ai-music-generation-comparison/vintage-kyoto-music-2.0.mp3)

Even when explicitly prompted for lo-fi ambient instruments, Music 2.0 layers vocals on top. Music 2.5+ solved background audio for Reels—but when we wanted standalone solo piano pieces that sound like a real Steinway session, we turned to Suno.

## Enter Suno: The Quality King

**Suno AI** produces arrangements, phrasing, and emotional dynamics that rival human recordings. We wanted Suno for standalone solo piano covers and ambient travel pieces—tracks people actually listen to on their own, not just hear buried at -18dB under a Reel.

There was one catch: **Suno has no public API.** So we reverse-engineered it.

## How We Reverse-Engineered Suno's API

If you just want to hear the tracks, [skip to the Suno Audio Showcase](#suno-showcase).

### The Architecture

We run a local Next.js wrapper (`suno-api/`) around Suno's internal endpoints:

Browser Cookie → Clerk Session → JWT Token → Suno Internal API → Audio URL

The wrapper includes a Playwright-based hCaptcha solver backed by [2Captcha](https://2captcha.com) (~$3 balance) for when Suno challenges automated requests.

### The Night Everything Broke

On March 13, 2026 at 9:38 PM, our piano cover pipeline died. Suno had shipped a web UI redesign that broke every Playwright selector:

| Old Selector | New Selector | Why It Broke |
| --- | --- | --- |
| `.custom-textarea` | `textarea:visible` | CSS class removed entirely. Hidden lyrics textarea required `:visible` filter. |
| `button[aria-label="Create"]` | `button.filter({hasText: 'Create'})` | aria-label removed from the button. |
| `waitUntil: 'domcontentloaded'` | `waitUntil: 'networkidle'` | React SPA fires domcontentloaded before rendering anything. Page shows a loading spinner. |

### The Plot Twist: Captcha Wasn't Even Required

After updating the selectors and adding debug screenshots, we checked Suno's captcha check endpoint (`/api/c/check`): it returned `required: false`.

The entire Playwright dance—launching Chromium, navigating to `suno.com/create`, locating the textarea, solving hCaptcha—was unnecessary. **Direct HTTP calls with the Clerk JWT token worked on their own.** Our broken DOM selectors had been timing out *before* the script even checked if a captcha was needed.

### The Bird Codename Mystery

Next wall: model selection. Passing `chirp-v5`, `v5`, or `chirp-v4-5` all returned `403 Forbidden`. Through midnight trial and error, we found that **Suno uses internal bird codenames** for its v4.5+ models:

| Bird Name | Version | Quality | Notes |
| --- | --- | --- | --- |
| `chirp-crow` | v5 | Best | Pro default, highest quality |
| `chirp-bluejay` | v4.5+ | Very good |  |
| `chirp-auk` | v4.5 | Good |  |
| `chirp-v4` | v4 | Solid | Older but reliable |
| `chirp-v3-5` | v3.5 | Legacy |  |

### Other Suno API Gotchas

- **No artist names in prompts.** "Solo piano cover of Cruel Summer by Taylor Swift" is rejected immediately. "Solo piano cover of Cruel Summer" works. Describe the style without naming the artist.
- **Prompt limit:** 500 characters for `gpt_description_prompt` on v5 (not 200 as older guides claim).
- **Each generation = 2 clips = 10 credits.** The $10/mo Pro Plan includes 2,500 credits (250 generations = 500 clips) with commercial rights.
- **Use `wait_audio: false` + polling.** Blocking mode (`wait_audio: true`) times out after 100 seconds. Fire-and-forget, then poll `/api/get?ids=X,Y`.

## The Cruel Summer Experiment

To test Suno's expressive range and build an automated quality filter, we generated 10 solo piano covers of "Cruel Summer" on `chirp-v4` (instrumental mode) across 5 mood variations—costing 50 credits ($0.20):

> "Solo piano cover of Cruel Summer. Steinway grand piano, close-miked. [MOOD]. [DYNAMICS]. Warm intimate recording."

| # | Strategy | Mood Modifier | Clips |
| --- | --- | --- | --- |
| 1 | **Balanced** | Bittersweet longing, hushed verses building to powerful chorus | 2 |
| 2 | **Melancholic** | Minor key reharmonization, wistful and sad | 2 |
| 3 | **Bright** | Bright uplifting, flowing arpeggios, shimmering upper register | 2 |
| 4 | **Sparse** | Minimal, lots of space between notes, ambient contemplative | 2 |
| 5 | **Virtuosic** | Fast runs, ornamental flourishes, concert-style performance | 2 |

## Gemini as AI Music Critic

We wrote `scripts/gemini-piano-scorer.py` to upload each MP3 to **Gemini 2.5 Flash** and score it 1–10 across five criteria, plus two binary checks (is it actually solo piano? is the melody recognizable?):

Emotional Impact/10 Piano Tone Quality/10 Arrangement/10 Spotify Playlist Fit/10 Replay Value/10

### The Results

All 10 clips passed both binary checks. Then we looked at the numerical scores:

| Variation | Clip | Emotion | Tone | Arrangement | Playlist | Replay | Total |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Balanced | A | 9 | 9 | 9 | 9 | 9 | 45/50 |
| Balanced | B | 9 | 9 | 8 | 9 | 9 | 44/50 |
| Melancholic | A | 9 | 9 | 9 | 9 | 8 | 44/50 |
| **Melancholic** | **B** | **9** | **9** | **9** | **10** | **9** | **46/50** |
| Bright | A | 9 | 9 | 8 | 9 | 9 | 44/50 |
| Bright | B | 8 | 9 | 9 | 9 | 9 | 44/50 |
| Sparse | A | 9 | 9 | 9 | 9 | 9 | 45/50 |
| **Sparse** | **B** | **9** | **10** | **9** | **10** | **9** | **47/50** |
| **Virtuosic** | **A** | **9** | **9** | **10** | **9** | **9** | **46/50** |
| Virtuosic | B | 9 | 9 | 9 | 9 | 8 | 44/50 |

**Top 3:** Sparse (B) at 47/50, Melancholic (B) and Virtuosic (A) tied at 46/50. Restraint and space scored slightly higher than flashy runs.

### The Problem: Gemini Is Too Nice

Every single clip scored between 44 and 47 out of 50, with no individual score below 8. In reality, a human listener could rank them immediately: some had clunky transitions, others meandered, and one lost the melody mid-bridge. Gemini graded all of them like a polite professor at an undergraduate recital. When every track gets 8–9/10, point scoring is useless for ranking.

### How to Fix AI Music Scoring

- **Adversarial scoring:** "Find 3 specific flaws in this performance. Be harsh."
- **Pairwise comparison:** "Listen to both clips. Which is better and why?"
- **Reference-based scoring:** Upload the original track alongside the cover to anchor melodic accuracy.
- **Calibrated rubric:** Anchor the scale ("10/10 is Oscar Peterson live; 5/10 is a first-year student").

### 💡 Key Insight: AI Can Analyze Audio, But Can't Rank It

Gemini 2.5 Flash accurately identifies instruments, key signatures, tempo, and arrangement style. Its *analysis* is sharp; its *point evaluation* is uselessly compressed. We now use Gemini strictly as a binary **filter** (verify instrumentation and reject broken renders) and leave final selection to human ears.

### The Scorer Code

```
import google.generativeai as genai
import json, sys

genai.configure(api_key="YOUR_GEMINI_API_KEY")

def score_piano_cover(mp3_path):
"""Upload MP3 to Gemini 2.5 Flash, score on 5 criteria."""
audio = genai.upload_file(mp3_path)
model = genai.GenerativeModel("gemini-2.5-flash-preview-05-20")

prompt = """Analyze this solo piano cover. Score each criterion 1-10:
    1. Emotional Impact - Does it evoke feeling?
    2. Piano Tone Quality - Realistic, warm, well-recorded?
    3. Arrangement Sophistication - Creative reinterpretation?
    4. Spotify Playlist Fit - Would it fit "peaceful piano"?
    5. Replay Value - Would you listen again?

Also: Is this actually solo piano? (yes/no)
Is the original melody recognizable? (yes/no)

Return JSON: {"scores": {"emotion": N, "tone": N,
"arrangement": N, "playlist_fit": N, "replay": N},
"solo_piano": bool, "melody_recognizable": bool,
"total": N, "notes": "brief explanation"}"""

response = model.generate_content([prompt, audio])
return json.loads(response.text.strip("```json\n").strip("```"))

if __name__ == "__main__":
result = score_piano_cover(sys.argv[1])
print(json.dumps(result, indent=2))
```

## Suno Audio Showcase

Here are raw Suno outputs from our production runs: two favorite piano covers, the winning "Cruel Summer" experiment clip (`chirp-v4`), and five original compositions on `chirp-crow` (v5).

🎹 Suno Piano Covers  Piano Cover #1 — Yiruma-style, warm and intimate Suno

[Media](https://img.zonted.com/resources/ai-music-generation-comparison/samples/suno-piano-cover-1.mp3)
Piano Cover #2 — Emotional, reflective Suno

[Media](https://img.zonted.com/resources/ai-music-generation-comparison/samples/suno-piano-cover-2.mp3)
Cruel Summer — Solo piano cover (experiment clip) Suno v4

[Media](https://img.zonted.com/resources/ai-music-generation-comparison/samples/suno-cruel-summer-piano.mp3)
🎵 Suno v5 Original Compositions (chirp-crow)  Morning Mist — Solo piano, dawn atmosphere Suno v5

[Media](https://img.zonted.com/resources/ai-music-generation-comparison/samples/suno-morning-mist.mp3)
Snowfall Nocturne — Solo piano, winter night Suno v5

[Media](https://img.zonted.com/resources/ai-music-generation-comparison/samples/suno-snowfall-nocturne.mp3)
Candlelight Waltz — Solo piano, warm 3/4 time Suno v5

[Media](https://img.zonted.com/resources/ai-music-generation-comparison/samples/suno-candlelight-waltz.mp3)
Coastal Reverie — Solo piano, ocean-inspired Suno v5

[Media](https://img.zonted.com/resources/ai-music-generation-comparison/samples/suno-coastal-reverie.mp3)
Paper Lanterns — Solo piano, East Asian influence Suno v5

[Media](https://img.zonted.com/resources/ai-music-generation-comparison/samples/suno-paper-lanterns.mp3)

Play these back-to-back with the MiniMax samples above. MiniMax sounds like polished MIDI; Suno's `chirp-crow` captures natural sustain, pedal noise, and human velocity dynamics.

## Native Video Audio: Veo 3, CogVideoX, Hailuo

Before building a dedicated music pipeline, we tested whether video generation models could supply their own usable audio:

- **Google [Veo 3](https://zonted.com/posts/veo3-vs-hailuo-minimax/) (`generate_audio`)** — Generates synchronized ambient SFX (street noise, wind, footsteps), not composed background music. We disable it for most Reels.
- **[Z.AI](https://z.ai/subscribe?ic=JY9V1BN5ZO) CogVideoX-3** — Advertises AI SFX audio, but outputs synthetic, low-bitrate noise (2/10). Never used in production.
- **MiniMax Hailuo I2V** — Ships completely silent, which is why we pair it with MiniMax Music 2.5+ via FFmpeg.

| Model | Audio Output | Music Quality | Our Usage |
| --- | --- | --- | --- |
| **Veo 3** | SFX + ambience | N/A (not music) | Disabled for Reels |
| **CogVideoX-3** | AI SFX | 2/10 | Never used |
| **Hailuo I2V** | None | N/A | Paired with Music 2.5+ |

> No video generation model produces music you'd want in a published Reel. Always mux a dedicated music model.

## Head-to-Head: Suno vs MiniMax

| Category | Suno AI | MiniMax Music 2.5+ |
| --- | --- | --- |
| **Music Quality** | 8.5/10 — genuinely impressive | 7/10 — good enough for bgm |
| **API** | No public API. Reverse-engineered wrapper. | Real REST API. Documented. |
| **Cost** | $10/mo subscription (~$0.02/clip) | ~$0.01/track, pay-per-use |
| **Automation** | Fragile — Suno can change their UI/API at any time | Stable, versioned API |
| **Instrumental Mode** | Excellent — true solo instrument support | Works on 2.5+ only |
| **Model Selection** | Bird codenames (chirp-crow, chirp-bluejay) | Simple version numbers |
| **Output Duration** | 30–240s | 60–192s |
| **Commercial Rights** | Pro plan required ($10/mo) | Included with API usage |
| **Reliability** | Breaks when Suno updates their site | 99%+ uptime |
| **Best For** | Standalone music, covers, quality-critical | Background music at scale |

Suno makes objectively better music, but "better" doesn't matter when a cron job needs 10 tracks reliably at 3 AM. For automated production, boring and documented beats brilliant and fragile.

### 🎯 When to Use Each

**Use MiniMax Music 2.5+** for automated pipelines, background music under Reels, and cron jobs where uptime matters more than concert-hall nuance (~$0.01/track).

**Use Suno** for standalone tracks, piano covers, and hero videos where a human is actively listening to the music itself (~$0.02/clip on the $10/mo Pro plan).

## Other Alternatives We Explored

- **Pixabay Royalty-Free Library (Our [Fallback](https://zonted.com/posts/ai-resilience-planning/))** — 21 local tracks organized by mood (adventure, dreamy, tropical, cinematic, cultural). Zero latency and zero cost when an API hiccups, but too small for primary rotation.
- **Trending Instagram Audio Pipeline** — Identifies trending IG audio, pulls via YouTube + `yt-dlp`, and categorizes mood with Gemini Flash (~$0.007/track across 19 tracks) when we want algorithmic sound reach rather than original beds.
- **Udio** — High audio quality like Suno, but also lacks an official public API.

## Production Pipeline & Code

| Reel Format | Music Source | Typical Prompt Style |
| --- | --- | --- |
| **Budget Reels** | MiniMax Music 2.5+ instrumental | Destination-mood based |
| **Scam Alert Reels** | MiniMax Music 2.5+ instrumental | Tension, suspense, minor key |
| **Tourist Mistake Reels** | MiniMax Music 2.5+ instrumental | Dramatic reveal, cinematic |
| **One Thing Reels** | Pixabay library (mood-based) | Pre-categorized by mood |
| **Wrong Answers Only** | MiniMax Music 2.5+ instrumental | Cultural mood matching |
| **Vintage POV** | MiniMax Music 2.5+ or 2.0 | Lo-fi, Rhodes, vinyl crackle |
| **Standalone Piano** | Suno (chirp-crow) | Solo piano, specific mood |

### The Standard Pipeline (MiniMax)

Destination + Mood → Music 2.5+ Generate → FFmpeg Trim (8–15s) → FFmpeg Mux with Video → Publish

Total music cost per Reel: **~$0.01** ($0.04–$0.10/day at 4–10 Reels/day).

### The Quality Pipeline (Suno + Gemini)

Song + Mood → Suno Generate (×5) → Gemini Score → Human Select Top 1 → Trim + Publish

Runs ~$0.20 per 10-clip batch plus Gemini Flash tokens; reserved for standalone pieces where music is the hero product.

### MiniMax Code

```
# Generate instrumental background music (Music 2.5+)
python3 scripts/minimax-video.py music \
"warm cinematic travel, acoustic guitar, golden hour" \
  -m music-2.5+ --instrumental \
  -o /tmp/my-track.mp3

# The underlying API call
curl -X POST "https://api.minimax.io/v1/music_generation" \
  -H "Authorization: Bearer $MINIMAX_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
"model": "music-2.5+",
"prompt": "warm cinematic travel background music",
"is_instrumental": true
}'
```

### Suno Code

```
import requests, time, os

SUNO_API = 'http://localhost:3000'

def generate_suno(prompt, instrumental=True, model='chirp-crow'):
"""Generate 2 clips via local Suno API wrapper."""
r = requests.post(f'{SUNO_API}/api/generate', json={
'prompt': prompt,
'make_instrumental': instrumental,
'model': model,
'wait_audio': False
}, timeout=180)
data = r.json()
ids = [clip['id'] for clip in data]

# Poll until complete
for _ in range(30):
r = requests.get(f'{SUNO_API}/api/get?ids={",".join(ids)}')
clips = r.json()
if all(c.get('status') in ('complete','error') for c in clips):
break
time.sleep(20)

# Download completed clips
for clip in clips:
if clip['status'] == 'complete' and clip.get('audio_url'):
mp3 = requests.get(clip['audio_url'])
with open(f"/tmp/{clip['id'][:8]}.mp3", 'wb') as f:
f.write(mp3.content)

# Usage
generate_suno(
"Solo piano cover of Cruel Summer. Steinway grand, "
"close-miked. Minor key reharmonization, wistful. "
"Warm intimate recording.",
model='chirp-v4'
)
```

### Full Shell Pipeline (What Our Cron Jobs Run)

```
#!/bin/bash
# Generate music → trim → mux with video → publish

# 1. Generate instrumental track
python3 scripts/minimax-video.py music \
"$MOOD_PROMPT" -m music-2.5+ --instrumental \
  -o /tmp/reel-music.mp3

# 2. Trim to 12s with fade-out
ffmpeg -y -i /tmp/reel-music.mp3 \
  -af "atrim=0:12,afade=t=out:st=10:d=2" \
/tmp/reel-music-trimmed.mp3

# 3. Mux with video
ffmpeg -y -i /tmp/reel-video.mp4 -i /tmp/reel-music-trimmed.mp3 \
  -map 0:v -map 1:a -c:v copy -c:a aac -shortest \
/tmp/reel-final.mp4

# 4. Publish
bash ~/tabiji/functions/publish-reel.sh \
/tmp/reel-final.mp4 "$CAPTION"
```

## Key Learnings & Gotchas

⚠️ Suno uses bird codenames, not version numbers

`chirp-crow` = v5, `chirp-bluejay` = v4.5+, `chirp-auk` = v4.5. Passing `chirp-v5` or `v5` returns 403.

⚠️ No artist names in Suno prompts

Suno blocks specific artist names. "Solo piano cover of Cruel Summer" works; "Taylor Swift piano cover" gets rejected. Describe the style without naming the artist.

⚠️ MiniMax is_instrumental only works on 2.5+

Music 2.0 ignores the parameter. Music 2.5 returns error `2013: invalid params, lyrics is required`. Only Music 2.5+ supports true instrumental mode.

⚠️ Gemini audio scoring is too generous

All scores cluster at 8–9/10 with no differentiation. Use Gemini as a binary **filter** (reject wrong instrumentation) rather than a point-based **ranker**.

⚠️ Suno's API can break without warning

UI updates (like March 13, 2026) break Playwright selectors—though direct API calls with a Clerk JWT token often work without launching a browser when `/api/c/check` returns `required: false`.

⚠️ MiniMax Music is a MUSIC model, not a foley model

Prompting for "ambient coffee shop sounds" or "ocean waves" still produces melodic compositions, not sound effects.

💡 FFmpeg muxing one-liner

Trim music to fit video and apply a 2-second fade-out in a single pass:

```
ffmpeg -i video.mp4 -i music.mp3 \
  -filter_complex "[1:a]atrim=0:12,afade=t=out:st=10:d=2[a]" \
  -map 0:v -map "[a]" \
  -c:v copy -c:a aac -shortest output.mp4
```

## Final Scorecard

| Category | Suno AI | MiniMax 2.0 | MiniMax 2.5 | MiniMax 2.5+ |
| --- | --- | --- | --- | --- |
| **Music Quality** | 8.5/10 | 5/10 | 6/10 | 7/10 |
| **Instrumental Mode** | 9/10 | N/A | N/A | 8/10 |
| **Prompt Adherence** | 8/10 | 6/10 | 6.5/10 | 8/10 |
| **API Quality** | 2/10 (reverse-engineered) | 7/10 | 5/10 | 9/10 |
| **Reliability** | 5/10 (can break anytime) | 7/10 | 5/10 | 9/10 |
| **Cost Efficiency** | 7/10 ($10/mo sub) | 10/10 | 10/10 | 10/10 |
| **Automation** | 4/10 (fragile) | 8/10 | 6/10 | 9/10 |
| **Output Duration** | 30–240s | 20–65s | 20–50s | 60–192s |
| **Overall** | **6.5/10** (quality king, infra nightmare) | 5/10 | 5.5/10 | **8.5/10** (production king) |

## The Verdict

### 🏆 Production Winner: MiniMax Music 2.5+

For automated video pipelines at scale, Music 2.5+ wins on infrastructure: documented REST API, working instrumental mode, ~$0.01/track, and 99%+ uptime.

### 👑 Quality Winner: Suno AI

For standalone music or piano covers where listeners focus on the audio itself, Suno's `chirp-crow` (v5) is in a different league—just budget maintenance time for its reverse-engineered API.

### 🤖 Surprise MVP: Gemini 2.5 Flash as Audio Analyzer

Use Gemini 2.5 Flash to verify instrumentation ("is this solo piano?") and tag moods, not to rank artistic quality.

Between **MiniMax Music 2.5+** for daily cron jobs, **Suno** for hero tracks, and a 21-track **Pixabay** local fallback, our entire monthly music budget across hundreds of Reels costs less than a single stock audio license.

---

All MiniMax audio samples on this page were generated from identical prompts via the MiniMax Music API on March 11, 2026. Suno samples were generated between March 11–13, 2026. No post-processing was applied — these are raw API/generation outputs. Gemini scoring was performed on March 13, 2026 using Gemini 2.5 Flash.
