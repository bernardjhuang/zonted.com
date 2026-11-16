---
title: "The May Recap: Miami, a Google Wipeout, and $600 in the Red"
author: "Bernard Huang"
date: "2026-06-01"
modified: "2026-06-01"
canonical: "https://zonted.com/posts/may-2026-recap/"
category: "AI Agents & Systems"
description: "May 2026: Consensus in Miami, plan-three-times-build-once, Google wiping Tabiji's traffic overnight, ~$600/month in the red, and four lessons that compounded."
---

# The May Recap: Miami, a Google Wipeout, and $600 in the Red

By Bernard Huang · 2026-06-01 · 5 min read

## TL;DR — May 2026

A dinner in Miami handed me a build workflow that changed my ship rate, Google erased my biggest site’s search traffic overnight, and diversification kept revenue intact.

- **Consensus, Miami:** One dinner conversation turned “plan 3×, build once” into my default loop — one-shotting Chrome extensions and shipping mobile apps in two or three passes.
- **The Google wipeout:** Around May 10, Google dropped Tabiji’s search traffic from 2,172 clicks to near-zero overnight.
- **The P&L:** ~$700/mo in stack burn against ~$125/mo from 45 Tabiji Kindle books sold on Amazon — ~$600/mo in the red, completely insulated from Google search.
- **The operator lesson:** Context-switching across 4–7 active agents now costs 5× what a meeting used to cost.

## Consensus, Miami

The best part of a conference is never the stage. I flew to Consensus in Miami and spent the week trading notes with people who build the way I do.

![Selfie at Consensus in Miami wearing an x402 cap and an Anchorage Digital lanyard.](https://img.zonted.com/resources/may-2026-recap/consensus-selfie.jpg)

*Consensus, Miami. The x402 hat got more conversations started than my badge did.*

The unlock that paid for the trip came from Jen: **plan three times before building once**. Run a frontier model through three independent planning passes, reconcile where they disagree, *then* let one agent implement. I’d [tested a version of this before](https://zonted.com/posts/plan-3x-build-once/), but hearing a practitioner walk through how she runs it daily turned it from an occasional experiment into my default. On my Hermes + GPT-5.5 stack, it’s the difference between a coin flip and a clean ship: Chrome extensions (Veracity) now land in **one shot**, and mobile apps (Palmaura) take **two or three**. Aaron helped sharpen the surrounding workflow, and Gaetano was a standing reminder that one solo operator with sharp taste can out-maneuver an entire team.

![Dinner at a Miami restaurant with two fellow builders, plates of breaded cutlets and fries on the table.](https://img.zonted.com/resources/may-2026-recap/consensus-dinner.jpg)

*The dinner that paid for the flight — in ideas, not schnitzel.*

## Google wiped Tabiji’s search traffic

Then came the gut-punch. Around May 10, Tabiji’s organic search traffic fell off a cliff — from a steady climb to essentially zero overnight. Weeks of fixes haven’t brought it back.

![Google Search Console showing Tabiji's web search clicks climbing through April then collapsing to near-zero around May 10.](https://img.zonted.com/resources/may-2026-recap/tabiji-search-clicks.jpg)

*2,172 web search clicks — then a wall, right around May 10.*

There’s no manual action in Search Console. My read: Google has gotten ruthlessly defensive against new domains in the vibecoded-slop era. A young domain publishing AI-assisted pages at volume matches the exact profile the classifier wants to bury, and Google would rather suppress a thousand legitimate new sites than let one slop farm rank. It stings — but it wasn’t fatal.

## The numbers

The stack costs about **$700/month** to run: Amazon ads, video generation ([Wavespeed](https://wavespeed.ai/?ref=zonted)), cloud hosting, model subscriptions (Claude, GPT, [z.ai](https://z.ai/subscribe?ic=JY9V1BN5ZO)), and a long tail of utilities.

![Monthly cost breakdown totaling about $700: Amazon ads $150, Wavespeed $100, Google Cloud $100, GPT $100, Claude $100, Cloudflare $50, z.ai $30, pubby $30, X $16, Instagram $15, Slack $14, 1Password $4.](https://img.zonted.com/resources/may-2026-recap/costs.jpg)

*~$700/month out the door.*

Against that burn, the top revenue line is [Tabiji books on Amazon Kindle](https://tabiji.ai/books/): 45 units sold across 30 titles in May, bringing in roughly **$125/month**.

![Amazon Kindle Direct Publishing report: 45 units processed across all 30 books, May 1-31, 2026.](https://img.zonted.com/resources/may-2026-recap/kdp-units.jpg)

*45 books sold in May — on Amazon, not on the site Google just buried.*

Net: roughly **$600/month in the red**. Still a lab with a tab rather than a business — but where the revenue came from is the real story.

## What May taught me

**1. Diversify or die.** Google zeroed out Tabiji’s search traffic and barely dented revenue, because book sales live on Amazon and the [18 million social views](https://zonted.com/posts/tabiji-18m-views/) live on Instagram and TikTok. Single-channel dependence kills you quietly; spread across independent surfaces, a platform wipeout is just a Tuesday.

**2. Trade notes with practitioners.** The plan-three-times unlock didn’t come from a model release or a benchmark paper — it came from Jen over dinner. When everyone has access to the same frontier models, your edge is workflow decomposition. One honest conversation with someone in the weeds moved my entire ship rate.

**3. Protect the flow state.** When I’m locked in, I’m holding four to seven parallel agent contexts in my head at once. Breaking that state for a 30-minute meeting costs roughly **5×** what it did pre-AI — reloading the mental state is the tax, not the calendar block. And when you do have focus, watch out for local-maximum traps: chasing more views or prettier UI instead of the bottleneck that moves revenue.

**4. Stack surfaces that combine.** Every capability I build — AI influencers, Kindle books, mobile apps, web games, MCP servers — is another card in the same deck. The outsized wins come from combining them: a viral reel that funnels into a Kindle book, a browser game that memorializes a dead startup, an API that powers a Chrome extension.

## Next

The search wipeout stings, and I’ll keep testing recovery paths. But May proved the underlying thesis: own multiple distribution surfaces, compound the build loop, and guard the focus required to run the orchestra. June is about stacking more cards.
