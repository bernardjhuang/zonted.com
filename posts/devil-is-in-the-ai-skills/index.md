---
title: "The Devil Is in the AI Skills"
author: "Bernard Huang"
date: "2026-05-25"
modified: "2026-05-25"
canonical: "https://zonted.com/posts/devil-is-in-the-ai-skills/"
category: "AI Agents & Systems"
description: "Stock AI couldn't draw my fiancée. An open-source skill on GitHub could. The model is a commodity; the skill is the moat."
---

# The Devil Is in the AI Skills

By Bernard Huang · 2026-05-25 · 6 min read

When I decided to experiment with AI game design over a weekend, I started with my engagement photo with Rebecca. The goal was simple: turn the two of us into walking 96×96 pixel-art sprites.

![Selfie of Bernard and Rebecca after the engagement — both smiling, Rebecca's left hand raised to show her ring.](https://img.zonted.com/resources/devil-is-in-the-ai-skills/engagement.jpg)

*The source photo. Goal: turn this into a walking 96×96 sprite of each of us.*

Round one produced generic stick figures — no glasses, no recognizable hair, and a walk cycle straight out of Microsoft Bob. Round two used the exact same underlying image model wrapped inside an open-source GitHub skill, and nailed both of us on the first pass. By Sunday night, pixel-Bernard was dashing across an Austin side-scroller to reach pixel-Rebecca on a neon rooftop. Same frontier weights; completely different scaffolding.

## TL;DR

Frontier models are commodities. What determines whether they ship usable work is the layer of domain-specific *skills* wrapped around them.

- **Round 1 (Stock AI):** Out-of-the-box Claude Design + GPT-5.5 generated generic NPC sprites that looked nothing like us — hedging that its own output was a “solid usable draft, not yet artist-polished.”
- **Round 2 (Open-source skill):** [`agent-sprite-forge`](https://github.com/0x0funky/agent-sprite-forge) called the same Gemini image weights, but wrapped them in strict prompt rules, deterministic grid postprocessing, and an automated QA repair loop.
- **The playable result:** Using those sprites, GPT-5.5 built a complete Austin side-scroller with coyote time, dash afterimages, and procedural WebAudio. [Play Run to Rebecca →](https://zonted.com/games/run-to-rebecca/)
- **The meta-lesson:** Enterprise and coding skills are saturated; creative-production skills are wide open.

Find the practitioners who already solved your failure mode and borrow their toolboxes.

## Round one: stock AI

I fed our engagement photo into Claude Design out of the box and asked for a walking sprite sheet. Here is what came back:

![Five pixel-art sprite frames of a generic male character — black hair, no glasses, simple grey shirt. No resemblance to Bernard.](https://img.zonted.com/resources/devil-is-in-the-ai-skills/v1-claude-design-him.png)

*Round one, “Bernard.” No glasses. No spiky hair. Could be any generic NPC.*

![Five pixel-art sprite frames of a generic female character in a black hood — no facial features, no recognizable hair shape.](https://img.zonted.com/resources/devil-is-in-the-ai-skills/v1-claude-design-her.png)

*Round one, “Rebecca.” A black hood. The last frame is the ring pose — it's the only thing that survived the abstraction.*

The agent knew it had missed. When it dropped the files into Slack, it pre-hedged:

> This is a solid usable draft, not yet “artist-polished.” The next useful pass would be tightening likeness: her hair shape, your face/glasses, and maybe adding a couple's idle/emote sheet.

The model could diagnose every defect in its own output, yet couldn’t fix them. It had no mechanism to enforce pixel-grid alignment, frame-to-frame proportion lock, or likeness retention.

## Why stock AI couldn't draw

A raw image model treats “draw a 16-frame sprite sheet” as a single illustration prompt. Without external constraints, characters drift in height between frames, baselines wobble so walk cycles jitter, backgrounds bleed into alpha channels, and fine details like glasses evaporate at low resolution.

That isn’t a model-weights problem — it’s a missing-pipeline problem. Calling a frontier image model without a sprite-sheet harness is like asking a senior engineer to ship production code without a compiler or test suite.

## Round two: a skill from GitHub

I mentioned the sprite failure to a builder who had already shipped a 2D game with AI assets, and he pointed me to [`0x0funky/agent-sprite-forge`](https://github.com/0x0funky/agent-sprite-forge) — an open-source skill purpose-built for game-ready pixel art. Its four-stage pipeline:

1. **Prompt scaffolding:** Locks outfit, silhouette, and proportions across all 16 cells (4 directions × 4 frames).
2. **Gemini 3 Pro image generation:** The exact same commercial model weights anyone can call via API.
3. **Deterministic postprocessor:** Slices the grid, strips backgrounds to clean alpha, quantizes the color palette, and normalizes baseline registration.
4. **Automated QA repair pass:** Detects broken or drifting cells, re-renders them against the canonical pose, and reassembles the final sprite sheet.

I fed the exact same engagement photo into `agent-sprite-forge`. Minutes later, it returned a 384×768 master sheet and animated walk cycles for all four directions.

## The receipts

![The agent-sprite-forge output: a 4-direction, 4-frame sprite sheet for Bernard (top half, glasses + spiky hair) and Rebecca (bottom half, long flowing hair, dark outfit). Both characters are recognizable as themselves.](https://img.zonted.com/resources/devil-is-in-the-ai-skills/v2-forge-combined-v2.png)

*Round two output. Bernard has glasses and spiky hair. Rebecca has the long flowing hair from the photo. The walk cycles read correctly in all four directions.*

![Animated GIF of the Bernard sprite walking right — four-frame cycle, glasses and spiky hair visible.](https://img.zonted.com/resources/devil-is-in-the-ai-skills/v2-forge-bernard-walk.gif)

*Bernard, walking right.*

![Animated GIF of the Rebecca sprite walking right — four-frame cycle, long dark hair, dark outfit.](https://img.zonted.com/resources/devil-is-in-the-ai-skills/v2-forge-rebecca-walk-right.gif)

*Rebecca, walking right.*

Those two sprites now pace back and forth at the bottom of [my About page](https://zonted.com/about/). Round one looked like a 2003 placeholder; round two looks like us.

## Then I built a game

Once the characters actually looked like us, the obvious next question was what world to drop them into. I had GPT-5.5 build a playable side-scroller: Bernard sprints from South Congress past the food trucks, over Lady Bird Lake under the Congress Avenue bridge bats, past the Capitol dome and UT Tower, all the way to Rebecca waiting on a neon rooftop.

![Annotated level overview of the Run to Rebecca game showing the Austin-themed side-scroller from start to finish: SOCO sign, food trucks, Lady Bird Lake, Capitol dome silhouette, UT Tower, Frost Bank crown tower, and Rebecca on a rooftop at the end. Annotated with labels for MOVE (coyote + buffered jump), DASH (Shift J K + shake), SAVE (checkpoint lanterns), JUICE (particles + zone toasts), SOUND (procedural WebAudio), WIN (Rebecca's final stats).](https://img.zonted.com/resources/devil-is-in-the-ai-skills/game-level-overview.png)

*The level. Austin landmarks, six checkpoint lanterns, three hearts and three faces collectible per run. Rebecca is the finish line.*

Three iterations took it from rough prototype to a tight little game — v2 wired the sprite sheets into a tilemap, v3 added a painterly parallax Austin skyline, and v4 added the game-feel polish:

- **Movement feel:** Coyote time, jump buffering, variable jump height, rechargeable air-dash, and directional screen shake.
- **Checkpoints:** Six lanterns along the route so missed jumps don’t reset the whole run.
- **Visual juice:** Dash afterimages, speed streaks, landing dust, pickup bursts, and confetti on completion.
- **HUD & audio:** Progress bar, speedrun timer, zone title toasts, and a procedural WebAudio synth generating the ambient bed and all SFX in real time.

![Polish review board for Run to Rebecca v4, showing active gameplay screenshot, the Rebecca-reached win screen, the list of v4 polish items (Celeste-ish movement, dash with recharge, checkpoint lanterns, procedural WebAudio, presentation), and a panorama strip of the level with checkpoints and game-feel callouts.](https://img.zonted.com/resources/devil-is-in-the-ai-skills/game-polish-board.png)

*The v4 polish board — the stuff that makes a prototype feel like a tiny finished game.*

![Win screen of Run to Rebecca: 'Rebecca reached' in white serif text on a dark overlay with a pink heart, run stats showing time, faces collected, and hearts collected, with the Austin neon rooftop visible behind the panel.](https://img.zonted.com/resources/devil-is-in-the-ai-skills/game-finish.png)

*The win state. No flagpole needed.*

[Play Run to Rebecca →](https://zonted.com/games/run-to-rebecca/)

None of that would have happened if I had stopped at round one. Stick figures don’t make you want to build a world around them; recognizable sprites do.

## The devil is in the AI skills

The model didn’t improve between round one and round two. The skill wrapper around it did.

Base models are a depreciating commodity — whatever flagship you use today gets leapfrogged in ninety days. The durable leverage lives in the skill layer that translates raw model capability into finished domain artifacts. Right now, default agent skill libraries are overwhelmingly skewed toward office work and software engineering, because that’s where enterprise budgets went first:

- Slide-deck, report, and spreadsheet generators (PPTX, DOCX, XLSX)
- PDF extraction and form-filling pipelines
- Code review, debugging, PR automation, and security-audit harnesses

What’s missing from the default kit is almost the entire creative stack: sprite rigging, animation timing, game-feel tuning, audio mixing, video assembly, and design-system enforcement. The creative skill layer is two years behind the enterprise coding layer — and that gap is where the highest-leverage open-source work is right now.

## Chauffeur knowledge

There’s an old story about Max Planck and his chauffeur. After winning the Nobel Prize, Planck delivered the same lecture across Germany so many times that his chauffeur memorized it word for word. One evening they swapped outfits, and the chauffeur delivered the lecture flawlessly — until a physicist in Munich stood up and asked a thorny follow-up. Without missing a beat, the chauffeur replied: “I’m surprised to hear such an elementary question in an advanced city like Munich. I’ll let my chauffeur answer it.”

Charlie Munger told that story to warn against confusing surface fluency with deep mastery. In the AI-skills era, there’s a corollary: *you don’t need to be Planck in every domain — you just need to find the practitioner who already built the skill.*

Hours of searching Hugging Face and GitHub trending wouldn’t have surfaced `agent-sprite-forge`. Describing my exact failure mode to one builder who had already shipped pixel art did it in thirty seconds. That’s now my default loop whenever I enter a new medium — short-form video, voice agents, generative music, or 2D games: find the practitioner in the weeds, ask what skill wrappers they actually run, and skip six months of trial and error.

## The takeaway

Stock AI couldn’t draw my fiancée. An open-source skill using the exact same model weights nailed it on the first try — and turned a weekend experiment into the sprites on [/about/](https://zonted.com/about/) and the side-scroller at [/games/run-to-rebecca/](https://zonted.com/games/run-to-rebecca/).

Stop waiting for the next model release to fix your output quality. The model is already good enough. The devil is in the skills.

— Bernard
