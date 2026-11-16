---
title: "Human-in-the-Loop: How AI Orchestrator Became My Full-Time Job"
author: "Bernard Huang"
date: "2026-04-10"
modified: "2026-04-10"
canonical: "https://zonted.com/posts/human-in-the-loop/"
category: "AI Agents & Systems"
description: "I have 20 AI agents running 24/7. The fantasy was that they'd work for me. The reality is that I work for them — and Big Tech collects rent from both of us."
---

# Human-in-the-Loop: How AI Orchestrator Became My Full-Time Job

By Bernard Huang · 2026-04-10 · 5 min read

I have twenty AI agents running around the clock. Every hour or two, a cron job fires and an agent posts to Pinterest, enriches destination data, renders a video reel, scrapes Reddit, or pulls an analytics report without me touching the keyboard. On paper, that makes me an AI orchestrator — a conductor directing a fleet of autonomous workers. In practice, I'm their IT support staff.

"Human-in-the-loop" was coined to describe humans supervising AI as a safety gate. When you actually run a 20-agent fleet, it means the opposite: the agents do the creative and production work, and the human's job is keeping the loop from stalling.

## TL;DR

Running 20 autonomous AI agents 24/7 doesn't buy you passive leverage — it puts you on permanent PagerDuty as both product strategist and full-time sysadmin.

- **24/7 agents mean 24/7 on-call** — when a Slack webhook channel goes quiet, you're dropping dinner to debug expired cookies, rate limits, or dead crons.
- **30–40% of time goes to "the jank"** — weekly model releases (MiniMax to Veo 3.1 Lite to Seedance 2.0) mean your stack is perpetually mid-migration.
- **Customer-in-the-loop economics** — your agents work for you, you work for your agents, and model providers collect token rent from both.

## On-Call

My agents live in Slack. Every workflow has its own channel — `#pinterest`, `#video-reels`, `#enrichment`, `#analytics`. When the fleet is healthy, those channels scroll with quiet completion receipts. When something breaks, a channel goes silent.

I check Slack constantly, not for messages from humans, but for heartbeats from bots. Did the Pinterest job fire? Did the six-scene reel finish rendering? Did the enrichment script hit a 429? When a channel goes dark for two hours, a familiar spike of dread hits: an agent is down, throughput is zero, and I need to get to a terminal to read the logs. I've built a 24/7 workforce, which means I've put myself on 24/7 PagerDuty.

## The Jank

Roughly 30 to 40 percent of my week goes to plumbing: diagnosing silent failures, upgrading CLI harnesses, swapping model endpoints, tuning fallback chains, and working around rate limits. Not building product. Not refining strategy. Just keeping the rig upright.

It never stabilizes because the underlying stack mutates every week. We built our reel pipeline on [MiniMax Hailuo](https://platform.minimax.io/subscribe/token-plan?code=B8atrcvv5N&source=link) because the unit economics worked. Then [Veo 3.1 Lite cut prices](https://zonted.com/posts/wavespeed/) on April 7 to match it, so we spent a day benchmarking and migrating. Days later, Seedance 2.0 dropped with noticeably better motion quality, kicking off another round of prompt rewrites and pipeline tests. You're never maintaining a finished system; you're maintaining a system that is perpetually mid-upgrade.

Meanwhile, the mundane failures compound. Session cookies expire. Scrapers hit new Cloudflare rules. Upstream APIs silently tighten concurrency limits. OAuth tokens lapse. One flaky dependency is a ten-minute fix; across twenty agents, something is breaking every single day.

## Two Jobs

Running an agent fleet forces you to context-switch between two incompatible jobs all day:

- **Orchestration (the leverage):** Deciding what the fleet should build, grading output quality, making taste calls on hooks and formats, and picking which distribution channels deserve more compute.
- **Maintenance (the tax):** Rotating API keys, patching broken DOM selectors, restarting wedged launchd daemons, and figuring out why a Pinterest upload needs three retries before the CDN accepts it.

I'm simultaneously the creative director and the night-shift sysadmin — and neither role is easy to delegate. The taste calls are the entire moat, while the debugging requires having the entire 20-agent dependency graph in your head.

In [AI Psychosis](https://zonted.com/posts/ai-psychosis/), I wrote about trading manual grunt work for high-frequency decision fatigue. This is the operational corollary: I didn't just trade up to a higher-level job; I bolted an unglamorous DevOps job underneath it.

## The Real Product

The internet is splitting into two camps: solo operators who use agent fleets to ship at the volume of a 15-person media company, and passive consumers scrolling through what those fleets generate. But even on the builder side, raw production volume isn't a moat for long — when everyone can spin up twenty crons, distribution gets harder at the exact rate generation gets cheaper.

And beneath all of us, the labs and cloud providers collect rent. They sell the tokens, meter the APIs, and train next quarter's frontier models on the public web traffic our agents generate. You're the human-in-the-loop, which also makes you the customer-in-the-loop: paying for compute to run agents that feed platforms that train the next model you'll rent.

The agents work for me. I work for the agents. And we all work for the token meter.

## The Loop

Right now I'm working twelve-hour days plus weekends. Because the crons don't take Saturday off, my brain doesn't either. I'm not conducting a frictionless symphony of intelligence; I'm babysitting brittle bash scripts, session cookies, and JSON schemas that happen to call a frontier LLM.

Yet turning the fleet off is unthinkable. Even with 35% of my week lost to maintenance, twenty agents running around the clock ship more data enrichments, reels, pins, and code than I could ever produce by hand. That's the bargain of solo AI orchestration in 2026: you get a twenty-person workforce that never sleeps, and the price is that you never fully log off either.
