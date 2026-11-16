---
title: "AI Comics: Do's & Don'ts, 5+ Models Tested"
author: "Bernard Huang"
date: "2026-04-18"
modified: "2026-04-18"
canonical: "https://zonted.com/posts/ai-comics-dos-donts/"
category: "AI Agents & Systems"
description: "We tested Midjourney, Seedream v5 Lite, Wan 2.7 Pro, Qwen Image 2.0, and Nano Banana Pro — then shipped 733 comics across eight countries."
---

# AI Comics: Do's & Don'ts, 5+ Models Tested

By Bernard Huang · 2026-04-18 · 18 min read

## TL;DR

We tested five image models and shipped 733 four-panel watercolor comics across eight countries on [tabiji.ai](https://tabiji.ai) for ~$0.15 per comic — after fixing a silent 9% classification bug mid-scale.

- **Model winner: Nano Banana Pro ($0.14/image)** — Beat Midjourney, Seedream v5 Lite, Wan 2.7 Pro, and Qwen Image 2.0 on English speech-bubble spelling and character consistency.
- **What broke at scale** — Thailand’s 50 comics shipped in 90 seconds from hand-written scripts, but scaling to Germany via regex keyword routing misclassified 9% of scams (rendering a Brandenburger Tor clipboard hustle as a U-Bahn pickpocket).
- **The V2 fix** — Replaced regex templates with per-scam Gemini 2.5 Pro script synthesis (`responseSchema`) and a fail-loud quality gate across all 733 comics (~$110 total).

Generating one four-panel AI comic is easy. Generating 733 four-panel comics that look like they came from the same illustrator, star the same four recurring characters, spell English speech bubbles accurately, and match the exact mechanics of 733 different tourist scams is an engineering problem.

Here is the exact pipeline — model benchmarks, prompt locks, reference-image payloads, and the V2 postmortem — that took us from Midjourney gibberish (*“SARPER TOLT”*) to [733 production comics](https://tabiji.ai/scams/country/th/) across eight countries.

## Why comics, and why this is hard

On [tabiji.ai](https://tabiji.ai), our city scam guides break down up to 25 local tourist traps per city with red flags, avoidance steps, and Reddit receipts. Useful material, but eight consecutive text blocks make readers bounce.

Our readership skews slightly older and female — couples planning a first trip to Thailand rather than 22-year-old backpackers. A warm, hand-painted watercolor comic communicates the *shape* of a con — the friendly stranger, the tuk-tuk detour, the gem-shop pressure, the regret — in five seconds flat.

The spec: one 2×2 four-panel watercolor comic per scam, legible English dialogue, and a recurring cast of four protagonists rotating across hundreds of scams. Three failure modes usually kill AI comics at this scale:

- **Broken text rendering.** Diffusion models mangle multi-word English dialogue into plausible-looking alien script.
- **Character drift.** Prompt for a “silver-haired 62-year-old woman in a straw hat” fifty times and you get fifty different women.
- **Style drift.** Palette, linework, and paper grain shift slightly on every call until comic #50 looks nothing like comic #1.

## Round 1: Midjourney — good styles, broken text

We started with [Midjourney](https://www.midjourney.com), driving it headlessly through the [Apify](https://www.apify.com?fpr=bernard) `imageaibot/midjourney-bot` actor (`action=imagine`, polling `action=getTask`).

We ran the classic Bangkok Grand Palace gem scam through five aesthetic directions:

1. **Warm watercolor storybook** — Beatrix Potter pastels and visible paper grain
2. **Hergé / Tintin ligne claire** — crisp black ink outlines and flat fills
3. **New Yorker editorial cartoon** — loose ink with watercolor wash
4. **Studio Ghibli / Miyazaki** — warm painterly anime
5. **Mid-century travel poster** — 1950s screen-print color blocks

Every prompt described the same four beats (palace “closed” → helpful tuk-tuk → gem shop → regret at home). Watercolor storybook won immediately:

![Midjourney's 4-variation grid for the watercolor storybook style](https://img.zonted.com/resources/ai-comics-dos-donts/mj-watercolor-styles.png)

*Midjourney v6: warm watercolor storybook. Midjourney's native output is a 2×2 variation grid, so each quadrant is its own interpretation of the prompt, and each of those interpretations is in turn a mini-comic. The bottom-right quadrant was the strongest.*

The watercolor aesthetic hit the exact tone we wanted: approachable, expressive faces, and a silver-haired protagonist who read clearly as ~60. Tintin had sharper architecture and the New Yorker style had great linework, but both felt colder than the storybook wash.

### The thing Midjourney cannot do

Next, we added explicit dialogue to the prompt: *“Speech bubble reads: PALACE CLOSED TODAY FOR ROYAL CEREMONY!”* Here is what Midjourney rendered:

![Midjourney's attempt at rendering English speech bubbles — most of the text is gibberish](https://img.zonted.com/resources/ai-comics-dos-donts/mj-gibberish.png)

*Midjourney v6 understood that we wanted speech bubbles in the right places. The text inside them reads: "SARPER TOLT," "BEETAL COCOCELS TOUS NT ST REGRSAAL," "FALLET GOLL!" — confident, legible-looking gibberish.*

Midjourney nails the visual texture of lettering — kerning, bubble geometry, pointer tails — while hallucinating the spelling. Compositing 2,900 speech bubbles manually in Photoshop was out of the question, and Midjourney still lacked a clean programmatic lock for multi-character consistency.

We moved the pipeline to [WaveSpeed](https://wavespeed.ai/?ref=zonted), which exposes current image models behind a single REST API and billing account.

## Round 2: Wavespeed four-model showdown

We sent the exact same four-panel watercolor prompt — with full English dialogue — to four models via WaveSpeed’s HTTP API:

- **Seedream v5 Lite** (ByteDance) — `bytedance/seedream-v5.0-lite`
- **Wan 2.7 Pro** (Alibaba) — `alibaba/wan-2.7/text-to-image-pro`
- **Qwen Image 2.0** (Alibaba) — `wavespeed-ai/qwen-image-2.0/text-to-image`
- **Nano Banana Pro** (Google Gemini 2.5 Flash Image) — `google/nano-banana-pro/text-to-image`

Each model received a parallel `POST /api/v3/{model_id}` with `{"prompt": ..., "aspect_ratio": "1:1"}`, polled via `GET /api/v3/predictions/{id}/result`. All four returned in under 90 seconds:

### Seedream v5 Lite ($0.035/image)

![Seedream v5 Lite's four-panel comic — speech bubbles are clean and correctly spelled](https://img.zonted.com/resources/ai-comics-dos-donts/ws-seedream.jpeg)

*Seedream v5 Lite. Perfect spelling across all four bubbles, clean 2×2 grid with panel numbers, consistent protagonist. The watercolor is slightly more saturated than we wanted but very usable.*

### Wan 2.7 Pro ($0.075/image)

![Wan 2.7 Pro's four-panel comic — one spelling typo visible](https://img.zonted.com/resources/ai-comics-dos-donts/ws-wan27.png)

*Wan 2.7 Pro. Strong composition, readable text, consistent character — but introduced "dollares" in panel 4. Tiny, but the kind of thing that means you're still proofreading every generation.*

### Qwen Image 2.0 ($0.03/image)

![Qwen Image 2.0's four-panel comic — lower resolution output](https://img.zonted.com/resources/ai-comics-dos-donts/ws-qwen20.png)

*Qwen Image 2.0. Decent composition and correctly-spelled text, but the default output is noticeably lower resolution and the linework is softer than we wanted.*

### Nano Banana Pro ($0.14/image)

![Nano Banana Pro's four-panel comic — cleanest result across all models](https://img.zonted.com/resources/ai-comics-dos-donts/ws-nanopro.jpeg)

*Nano Banana Pro. Perfect spelling, the strongest character consistency, the warmest watercolor palette, and the most compositionally sophisticated result — notice how panel 2 captures the boarding action, panel 4 is a believable kitchen, not just four talking-head shots.*

### The Verdict

**Nano Banana Pro wins decisively for any comic project requiring English dialogue. At $0.14/image, it costs 4× Seedream and 4.7× Qwen, but zero spelling touch-ups saves hours of manual review per batch.**

Why Nano Banana Pro (Google’s Gemini image model on WaveSpeed) pulls ahead: it is a native multimodal transformer rather than a diffusion model bolted onto a text encoder. It models speech-bubble strings as tokens rather than guessing at letter-shaped pixels, giving it a massive edge on dialogue, signage, and multi-panel staging.

## The three consistency locks

Solving spelling only gets you halfway; preventing character and palette drift across hundreds of comics requires three explicit locks:

### 1. A locked style block

We prepend a 100-word visual style paragraph verbatim to every prompt, with zero variation between calls. Here is the Thailand block:

```
A single illustrated comic book page in warm soft watercolor
storybook style, showing four sequential panels arranged in a 2x2
grid with small numbers 1, 2, 3, 4 in the upper-left corner of
each panel, separated by thin clean white gutters. Hand-painted
watercolor textures with visible paper grain, muted pastel palette
warmed by golden Thai sunlight, gentle expressive faces with soft
pencil linework, delicate shadows, unhurried storybook pacing.
Each panel contains one clean white rounded speech bubble with a
small pointer tail, holding short printed English dialogue in
simple black lettering — text must be legible and correctly
spelled. Square 1:1 composition, 2K resolution.
```

Every phrase anchors a specific dimension: “visible paper grain” blocks glossy digital rendering, “muted pastel palette warmed by golden Thai sunlight” locks regional color temperature, and “text must be legible and correctly spelled” measurably tightens Gemini’s typography.

### 2. Canonical character sheets

We wrote four canonical protagonist paragraphs — Margie (62F), Priya (34F), Harry (64M), and Marcus (34M) — and pasted the chosen character verbatim into the `CHARACTER:` slot of each prompt. Trust-based cons go to Margie; transit hustles go to Priya; map/charm distractions go to Harry; nightlife traps go to Marcus.

Here is Margie’s character lock:

```
A 62-year-old Western woman with shoulder-length silver-gray hair
worn under a woven straw sun hat with a cream ribbon, warm blue
eyes behind tortoiseshell reading glasses often perched on her
head, light olive complexion with gentle laugh lines and a
friendly curious expression. She wears a cream linen blouse, tan
wide-leg travel pants, and white canvas sneakers, with a small
tan leather crossbody bag and a coral scarf. Gracious, cheerful,
a little too trusting.
```

Four rules keep characters recognizable across panels:

- **Hard costume anchors.** The straw hat with a cream ribbon, coral scarf, and tan crossbody bag do more work than facial descriptions.
- **Concrete physical traits.** “Light olive complexion with gentle laugh lines” constrains the generator far better than “friendly older woman.”
- **An emotional baseline.** “Gracious, cheerful, a little too trusting” shapes her posture in Panel 1 and her dismay in Panel 4.
- **Zero paraphrasing.** Never tweak a single adjective between prompts.

### 3. Reference images (the big lock)

Once you generate two or three baseline comics you love, **pass their URLs into the `images` array on every subsequent call** via Nano Banana Pro’s `edit` endpoint:

```
POST https://api.wavespeed.ai/api/v3/google/nano-banana-pro/edit
{
"prompt": "<style block>\n\nCHARACTER: <Priya paragraph>\n\nSCENE:\nPanel 1: ...\nPanel 2: ...",
"images": [
"https://img.tabiji.ai/scams/bangkok/scam-1.jpg",
"https://img.tabiji.ai/scams/bangkok/scam-2.jpg",
"https://img.tabiji.ai/scams/bangkok/scam-4.jpg"
],
"aspect_ratio": "1:1",
"output_format": "jpeg"
}
```

Passing three reference comics locks the watercolor wash, gutter width, paper texture, and speech-bubble font. To stop the model from copying the reference character into scenes meant for a different protagonist, append this instruction to the style block:

```
Match the watercolor palette, linework, paper texture, and
lettering style of the reference images exactly; the protagonist
must be the NEW character described in CHARACTER below — do not
reuse characters from the reference images.
```

Without that sentence, the model bleeds Margie into Priya’s scenes. With it, style transfers cleanly while the protagonist swaps on command.

### The `edit-multi` gotcha

WaveSpeed exposes both `edit` and `edit-multi` for Nano Banana Pro. Save yourself a failed run: **only `edit` supports `aspect_ratio: "1:1"`** (`edit-multi` rejects square outputs with *“value is not one of the allowed values [3:2, 2:3, 3:4, 4:3]”*). Standard `edit` already accepts multiple reference URLs in its `images` array.

## Scaling to 50 comics

For Thailand (our first country), we extracted every scam title, location, and summary from nine city pages (Bangkok, Chiang Mai, Chiang Rai, Koh Phangan, Koh Samui, Krabi, Pai, Pattaya, Phuket) and hand-authored a Python dictionary mapping each scam to a character and four-panel script:

```
SCENES = {
("chiang-mai", 5, "margie"): panels(
("Margie looks at a colorful Chiang Mai flyer advertising "
"'Ethical Elephant Sanctuary — Bathing & Riding' with happy "
"elephant photos.",
"Ethical elephant sanctuary — sounds lovely!"),
("Margie arrives at a dusty roadside camp with chained elephants "
"and tourists taking rides, shocked expression.",
"These elephants look unhappy!"),
("A staff member at the camp shrugs dismissively; another tourist "
"climbs on for a ride.",
"All elephants like rides here!"),
("Margie at a real ethical sanctuary later, watching elephants "
"bathing freely in a river, smiling.",
"Real sanctuaries don't chain elephants!"),
),
# ... 41 more
}
```

The build script concatenated `STYLE + CHARACTER + SCENE` into `/tmp/th_*.json` (each pointing to the same three Bangkok reference comics) and fired all 42 jobs in parallel:

```
for f in /tmp/th_*.json; do
(curl -s -X POST \
    -H "Authorization: Bearer $WS_KEY" \
    -H "Content-Type: application/json" \
    -d @"$f" \
"https://api.wavespeed.ai/api/v3/google/nano-banana-pro/edit" \
| jq -r '.data.id' > "$(dirname "$f")/$(basename "$f" .json).id"
) &
done
wait
```

All 42 requests dispatched in under three seconds, and parallel polling finished in **~90 seconds of wall time**.

Hand-writing scripts worked great for 50 Thai comics. It broke badly when we tried to scale to 733 comics across eight countries.

### The negative-cache gotcha

One Cloudflare trap to watch out for: if your script `HEAD`-checks an R2 image URL before the upload finishes, Cloudflare caches the `404` for 60–120 seconds. Subsequent verification checks will see phantom 404s until the negative cache expires (or until you bust it with `?v=1`). Also set a browser `User-Agent` when verifying URLs from Python; Cloudflare’s default WAF blocks `Python-urllib/3.x` with a `403`.

## Cost, time, and the final recipe

Generator spend for the initial 50-comic Thailand batch:

| Stage | Model | Calls | Unit | Total |
| --- | --- | --- | --- | --- |
| Style exploration | Midjourney (Apify) | 7 | ~$0.25 | ~$1.75 |
| Model showdown | Seedream v5 Lite | 1 | $0.035 | $0.04 |
| Model showdown | Wan 2.7 Pro | 1 | $0.075 | $0.08 |
| Model showdown | Qwen Image 2.0 | 1 | $0.03 | $0.03 |
| Production | Nano Banana Pro (text-to-image) | 2 | $0.14 | $0.28 |
| Production | Nano Banana Pro (`edit` with refs) | 48 | $0.14 | $6.72 |
| **Total** |  | **60** |  | **~$8.90** |

Under nine dollars for 50 production comics across nine city pages — **$0.17 per comic all-in**, including style exploration and model benchmarks. Commissioning 50 custom four-panel watercolor strips from a freelance illustrator runs $200–$400 per strip and takes six weeks.

At multi-country scale, adding a per-scam Gemini 2.5 Pro script-synthesis call (~$0.01–$0.05) nudged our per-country run from ~$10 to ~$15. Across eight countries and 733 comics, total compute spend landed around **$110**.

### The final recipe, one screen

1. **Explore styles on Midjourney first.** Generate 3–5 aesthetic directions cheaply before locking your production model.
2. **Run production on Nano Banana Pro** (`google/nano-banana-pro/edit` on [WaveSpeed](https://wavespeed.ai/?ref=zonted), `1:1` aspect ratio) whenever panels contain English dialogue.
3. **Lock a 100-word style block.** Paste it verbatim at the top of every prompt.
4. **Write canonical character sheets.** One paragraph per recurring protagonist with explicit wardrobe anchors (hat, scarf, bag). Never paraphrase.
5. **Pass 2–3 reference comics via `images`.** Anchors palette, gutter width, paper grain, and lettering across hundreds of calls.
6. **Explicitly separate style from character.** Instruct the model to match the reference style while drawing the *new* character specified in `CHARACTER:`.
7. **Parallelize the batch.** WaveSpeed handles 40+ concurrent jobs cleanly; wall time equals your slowest single image (~90 seconds).
8. **Synthesize each script with an LLM (`responseSchema`), never a regex classifier.** Have Gemini 2.5 Pro write bespoke four-panel scripts directly from each scam’s source paragraphs.
9. **Fail loud, never soft.** If a render fails twice, log and flag it for manual review. Never substitute a generic fallback template.

## Scaling past Thailand: what silently broke

Hand-writing 42 four-panel Python scripts took an afternoon for Thailand. Hand-writing 733 scripts across 130+ cities was a non-starter.

For our first multi-country attempt (Germany, 88 comics), I took a shortcut: a regex classifier that matched keywords in each scam’s title to a library of 35 pre-written comic templates, interpolated `{city}` and `{landmark}`, and fired Nano Banana Pro. Germany’s 88 comics finished in an hour.

They also shipped with a silent 9% error rate.

```
PATTERNS = [
(r"shell game|three.?card",          t_shell_game),
(r"pickpocket|u-bahn|s-bahn|metro",  t_pickpocket),   # <-- landmine
(r"fake police|polizei|document",    t_fake_police),
(r"petition|deaf|clipboard",         t_petition),
# ...30 more patterns...
(r".*",                              t_pickpocket),   # fallback
]
def classify(title):
for pattern, template in PATTERNS:
if re.search(pattern, title.lower()):
return template
```

Berlin Scam #3 was titled **“Brandenburger Tor Petition & Bracelet Pickpocket Distraction”** — a fake charity worker at the Brandenburg Gate hands you a clipboard while an accomplice ties a woven bracelet onto your wrist and lifts your wallet. Because `r"pickpocket"` sat above `r"petition"` in the cascade, the script routed it to the generic transit-pickpocket template and drew Priya getting her pocket picked on a U-Bahn train.

Great watercolor. Completely wrong scam.

**Eight of Germany’s 88 comics were misrouted the same way.** Three blind spots hid the bug during deploy:

1. WaveSpeed returned `status: completed` on all 88 jobs.
2. Our file-level check (valid JPEG header, size ≥ 120 KB) passed 100%.
3. Spot-checking six random comics at deploy happened to hit six cleanly routed ones.

We only caught it when a human scrolled the live Berlin page and asked why a Brandenburg Gate petition scam was set inside a subway car.

### Why first-match cascades are structurally unsafe

Reshuffling the regex order doesn’t fix compound scam titles:

- *“Lucky Face” Indian Hair Supplement & Fortune Teller* — fortune teller, supplement pitch, or street compliment?
- *Patpong Ping Pong Show Drink Bill* — tout bait, bill extortion, or nightlife venue?
- *Fake Elephant Sanctuary & Tiger Petting Trap* — elephant riding or drugged-tiger photo op?

Worse, static templates strip out local mechanics. Even if `bracelet` had matched first, a generic bracelet template doesn’t know that the Berlin variant uses a “Help for Deaf Children” clipboard as the distraction. In travel-safety guides, “close enough” illustration destroys reader trust.

## V2: Gemini writes the script

We ripped out the template library and put Gemini 2.5 Pro upstream to write a custom four-panel script for every single scam:

1. Extract the scam title, city, and full narrative paragraphs from the HTML.
2. Send them to Gemini 2.5 Pro alongside the four character profiles and a server-enforced `responseSchema`:

```
RESPONSE_SCHEMA = {
"type": "object",
"properties": {
"character": {"type": "string", "enum": ["margie", "priya", "harry", "marcus"]},
"character_reason": {"type": "string"},
"panels": {
"type": "array", "minItems": 4, "maxItems": 4,
"items": {
"type": "object",
"properties": {
"scene": {"type": "string"},
"dialogue": {"type": "string"},
},
"required": ["scene", "dialogue"],
},
},
},
"required": ["character", "character_reason", "panels"],
}
```

Here is Gemini’s exact JSON output for the Brandenburger Tor scam:

```
{
"character": "margie",
"character_reason": "This scam preys on politeness and a desire
to help a fake charity, which is Margie's key vulnerability.",
"panels": [
{"scene": "Margie stands smiling before Berlin's Brandenburg
Gate. A young woman approaches, holding a clipboard with a
sign that reads 'HELP FOR DEAF CHILDREN'.",
"dialogue": "A signature for the children?"},
{"scene": "Margie focuses on signing. An accomplice's hand
slips a woven bracelet onto her wrist while a third hand
lifts the wallet from her purse.",
"dialogue": "Of course, I'm happy to help."},
{"scene": "The petition-holder is gone. The accomplice
aggressively points to the bracelet on Margie's arm.
Margie looks at her empty, open purse in shock.",
"dialogue": "The clipboard is just a distraction."},
{"scene": "Margie speaks to a German Polizei officer. In
the background, other tourists are being approached by a
similar clipboard group.",
"dialogue": "Lesson learned."}
]
}
```

The regenerated comic shows the Brandenburg Gate, the clipboard, the bracelet accomplice, the lifted wallet, and the Polizei officer.

### Fail loud, not soft

V1 had a silent catch-all fallback (`(r".*", t_pickpocket)`) plus a retry fallback that substituted a generic template whenever an API call failed. V2 enforces a strict contract: **every shipped comic was synthesized specifically for that scam, with zero silent fallbacks.**

- **First render failure** → retry once via Nano Banana Pro’s `/text-to-image` endpoint (whose safety filter is slightly less jumpy than `/edit`).
- **Second render failure** → log the failure and halt that item for human review. Never substitute a generic image.

### The cast-distribution tell

Comparing character assignments across Germany’s 88 comics between V1 and V2 exposed just how badly the V1 fallback had skewed the set:

| Germany cast distribution (88 comics) | V1 | V2 |
| --- | --- | --- |
| Margie (trusting 62-year-old) | 10 | **42** |
| Priya (savvy 34-year-old) | **68** | 28 |
| Harry (charmed 64-year-old) | 6 | 17 |
| Marcus (curious 34-year-old) | 4 | 1 |

V1’s `t_pickpocket` catch-all dumped 68 of 88 German scams onto Priya. Once V2 matched characters to actual scam mechanics, Margie jumped from 10 to 42 appearances — reflecting the reality that German tourist scams skew heavily toward politeness traps, fake charities, and bill padding rather than subway pickpocketing.

## Seven lessons for AI-illustration pipelines

1. **Regex classifiers fail silently on compound inputs.** First-match cascades break as soon as an item combines two mechanics.
2. **Semantic specificity beats rendering polish.** A gorgeous watercolor of the wrong scam is worse than no image at all.
3. **Spend the $0.03 on per-item LLM synthesis.** Having Gemini 2.5 Pro write a custom script from the source paragraphs costs pennies and eliminates template drift.
4. **Enforce server-side JSON schemas (`responseSchema`).** Never regex-parse freeform markdown responses in a batch pipeline.
5. **Ban silent fallbacks.** If an item fails twice, leave the slot empty and flag a human. “88 comics generated” must never mean “80 bespoke comics + 8 generic fallbacks.”
6. **Byte-level checks catch 0% of semantic bugs.** A valid 250 KB JPEG can still depict a subway instead of the Brandenburg Gate. Push semantic accuracy upstream into script generation.
7. **Regenerate the whole batch when upgrading the pipeline.** Re-running all 88 German comics in V2 cost ~$15 and one hour of wall time, lifting the quality of the other 80 comics alongside the 8 broken ones.

### What's next

- **Multimodal LLM-as-judge QA:** Passing each finished JPEG + source scam text to Gemini Vision to verify that the rendered panels match the described setting and props before upload.
- **Pose anchors in character sheets:** Adding explicit action-pose notes (sitting in a tuk-tuk, climbing stairs) where character likeness tends to loosen.
- **Strict 8-word bubble caps:** Keeping dialogue under eight words per panel eliminates the last 1% of typography glitches.

---

### Tools referenced in this post

- [**WaveSpeed**](https://wavespeed.ai/?ref=zonted) — unified REST API across 1,000+ image and video models ([pricing](https://wavespeed.ai/pricing?ref=zonted)).
- [**Gemini 2.5 Pro**](https://ai.google.dev/gemini-api/docs/structured-output) — drives V2 per-scam script synthesis via strict `responseSchema` output.
- [**Apify**](https://www.apify.com?fpr=bernard) — `imageaibot/midjourney-bot` actor used for Round 1 style exploration.
- [**Claude Code**](https://claude.ai/referral/IDrXculiTA) — the agentic coding harness that wrote the build scripts, fired the WaveSpeed batches, uploaded to R2, injected the HTML, and rebuilt V2.

You can browse all 733 comics live across our country hubs: [Thailand](https://tabiji.ai/scams/country/th/), [France](https://tabiji.ai/scams/country/fr/), [Germany](https://tabiji.ai/scams/country/de/), [Greece](https://tabiji.ai/scams/country/gr/), [Spain](https://tabiji.ai/scams/country/es/), [China](https://tabiji.ai/scams/country/cn/), [Indonesia](https://tabiji.ai/scams/country/id/), and [Canada](https://tabiji.ai/scams/country/ca/).
