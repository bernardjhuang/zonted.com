---
title: "Run on Agentic Rails"
author: "Bernard Huang"
date: "2026-08-08"
modified: "2026-08-08"
canonical: "https://zonted.com/posts/agentic-rails/"
category: "Guides"
description: "Seedance 1.5 → 2 → 2.5 made my video pipeline better twice, free. Work on agentic rails inherits each model release. Legacy doesn't."
---

# Run on Agentic Rails

By Bernard Huang · 2026-08-08 · 5 min read

Sometime in the last few days, every video my pipeline produces got better. I didn't touch a prompt. I didn't redeploy a cron. I didn't even notice at first. ByteDance shipped Seedance 2, Tabiji's reel pipeline started pulling it through [Wavespeed](https://wavespeed.ai/?ref=zonted), and the same queue JSON that made [a 3.9-million-view reel](https://zonted.com/posts/how-my-agent-made-a-viral-video/) on Seedance 1.5 started spitting out sharper ones. Then Seedance 2.5 landed and it happened again. Engineering work on my side, both times: none.

## TL;DR

Code you ship is frozen the day it ships. Work that runs on agentic rails — prompts, pipelines, agents around a model slot — quietly gets better every time the labs drop a new model.

- **Seedance 1.5 → 2 → 2.5 made my videos better twice.** Same prompts. Same crons. Two free upgrades.
- My [AI-stack board](https://zonted.com/ai-stack/) is mostly just swapped labels now: Opus 4.7 → 4.8, Codex → GPT 5.5 → 5.6, Fable 5 on the desk. The slots didn't change. Everything under them did.
- Same pattern for content, support, trading, this website. One model release upgrades all of it.
- If you're still on hand-built legacy systems, the painful move is rebuild now. The gap widens every release, not every year.

Not because AI replaces you. Because the people on rails keep getting a higher ceiling for free, and you don't.

## The upgrade I didn't work for

A lab spent months and a mountain of compute making video generation better, then shipped it behind an API. That improvement dropped into one slot in my pipeline and came out the other side as a sharper product while I was asleep. ByteDance has no idea my pipeline exists. I didn't open a ticket, migrate a service, or retrain a person — and when 1.5 gave way to 2 and then 2.5 days later, each release landed in the same slot. Version numbers used to be migration projects. On rails they're just weather, and my pipelines are standing where it rains.

The same pattern keeps repeating across the stack. Image models jumped; my thumbnails got cleaner. Reasoning models jumped; the [trading desk](https://zonted.com/posts/ai-trading-rig/) briefs got sharper mid-season on the same crons and feeds. Two of those agents just [started their own paper funds](https://zonted.com/posts/introducing-autonomous-agent-paper-fund-i-slo/). I didn't upgrade the agents. The model underneath them upgraded.

## Rails vs. artifacts

**Legacy software is an artifact.** The code you shipped in 2023 is exactly as smart today as the day you wrote it. Anything better requires a human to show up, figure it out, change it, and not break it. Leave it alone and it doesn't hold value. It rots. The world moves. It doesn't.

**Agentic rails are the other shape.** What you keep is the boring stuff: prompts, pipelines, tools, evals, crons, guardrails. The intelligence is a slot. You don't own the smarts. You rent whatever is currently best and let the labs fight over who upgrades you next.

> Artifacts depreciate. Rails appreciate.

My [AI-stack board](https://zonted.com/ai-stack/) is the receipt. Over six months the model labels across coding, media, and the trading desk kept rotating while the board's wiring barely moved. Every swap was a free upgrade to whatever sat under that slot. Had I built those jobs as hand-tuned one-offs, each model release would have been a rewrite instead of better output showing up on schedule.

## Every function you hand to agents inherits the curve

Video is the easy example because you can see it. Same prompt, better render. But it's not special to video:

- **Support:** if agents handle the queue, the next model release makes 2am answers more accurate and less brittle. No training day. No new hire.
- **Algos:** if agents research and audit strategies, each release upgrades the analysis in the loop. The scaffolding that catches their dumb mistakes stays. The dumb mistakes get rarer.
- **This site:** posts, metrics, trading briefs, games. Agents on crons. All of it sits under model slots I can swap in an afternoon.

When models get better at long-horizon work, a normal company has to hire, retrain, and reshuffle to capture any of it. A company on rails just wakes up better.

## Transition now or fall behind

Labs ship real upgrades every few months. On rails, you compound on *their* schedule. Off rails, your ceiling is whatever your team can personally keep alive. And the gap with a rails-native competitor doesn't open once a year. It opens every release.

Falling behind won't feel dramatic. It'll feel like watching someone else's costs drop and quality climb every quarter while yours do neither, and never being able to point at the week it started. No big explosion. Just a pile of Seedance-sized free upgrades you weren't set up to catch.

## The hard decision

If your core systems are still legacy — hand-built, artifact-shaped, bottlenecked on human throughput — the rational move is often to **kill them and rebuild on agentic rails now**. Almost every incentive fights that. The old system still works. It cost real money. It has years left in it, if you squint.

That's sunk cost talking. A working legacy system is still depreciating. Rails that barely work yet are appreciating. And the rebuild is cheaper than the last time you priced it, because agents now do most of the heavy lifting — [plan three times, build once](https://zonted.com/posts/plan-3x-build-once/) is an actual workflow for me, not a slogan. I've killed working products before and [buried them in public](https://zonted.com/games/graveyard/). Killing a working codebase is harder. It's also more often the right call.

The next Seedance, the next GPT, and the next Fable are already in training. The only question worth asking is whether anything you own is pointed at the slot when they land.

Get on the rails. This post went out through one.

Disclosure: the Wavespeed link is a referral link.
