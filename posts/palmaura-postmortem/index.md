---
title: "PalmAura: a two-week, five-build, two-rejection post-mortem"
author: "Bernard Huang"
date: "2026-06-09"
modified: "2026-06-09"
canonical: "https://zonted.com/posts/palmaura-postmortem/"
category: "Post-Mortems"
description: "Five builds, two App Store rejections, same guideline both times. What Apple's spam wall means for vibe-coded apps, and the lesson I never got to take."
---

# PalmAura: a two-week, five-build, two-rejection post-mortem

By Bernard Huang · 2026-06-09 · 4 min read

Five builds. Two rejections. Fourteen days between them, citing the exact same clause both times. This morning Apple rejected PalmAura a second time under **Guideline 4.3(b) — Design — Spam**, and I’m calling time of death. Here is the autopsy — and what it taught me about shipping vibe-coded apps into Apple’s walled garden.

## TL;DR

Apple has raised a category-level spam wall against vibe-coded apps — and honestly, it’s a defensible wall. My palm-reading iOS app died at the door twice without a single user ever seeing it.

- **Writing the code took two days; App Review took twelve:** The [plan-3x-build-once loop](https://zonted.com/posts/plan-3x-build-once/) one-shotted the Cloudflare Workers backend and built the native Swift app in three passes. Two trips through Apple’s review queue ate the next two weeks.
- **Guideline 4.3(b) rejects your category, not your code:** Apple’s verdict was explicit: “There are already enough of these apps on the App Store.” UI polish and bug-free builds don’t clear a saturated-category gate.
- **Agentic iOS development moves at Apple’s clock speed:** Models write Swift in seconds, but provisioning, code-signing, TestFlight processing, and multi-day human review turn a 60-second web deploy loop into a two-week stall.
- **You can’t practice App Store Optimization from outside the store:** On the web, distribution is a skill test starting day one; on iOS, distribution starts with a gatekeeper’s permission.

PalmAura joins [Kapiko](https://zonted.com/posts/kapiko-postmortem/) in the [project graveyard](https://zonted.com/games/graveyard/).

## What I shipped

PalmAura was a native iOS palm-reading app: snap a photo of your palm, get a daily reading. Freemium model, one photo in, one reading out — a self-contained test of whether my web-honed agentic build loop could ship a native iOS binary.

Mechanically, the build was effortless. The Cloudflare Workers backend compiled cleanly in a [single pass](https://zonted.com/posts/plan-3x-build-once/), and the Swift client came together in three iterations using the plan-3x workflow. By day two, the app was feature-complete, crash-free, and running on physical hardware.

[Video](https://img.zonted.com/resources/palmaura-postmortem/palmaura-demo.mp4)

*PalmAura in motion — palm photo in, daily read out. The app no user will ever download.*

## Two rejections, one guideline

![App Store Connect showing the PalmAura app with a red badge: iOS 1.0 Rejected.](https://img.zonted.com/resources/palmaura-postmortem/app-store-rejected.png)

*The whole story, in one App Store Connect row.*

I submitted build 1 on May 26. It came back rejected under **Guideline 4.3(b) — Design — Spam**. I expanded the feature set, cut new builds, resubmitted, and waited. On June 9 — fourteen days and five builds after initial submission — rejection #2 arrived, citing the exact same boilerplate:

> The app primarily features astrology, horoscopes, palm reading, fortune telling or zodiac reports that duplicate the content and functionality of similar apps in a saturated category. … These app features may be useful, informative or entertaining, and the app may include features or characteristics that distinguish it. However, there are already enough of these apps on the App Store.

![Apple App Review rejection message, June 9 2026: Guideline 4.3(b) Design - Spam, citing a saturated category of astrology, horoscope, palm reading and fortune telling apps.](https://img.zonted.com/resources/palmaura-postmortem/apple-rejection-43b.png)

*The second rejection, June 9. Reviewed on an iPhone 17 Pro Max, version 1.0, build 5.*

Read that paragraph closely. There is no bug report, no crash log, and no complaint about StoreKit billing or privacy disclosures. Apple explicitly concedes that the app “may be useful, informative or entertaining” and may even include distinguishing features — *and rejects it anyway*. Guideline 4.3(b) doesn’t audit your execution; it audits your **category**, and declares the category closed.

This is Apple’s structural defense against the vibe-coding wave. When an agentic workflow can assemble a polished consumer utility in a weekend, the marginal cost of a clone drops to near zero — threatening to bury the App Store under ten thousand slightly restyled palm readers, tarot decks, and Pomodoro timers. Google met the same flood by [de-indexing new domains](https://zonted.com/posts/google-zero-patience-ai-slop/); Apple met it by stationing a bouncer at the door who doesn’t care how well your shirt fits because the club is already full of guys wearing that shirt.

And the honest operator takeaway is that **Apple made the right call.** PalmAura was a clean build in a crowded aisle. It had a neat hook, not a defensible reason to exist. If I ran App Review while AI-generated submissions went vertical, I would enforce the exact same rule.

## The loop is the product

The deeper lesson cost me twelve days of calendar time. My entire studio workflow is optimized around a single metric: time from code edit to live user feedback. On the web, that loop takes sixty seconds — an agent edits a file, pushes to main, Cloudflare deploys globally, and production traffic hits the new code immediately.

iOS subjects that loop to completely different physics. The LLM still writes Swift in seconds, but everything downstream runs in slow motion: Xcode compilation, provisioning profiles, certificate signing, physical device testing, TestFlight binary processing, and finally a multi-day human review queue. **The bottleneck shifts from code generation to platform ceremony** — and ceremony is the one thing an AI agent cannot compress.

Building PalmAura took two days; waiting for Apple to say no twice took twelve. Even if build 5 had been approved, every subsequent paywall test, onboarding tweak, and bugfix would have paid that same multi-day tax. The open web spoiled me, and I have zero interest in giving that speed back.

## The class I never got to take

I didn’t build PalmAura because the world needed another palm reader; I built it to learn a new distribution surface. The goal was to ship a simple consumer utility and learn App Store Optimization (ASO) hands-on — keyword metadata, screenshot conversion rates, ratings velocity, and Apple Search Ads — adding mobile distribution to [my operating deck](https://zonted.com/posts/may-2026-recap/) alongside search, social, and Amazon.

I never got to run a single test because ASO requires being inside the store first. On the web, distribution is an execution problem you can work on the minute you buy a domain. On iOS, distribution starts with a landlord’s permission slip — and the landlord can veto your category before you ever compete for a user.

## To the graveyard

At the bottom of the rejection notice, Apple’s boilerplate helpfully suggests: *“You may consider creating a web app, which looks and behaves like a native app.”* After two weeks in the queue, Apple advised me to go build web apps — the exact thing I already do every day.

I’m not porting PalmAura to the web. It was a distribution exercise, not a high-conviction product, and the category is just as crowded in a browser. Two weeks and a $99 developer fee bought three clear answers: yes, my agent loop can ship native Swift; no, the iteration economics don’t pencil out when review queues eat model speed; and no, Apple isn’t letting generic consumer wrappers through the gate. PalmAura joins [Kapiko](https://zonted.com/posts/kapiko-postmortem/) in [the graveyard](https://zonted.com/games/graveyard/), and the next surface I test will be one where the door opens from my side.
