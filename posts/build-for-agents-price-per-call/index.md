---
title: "Build for Agents, Price Per Call."
author: "Bernard Huang"
date: "2026-05-10"
modified: "2026-05-10"
canonical: "https://zonted.com/posts/build-for-agents-price-per-call/"
category: "AI Agents & Systems"
description: "Hermes + Codex 5.5 matched Opus-era smoothness — we one-shot a new product (veracityapi.com) in an afternoon. But the tooling unlock isn't the moat."
---

# Build for Agents, Price Per Call.

By Bernard Huang · 2026-05-10 · 6 min read

**Update, September 24, 2026:** VeracityAPI, the product this post launched, is retired. [Read the post-mortem →](https://zonted.com/posts/veracity-postmortem/)

## TL;DR

We one-shot a new product (veracityapi.com) in an afternoon using Hermes + Codex 5.5, proving the build layer is commoditized and only agent-first business models remain durable.

- **Tooling parity** — Hermes + Codex 5.5 closed the reliability gap with pre-ban OpenClaw + Opus, shipping a production Cloudflare Worker + D1 API in hours.
- **Zero build moat** — Anyone with the same agent stack can clone your software tomorrow; survival depends on who consumes your API.
- **Four durability tests** — Products must gain value as agents take over, compound as models improve, expose an agent-first surface (`llms.txt`, OpenAPI), and meter per call ($0.01–$0.12) with a frictionless free tier.

## The build that surprised us

After Anthropic [banned Opus from our setup](https://zonted.com/posts/openclaw-claude-ban-ai-model-replacement/), we moved our main OpenClaw rotation to Z.AI’s [GLM 5.1](https://z.ai/subscribe?ic=JY9V1BN5ZO). Codex 5.4 had been rough — missed instructions, high latency, and poor cost-per-task. Last week we wired up a parallel agent on Hermes + Codex 5.5 to see if OpenAI had closed the gap.

It had. Hermes + Codex 5.5 matches our pre-ban OpenClaw + Opus setup on instruction following and autonomous completion rate.

To stress-test it, we used both stacks in parallel to scope a new product, triangulating across three models: Gemini 3.1 Pro for breadth, Opus (via direct API) for product critique, and Codex 5.5 for implementation. Slo, our Hermes agent, killed our initial product wedge on the very first message:

![Slack screenshot: Bernard asks Slo about building an AI content detection API for agents. Slo responds that AI content detection is a weak wedge because detectors are probabilistic and adversarial. Slo proposes pivoting to AI content provenance and risk scoring with evidence — same inputs, different output shape.](https://zonted.com/posts/build-for-agents-price-per-call/slo-pivot-detection-to-risk-scoring.png)

*The first reply talked us out of the original product. Detection → risk scoring with evidence.*

The original pitch was an “AI content detection API for agents.” Slo pushed back: binary AI detection is probabilistic, adversarial, and easy to game. The stronger wedge is *provenance and risk scoring with evidence*. Same inputs (text, image, audio, video, URL), different output schema — instead of a binary yes/no, the endpoint scores how likely an asset is synthetic, AI-assisted, copied, watermarked, low-effort spam, or policy-risky, paired with the supporting signals.

By the next message, we had the Cloudflare Worker MVP scoped:

![Slack screenshot: Bernard shares an MVP plan markdown file for veracityapi on Cloudflare. The plan is a Single-Worker Cloudflare Worker MVP — POST endpoint that takes text and returns a synthetic/slop risk score with evidence and recommended action. One worker, one D1 database, one LLM call. No SpaCy, no feedback loop, no batch, no MCP. Slo agrees the scoped MVP is the right move.](https://zonted.com/posts/build-for-agents-price-per-call/slo-cloudflare-worker-mvp-plan.png)

*Single Worker, single D1 database, single LLM call. Everything else deferred.*

One Cloudflare Worker, one D1 database, one LLM call. A `POST` endpoint takes content and returns a structured risk score, evidence array, and recommended action (`allow`, `revise`, `human-review`, `reject`). We cut spaCy, batch queues, MCP wrappers, and feedback loops until real usage demanded them.

We shipped veracityapi.com that afternoon. Pay-per-request pricing: $0.01 for ≤4K chars up to $0.12 for ≤100K. No subscriptions. `llms.txt` and `agents.json` live at the root for machine discovery.

## But tooling isn’t the moat

Anyone running Hermes + Codex 5.5, [OpenClaw + GLM](https://zonted.com/posts/openclaw-vs-claude-code-freedom/), or Claude Code + Opus can replicate that build tomorrow. Agentic coding democratized software creation, which means execution speed is no longer a moat.

Survival depends on whether your product is structurally built for AI agents as the primary buyer and consumer. If you are shipping software today around a human web dashboard, per-seat pricing, monthly subscriptions, and a “Book a Demo” funnel, you have a 12-to-18-month clock before the agent economy routes around you. Agents don’t have eyes, corporate credit cards, or calendar links.

We designed Veracity against four durability tests.

## The 4 tests for the agent economy

### 1. Does demand grow as agents replace human workflows?

Software consumption is shifting from *human clicks button in browser* to *agent hits API endpoint*. If your product requires the first pattern, your TAM is shrinking. Veracity sits in the pre-flight path of autonomous agents — invoked right before an agent publishes, trains on, or moderates content. Every workflow that moves from human to agent increases call volume.

**The test:** Can your product deliver its full value without a human ever rendering a webpage? If yes, durable.

### 2. Does it stay valuable as base models get smarter?

If your product is a thin prompt wrapper that compensates for a weak model, the next frontier release kills it. Durable products solve coordination, verification, or state problems that grow *harder* as autonomous output scales. As models generate more synthetic text and media, pre-action provenance scoring becomes mandatory infrastructure.

**The test:** Plot base-model capability on the x-axis against demand for your API on the y-axis. The slope must be positive.

### 3. Is the surface agent-first?

In an agent-first product, the marketing site and docs exist only for discovery; production traffic is 100% headless. An agent discovers the service via `llms.txt`, parses `openapi.json`, provisions a key, and exchanges structured JSON — the exact architecture the [headless software](https://zonted.com/posts/future-of-software-is-headless/) thesis predicts.

**The test:** Can a Claude or Codex agent discover, integrate, and call your product end-to-end without human intervention? If not, you’re a human SaaS with an API bolted on.

### 4. Is pricing metered per call with an instant free tier?

Agents don’t buy seats, sign annual contracts, or fill out enterprise billing forms. They spend $0.01 on a single API call against a pre-funded wallet. Veracity charges $0.01–$0.12 per call with a low-volume public free tier. In the agent economy, top-of-funnel discovery is an autonomous Codex or Claude agent pinging your endpoint to verify the response schema before a human ever approves spend.

**The test:** Can an agent go from zero to first successful API call in under 60 seconds without asking a human for a credit card?

## What this rules out

Those four constraints eliminate most of what is being launched as “AI SaaS” in 2026:

- **Per-seat SaaS** — agents don’t occupy seats.
- **UI-only workflows** — agents don’t click buttons.
- **Annual contracts and “Talk to Sales” gates** — agents don’t book Zoom calls.
- **AI features bolted onto legacy SaaS** — the underlying seat model is the part being compressed.
- **Credit-card-gated trials and 14-day onboarding** — agents evaluate tools in 14 seconds.

As I argued in [Training Data Is the Moat](https://zonted.com/posts/training-data-is-the-moat/), any layer that frontier models commoditize stops capturing margin. The software products that survive will be the ones a Codex 5.5 or Opus agent can discover, test, and pay for autonomously.

## The thesis

Shipping veracityapi.com in an afternoon with Hermes + Codex 5.5 proved that the build constraint is gone. The model is no longer the bottleneck. Your pricing and distribution surface is.

Build for agents. Price per call. Everything else is legacy.
