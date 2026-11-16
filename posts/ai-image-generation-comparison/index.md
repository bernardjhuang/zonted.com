---
title: "AI Image Generation: 5 Models, 26 Real Results"
author: "Bernard Huang"
date: "2026-03-11"
modified: "2026-03-11"
canonical: "https://zonted.com/posts/ai-image-generation-comparison/"
category: "AI Agents & Systems"
description: "We tested GPT, Grok, Gemini (Nano Banana 2), MiniMax, and CogView-4 across 26 images in two real production workflows."
---

# AI Image Generation: 5 Models, 26 Real Results

By Bernard Huang · 2026-03-11 · 12 min read

![Side-by-side comparison of AI-generated vintage 1970s photographs of Fushimi Inari by Nano Banana 2 (9.5/10), MiniMax (5.5/10), and CogView-4 (4/10) — same prompt, dramatically different results](https://img.zonted.com/resources/ai-image-generation-comparison/hero-comparison-grid.jpg)

We tested five AI image models—**Nano Banana 2** (Gemini 3.1 Flash), **[MiniMax image-01](https://platform.minimax.io/subscribe/token-plan?code=B8atrcvv5N&source=link)**, **Grok Aurora**, **CogView-4**, and **GPT (DALL-E 3)**—across 26 images in two real production workflows for [tabiji](https://tabiji.ai/): 1970s Kodachrome film slides of Kyoto (18 images) and candid iPhone tourist shots of Verona for [Instagram Reels](https://zonted.com/posts/ai-reels-what-actually-works/) (8 images).

## TL;DR

Across 26 production images and 5 models, prompt adherence—not raw visual polish—separated usable tools from toys: Nano Banana 2 won overall at ~$0.02/image.

- **Vintage film & crowd scenes (Nano Banana 2)** — Scored 8.8/10 on 1970s Kodachrome Kyoto and 9/10 on Verona crowd shots, rendering legible Japanese kanji and real Kodachrome rebate markings at ~$0.02/image.
- **Close-up portraits (MiniMax image-01)** — Scored 8/10 on candid café portraits with the most convincing human faces (~$0.04/image), but ignored monochrome constraints (2/10 on B&W).
- **All-rounder vs. laggards** — Grok Aurora (~$0.07/image) finished a close second across Verona with 9/10 emotional storytelling; CogView-4 (2/10 prompt adherence) and GPT/DALL-E 3 (4–6/10, garbled text and plastic skin) finished last.

## Why This Test Matters

Most AI image benchmarks test forgiving prompts like "a cat wearing a hat" or "futuristic cityscape." That tells you which model makes pretty default wallpapers—not which model follows a production brief.

Our [Instagram Reels](https://www.instagram.com/tabijiai/) require two unforgiving aesthetics: 1970s Kodachrome slides with period-accurate grain and clipped dynamic range, and handheld iPhone tourist shots with legible street signage and imperfect framing. If a model ignores stylistic constraints on vintage film or monochrome silver gelatin prints, it will ignore your constraints on any production workflow.

## The 5 Models We Tested

| Model | Provider | Cost/Image | Max Resolution | Tests |
| --- | --- | --- | --- | --- |
| **Nano Banana 2** | Google (Gemini 3.1 Flash) | ~$0.02 | Up to 4K | Kyoto + Verona |
| **MiniMax image-01** | MiniMax | ~$0.04 | Up to 2K | Kyoto + Verona |
| **CogView-4** | [Z.AI](https://z.ai/subscribe?ic=JY9V1BN5ZO) (Zhipu AI) | ~$0.02 | 720×1440 | Kyoto only |
| **Grok Aurora** | xAI | ~$0.07 | Up to 2K | Verona only |
| **GPT (DALL-E 3)** | OpenAI | ~$0.04–$0.08 | 1024×1792 | Verona only |

**Test 1 (Kyoto)** ran Nano Banana 2, MiniMax, and CogView-4 across four landmarks (Fushimi Inari, Kinkaku-ji, Arashiyama, and Gion). **Test 2 (Verona)** dropped CogView-4 and added GPT and Grok Aurora across two candid iPhone prompts.

## Test 1: Vintage 1970s Kyoto — Can AI Fake Film Photography?

We prompted all three models for 1970s Kodachrome film: warm saturated midtones, vintage grain, off-center tourist framing, and period-accurate details. Here is Fushimi Inari:

![AI-generated vintage 1970s photograph of Fushimi Inari torii gates in Kyoto, created by Nano Banana 2 (Gemini 3.1 Flash) — rated 9.5/10 for authenticity](https://img.zonted.com/resources/ai-image-generation-comparison/nano-fushimi-inari.jpg)
Nano Banana 2 9.5/10

![AI-generated vintage photograph of Fushimi Inari torii gates by MiniMax image-01 — warm color science but wrong POV, rated 5.5/10](https://img.zonted.com/resources/ai-image-generation-comparison/minimax-fushimi-inari.jpg)
MiniMax 5.5/10

![AI-generated photograph of Fushimi Inari by CogView-4 — cinematic modern look instead of vintage, garbled kanji, rated 4/10](https://img.zonted.com/resources/ai-image-generation-comparison/cogview-fushimi-inari.jpg)
CogView-4 4/10

### ▶ Animated — Vintage POV Reel Clips

[Video](https://img.zonted.com/resources/ai-image-comparison/clips/nano-01-fushimi.mp4)
Nano Banana 2 — Animated

[Video](https://img.zonted.com/resources/ai-image-comparison/clips/minimax-01-fushimi.mp4)
MiniMax — Animated

These clips show the same images after Remotion rendering — with film grain, vignette, and slow drift animation applied.

Across all four landmarks, **Nano Banana 2** nailed the brief: warm Kodachrome midtones, legible kanji ("奉" and "納" carved on the torii columns), and casual snapshot framing. **MiniMax** had pleasing color science but ignored POV instructions and composed like a modern travel magazine. **CogView-4** ignored the vintage prompt entirely—rendering HDR orange-teal grading and garbled kanji.

Kinkaku-ji and Arashiyama showed the exact same split:

![AI-generated vintage 1970s photograph of Kinkaku-ji Golden Pavilion reflected in mirror pond, created by Nano Banana 2 — muted gold tones, rated 8/10](https://img.zonted.com/resources/ai-image-generation-comparison/nano-kinkakuji.jpg)
NB2 — Kinkaku-ji 8/10

![AI-generated photograph of Kinkaku-ji by MiniMax image-01 — warm tones but overly polished composition, rated 6/10](https://img.zonted.com/resources/ai-image-generation-comparison/minimax-kinkakuji.jpg)
MiniMax — Kinkaku-ji 6/10

![AI-generated photograph of Kinkaku-ji by CogView-4 — modern HDR look with no vintage character, rated 3/10](https://img.zonted.com/resources/ai-image-generation-comparison/cogview-kinkakuji.jpg)
CogView-4 — Kinkaku-ji 3/10

### ▶ Animated — Kinkaku-ji Reel Clips

[Video](https://img.zonted.com/resources/ai-image-comparison/clips/nano-02-kinkakuji.mp4)
Nano Banana 2 — Animated

[Video](https://img.zonted.com/resources/ai-image-comparison/clips/minimax-02-kinkakuji.mp4)
MiniMax — Animated

![AI-generated vintage 1970s photograph of Arashiyama bamboo grove in Kyoto by Nano Banana 2 — olive-shifted greens mimicking Kodachrome, rated 8.5/10](https://img.zonted.com/resources/ai-image-generation-comparison/nano-arashiyama-bamboo.jpg)
NB2 — Arashiyama 8.5/10

![AI-generated photograph of Arashiyama bamboo grove by MiniMax — warm tones but too vivid for vintage, rated 6/10](https://img.zonted.com/resources/ai-image-generation-comparison/minimax-arashiyama-bamboo.jpg)
MiniMax — Arashiyama 6/10

![AI-generated photograph of Arashiyama bamboo grove by CogView-4 — oversaturated modern cinematic look, rated 2.5/10](https://img.zonted.com/resources/ai-image-generation-comparison/cogview-arashiyama-bamboo.jpg)
CogView-4 — Arashiyama 2.5/10

### ▶ Animated — Arashiyama Reel Clips

[Video](https://img.zonted.com/resources/ai-image-comparison/clips/nano-03-arashiyama.mp4)
Nano Banana 2 — Animated

[Video](https://img.zonted.com/resources/ai-image-comparison/clips/minimax-03-arashiyama.mp4)
MiniMax — Animated

## The Black & White Test That Broke Two Models

For Gion at dusk, we specified **"absolutely no color whatsoever, silver gelatin print"**—a geisha walking down a lantern-lit alley on black-and-white film.

![AI-generated black and white silver gelatin photograph of Gion district in Kyoto by Nano Banana 2 — stunning monochrome with deep blacks and luminous lanterns, rated 9/10](https://img.zonted.com/resources/ai-image-generation-comparison/nano-gion-evening.jpg)
Nano Banana 2 9/10

![MiniMax failed black and white test for Gion evening scene — rendered in full color despite explicit B&W prompt, rated 2/10](https://img.zonted.com/resources/ai-image-generation-comparison/minimax-gion-evening.jpg)
MiniMax 2/10

![CogView-4 completely ignored black and white instruction for Gion scene — bright orange and red colors, rated 0/10 for prompt adherence](https://img.zonted.com/resources/ai-image-generation-comparison/cogview-gion-evening.jpg)
CogView-4 0/10

### ▶ Animated — Gion Evening Reel Clips

[Video](https://img.zonted.com/resources/ai-image-comparison/clips/nano-06-gion.mp4)
Nano Banana 2 — Animated

[Video](https://img.zonted.com/resources/ai-image-comparison/clips/minimax-06-gion.mp4)
MiniMax — Animated

**Nano Banana 2** delivered pure monochrome with zero color bleed—inky machiya shadows, glowing lanterns, and Tri-X-style silver grain reminiscent of Daidō Moriyama. **MiniMax (2/10)** rendered warm amber lanterns and teal shadows. **CogView-4 (0/10)** output neon orange lanterns and bright red obi accents.

> When we asked for "absolutely no color whatsoever," Nano Banana 2 gave us black and white. MiniMax and CogView-4 gave us whatever their priors wanted.

## Test 2: Phone Camera Realism — Verona

The other half of our pipeline needs images that pass as **unfiltered iPhone photos**—handheld framing, natural depth of field, crowd density, and readable signs. We tested **GPT (DALL-E 3)**, **Grok (Aurora)**, **Nano Banana 2**, and **MiniMax** across two Verona prompts.

### Which AI model handles crowd scenes best?

**Prompt:** An exhausted female tourist photographed from behind in a dense crowd outside Casa di Giulietta in Verona. iPhone photo quality — handheld, natural grain, depth of field, motion blur. Juliet's bronze statue visible ahead. Tourist overwhelm is palpable.

![GPT DALL-E 3 generated image of Juliet's House crowd scene — over-cinematic, garbled text on signs, porcelain-smooth faces, rated 6/10](https://img.zonted.com/tmp/verona-benchmark/gpt-mistake.png)
GPT (DALL-E 3) 6/10

![Grok Aurora generated image of Juliet's House crowd scene — incredibly expressive exhausted woman, natural crowd density, rated 8.5/10](https://img.zonted.com/tmp/verona-benchmark/grok-mistake.jpg)
Grok (Aurora) 8.5/10

![Nano Banana 2 generated image of Juliet's House crowd scene — most photorealistic, legible Juliet text, correct Fjällräven backpack, rated 9/10](https://img.zonted.com/tmp/verona-benchmark/nb2-mistake.png)
Nano Banana 2 9/10 🏆

![MiniMax generated image of Juliet's House crowd scene — too dark, bokeh too cinematic, reads as dangerous alley not tourist trap, rated 7/10](https://img.zonted.com/tmp/verona-benchmark/minimax-mistake.jpg)
MiniMax 7/10

**Nano Banana 2 won (9/10):** legible "Juliet" souvenir text, an accurate Fjällräven Kånken logo on the backpack, and a raised phone screen in the foreground that sells the tourist crush. **Grok Aurora (8.5/10)** delivered the most expressive facial fatigue on the main subject, with slight face melting deeper in the crowd. **MiniMax (7/10)** shot it like a moody Sony A7III thriller in a dark alley, and **GPT (6/10)** produced porcelain skin and gibberish signage ("SLOLEROCVEE").

### Is GPT good for portrait-style travel photos?

**Prompt:** Two Italian men in their 50s laughing and drinking wine at an outdoor café in Piazza delle Erbe, Verona. Candid iPhone shot — natural light, movement blur, authentic body language. Amarone bottle visible. Medieval tower in background.

![GPT DALL-E 3 generated image of Italian men at Piazza delle Erbe café — over-saturated, hyper-rendered, uncanny faces, tourism ad look, rated 4/10](https://img.zonted.com/tmp/verona-benchmark/gpt-local.png)
GPT (DALL-E 3) 4/10

![Grok Aurora generated image of Italian men at Piazza delle Erbe café — best authentic mood, convincingly Italian men, natural laughter, rated 7/10](https://img.zonted.com/tmp/verona-benchmark/grok-local.jpg)
Grok (Aurora) 7/10

![Nano Banana 2 generated image of Italian men at Piazza delle Erbe café — best prompt adherence, legible Amarone label, wine glass + bottle, rated 6.5/10](https://img.zonted.com/tmp/verona-benchmark/nb2-local.png)
Nano Banana 2 6.5/10

![MiniMax generated image of Italian men at Piazza delle Erbe café — most photographically convincing, best faces, natural lighting, documentary feel, rated 8/10](https://img.zonted.com/tmp/verona-benchmark/minimax-local.jpg)
MiniMax 8/10 🏆

**MiniMax won portraits (8/10):** the two men look like specific, lived-in human beings with documentary lighting. **Grok (7/10)** nailed the candid laughter (despite matching sweaters and missing wine glasses). **Nano Banana 2 (6.5/10)** rendered a legible "Amarone" bottle label and medieval tower, but the pose felt staged. **GPT (4/10)** looked like an oversaturated stock illustration.

### 📱 Key Finding: Different Models Win Different Scene Types

**Nano Banana 2 dominates crowd and location scenes** — text rendering, brand accuracy, and iPhone aesthetic make it the clear winner for anything with signage, landmarks, or branded items.

**MiniMax dominates intimate people/portrait scenes** — when the faces are the subject, MiniMax's human rendering is unmatched.

**Grok is the strongest all-rounder** — close second in both categories, best emotional storytelling overall. If you're picking one model for everything, pick Grok.

**GPT/DALL-E 3 is dead last for photorealism.** Garbled text, over-rendered aesthetics, and uncanny faces make it unsuitable for content that needs to pass as real.

## Prompt Engineering Makes or Breaks It

After the first Kyoto pass, we rewrote our prompts with explicit optical and film-stock physics:

- **V1 (vague):** "Shot on Kodachrome film, vintage feel"
- **V2 (specific):** "Warm saturated midtones, slightly cool shadows, limited dynamic range with clipped highlights and blocked shadows. Include scan artifacts: dust specks, hair, scratches. Amateur composition, slightly off-center. Chromatic aberration, lens softness at edges. No borders, no frame edges."

![Nano Banana 2 Fushimi Inari with basic V1 prompt — good vintage feel but missing physical film artifacts](https://img.zonted.com/resources/ai-image-generation-comparison/nano-fushimi-inari.jpg)
Nano Banana 2 — V1 Prompt

![Nano Banana 2 Fushimi Inari with detailed V2 prompt — added Kodachrome film rebate markings, exposure-dependent grain, and scan artifacts](https://img.zonted.com/resources/ai-image-generation-comparison/nano-v2-fushimi-inari.jpg)
Nano Banana 2 — V2 Prompt

With V2, **Nano Banana 2** generated authentic **Kodachrome film rebate markings** ("12 KODACHROME" in orange-on-black along the border with frame arrows) and exposure-dependent grain that clumps in the shadows like real silver halide crystals.

![MiniMax Fushimi Inari with basic V1 prompt — warm tones but modern composition](https://img.zonted.com/resources/ai-image-generation-comparison/minimax-fushimi-inari.jpg)
MiniMax — V1 Prompt

![MiniMax Fushimi Inari with detailed V2 prompt — warmer and moodier but still unable to produce physical film artifacts](https://img.zonted.com/resources/ai-image-generation-comparison/minimax-v2-fushimi-inari.jpg)
MiniMax — V2 Prompt

**MiniMax** shifted warmer and added a subtle light leak, but ignored the physical scan artifacts and film stock details.

> Detailed prompt engineering only pays off on models that actually listen. Nano Banana 2's prompt ceiling is 10/10; MiniMax improves marginally; CogView-4 ignores technical specs.

## Combined Scorecard: All 5 Models

| Category | Nano Banana 2 | MiniMax | CogView-4 | Grok Aurora | GPT (DALL-E 3) |
| --- | --- | --- | --- | --- | --- |
| **Prompt Adherence** | 9.5/10 | 5/10 | 2/10 | 7/10 | 5/10 |
| **Vintage Film** | 8.8/10 | 5.9/10 | 3.6/10 | — | — |
| **Crowd Scenes** | 9/10 | 7/10 | — | 8.5/10 | 6/10 |
| **People/Portraits** | 6.5/10 | 8/10 | — | 7/10 | 4/10 |
| **Text / Kanji Accuracy** | 8/10 | 4/10 | 1.5/10 | 6/10 | 3/10 |
| **Prompt Eng. Ceiling** | 10/10 | 5/10 | 3/10 | 7/10 | 5/10 |
| **Emotional Storytelling** | 7/10 | 7/10 | 6/10 | 9/10 | 5/10 |
| **Cost per Image** | ~$0.02 | ~$0.04 | ~$0.02 | ~$0.07 | ~$0.04–$0.08 |

## What to Use for What

- **Crowd scenes, landmarks, signage, or CJK text →** Nano Banana 2 (~$0.02/image). Unbeatable prompt adherence and legible text.
- **Vintage film / strict stylistic constraints →** Nano Banana 2. The only model that respects monochrome and film-stock physics.
- **Close-up portraits & human faces →** MiniMax image-01 (~$0.04/image). Best skin texture and natural lighting.
- **Single all-rounder model →** Grok Aurora (~$0.07/image). Strong second place everywhere and 9/10 emotional storytelling.
- **Skip for photorealism →** GPT/DALL-E 3 (plastic skin, garbled text) and CogView-4 (ignores style instructions).

## Pricing Comparison

| Factor | Nano Banana 2 | MiniMax | CogView-4 | Grok Aurora | GPT (DALL-E 3) |
| --- | --- | --- | --- | --- | --- |
| **Cost per image** | ~$0.02 | ~$0.04 | ~$0.02 | ~$0.07 | ~$0.04–$0.08 |
| **6-image Reel cost** | ~$0.12 | ~$0.24 | ~$0.12 | ~$0.42 | ~$0.24–$0.48 |
| **Max resolution** | Up to 4K | Up to 2K | 720×1440 | Up to 2K | 1024×1792 |
| **Free tier** | Yes (Gemini API) | Limited | Limited | Limited | No |
| **API complexity** | Moderate (SDK) | Simple REST | Simple REST | Simple REST | Simple REST |
| **Latency** | ~8–15s | ~10–20s | ~15–25s | ~10–15s | ~10–20s |

At ~$0.12 per 6-image Reel (plus a free tier on Google AI Studio), Nano Banana 2 is both the cheapest and highest-scoring model for location and vintage workflows.

## How to Use These Models (Code Examples)

Here are the minimal API calls for all five models:

### Nano Banana 2 (Google Gemini 3.1 Flash Image)

```
import google.generativeai as genai

genai.configure(api_key="YOUR_GEMINI_API_KEY")
model = genai.GenerativeModel("gemini-3.1-flash-image-preview")

response = model.generate_content(
"A vintage 1970s Kodachrome photograph of Fushimi Inari torii gates. "
"Warm saturated midtones, slightly cool shadows, limited dynamic range. "
"Include scan artifacts: dust specks, scratches. Amateur composition.",
generation_config=genai.GenerationConfig(
response_modalities=["IMAGE", "TEXT"]
)
)

# Save the image
for part in response.candidates[0].content.parts:
if part.inline_data:
with open("output.png", "wb") as f:
f.write(part.inline_data.data)
```

### [MiniMax image-01](https://platform.minimax.io/subscribe/token-plan?code=B8atrcvv5N&source=link)

```
curl -X POST "https://api.minimax.chat/v1/image_generation" \
  -H "Authorization: Bearer YOUR_MINIMAX_KEY" \
  -H "Content-Type: application/json" \
  -d '{
"model": "image-01",
"prompt": "A vintage 1970s photograph of Fushimi Inari torii gates...",
"aspect_ratio": "9:16",
"response_format": "url"
}'
```

### CogView-4 ([Z.AI](https://z.ai/subscribe?ic=JY9V1BN5ZO))

```
curl -X POST "https://open.bigmodel.cn/api/paas/v4/images/generations" \
  -H "Authorization: Bearer YOUR_ZAI_KEY" \
  -H "Content-Type: application/json" \
  -d '{
"model": "cogview-4-250304",
"prompt": "A vintage 1970s photograph of Fushimi Inari torii gates...",
"size": "720x1440"
}'
```

### Grok (xAI Aurora)

```
curl -X POST "https://api.x.ai/v1/images/generations" \
  -H "Authorization: Bearer YOUR_XAI_KEY" \
  -H "Content-Type: application/json" \
  -d '{
"model": "grok-2-image-1212",
"prompt": "Phone camera photo of exhausted tourist in crowd...",
"n": 1,
"response_format": "url"
}'
```

### GPT / DALL-E 3 (OpenAI)

```
curl -X POST "https://api.openai.com/v1/images/generations" \
  -H "Authorization: Bearer YOUR_OPENAI_KEY" \
  -H "Content-Type: application/json" \
  -d '{
"model": "dall-e-3",
"prompt": "Phone camera photo of exhausted tourist in crowd...",
"n": 1,
"size": "1024x1792",
"quality": "standard"
}'
```

## Full Reels: Side by Side

Here are the complete 21-second Vintage POV Reels assembled from the Kyoto outputs—identical Remotion timing, vignette, slow drift, and text overlays, differing only in the source images:

[Video](https://img.zonted.com/resources/ai-image-comparison/vintage-kyoto-nano-reel.mp4)
🏆 Nano Banana 2 — Full Kyoto Reel (21s)

[Video](https://img.zonted.com/resources/ai-image-comparison/vintage-kyoto-minimax-reel.mp4)
MiniMax — Full Kyoto Reel (21s)

Both Reels use identical Remotion compositions and timing. Nano Banana 2's Kodachrome color science locks right into the animated film-grain layer, whereas MiniMax's modern rendering clashes with the vintage overlay.

---

All images in this comparison were generated from identical prompts on the same day (March 10, 2026). No post-processing was applied. The images shown are direct outputs from each model's API.
