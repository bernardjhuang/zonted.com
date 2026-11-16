---
title: "Plan 3×, Build Once: How Three Models Plan What One Model Ships"
author: "Bernard Huang"
date: "2026-05-22"
modified: "2026-05-22"
canonical: "https://zonted.com/posts/plan-3x-build-once/"
category: "AI Agents & Systems"
description: "We asked Opus 4.7 and GPT-5.5 to independently plan the same VeracityAPI feature."
---

# Plan 3×, Build Once: How Three Models Plan What One Model Ships

By Bernard Huang · 2026-05-22 · 7 min read

**Update, September 24, 2026:** VeracityAPI, the product behind this post’s receipt, is retired. The loop outlived it. [Read the post-mortem →](https://zonted.com/posts/veracity-postmortem/)

I asked Opus 4.7 and GPT-5.5 to independently plan the same new feature, then handed both plans to Gemini 3.1 Pro to pick the winning combination. One sentence in Gemini's audit earned the entire workflow:

> Opus designed a consumer SaaS application (beautiful, real-time, client-side, targeting writers). GPT-5.5 designed a B2B API marketing tool (pragmatic, server-tied, conversion-focused, targeting engineers/QA). Because your goal is to sell API keys for VeracityAPI, GPT-5.5 has the winning product strategy, but Opus has the winning technical architecture.

Each model produced a half-right spec. Single-model planning would have shipped one of those halves; Gemini's audit synthesized a build neither planner would have written alone.

## TL;DR

For every complex build, three models write the spec before one model writes the code: Opus 4.7 and GPT-5.5 draft independent plans, Gemini 3.1 Pro reconciles them into a Goldilocks spec, and GPT-5.5 one-shots the implementation.

- **Three one-shot builds shipped so far:** the Veracity Chrome extension, the Palmaura backend, and the VeracityAPI Text Linter (14 milestones).
- **Complementary blindspots:** Opus designs clean isomorphic architecture for the wrong buyer; GPT-5.5 nails B2B conversion strategy on fragile technical primitives; Gemini cold-audits both and keeps the working half of each.
- **10× ROI on planning tokens:** Three planning passes cost ~$2–$4 in API tokens vs. ~$20–$60 for the wasted implementation pass they prevent.

## The loop

Every complex feature runs through four steps before a line of application code gets written:

1. **Opus 4.7 plans it cold.** Fresh context, zero cross-talk.
2. **GPT-5.5 plans the exact same prompt cold.** Fresh context, independent framing.
3. **Gemini 3.1 Pro audits both plans.** Scores the tradeoffs, flags what both models missed, and writes a reconciled Goldilocks spec.
4. **GPT-5.5 executes the Goldilocks spec.** Subagent-driven development steps through the reconciled milestones in a single implementation pass.

## The receipt: VeracityAPI Text Linter

We were shipping an AI text linter for VeracityAPI at `/tools/style-editor`, and the product surface had four open design forks:

- **UX**: Hemingway-style editor, static form, or an open-source agent skill suite on GitHub?
- **Deployment**: Cloudflare Worker only, open-source repo, or both?
- **Architecture**: `contenteditable`, textarea overlay, or raw JSON with no editor UI?
- **Positioning**: Writers, developers, or enterprise trust teams?

Given the same brief, each planner anchored hard on its own priors.

### What Opus 4.7 proposed

I gave Opus two passes with slightly different lead-in prompts, and it returned two distinct framings:

**Plan A — open-source agent skill suite.** Publish to GitHub as `veracityapi/ai-text-risk-skills` with five skills: ensemble detector, author-style-compare, provenance-probe, source-claim-audit, and benchmark harness. Heavy emphasis on multi-signal risk reports ("evidence, not accusations"), local model execution, and BYOK for search providers.

**Plan B — Hemingway-style editor.** A live browser app at `/tools/style-editor` built on `contenteditable` with overlay `<mark>` spans, backed by a pure-TypeScript calculator shared between the browser bundle and Cloudflare Worker. Targeted "Hemingway alternative" SEO with preloaded sample text and a live metrics sidebar.

Both Opus specs were architected cleanly, and both were aimed at the wrong buyer.

### What GPT-5.5 proposed

GPT-5.5 returned a single, commercial-first spec:

- "Veracity Editor" at `/editor` — developer linter positioning rather than a Hemingway clone
- Textarea + mirrored highlight overlay (avoiding `contenteditable`)
- Fast Scan (deterministic, local) + Deep Scan (LLM-backed, paid) as the API conversion bridge
- Authenticated `/v1/analyze-style` endpoint matching existing API conventions
- Privacy defaults: `store_content=false`, with zero text leaving the browser on Fast Scan
- VeracityAPI action spine: `allow / revise / human_review / reject`

GPT nailed the buyer and conversion funnel, but picked clumsy technical primitives and glossed over the shared module architecture.

### What Gemini 3.1 Pro said

I handed all three specs to Gemini 3.1 Pro for a cold audit:

![Gemini 3.1 Pro's synthesis verdict: Opus designed a consumer SaaS application, GPT-5.5 designed a B2B API marketing tool, GPT-5.5 has the winning product strategy but Opus has the winning technical architecture.](https://img.zonted.com/resources/plan-3x-build-once/gemini-synthesis.png)

*Gemini 3.1 Pro auditing the Opus and GPT-5.5 plans for the VeracityAPI Text Linter. The split between “winning product strategy” and “winning technical architecture” is the whole game.*

When I asked Gemini to itemize what each model got right and wrong, its critique of GPT-5.5 caught a failure mode I had missed completely:

![Gemini's audit of what GPT-5.5 got right and wrong. Right: persona match for developers not students, warning about Python ML dependency hell, riding the MCP distribution wave. Wrong: web UI first sequencing, missed context window economics for agents, assumed local ML is required.](https://img.zonted.com/resources/plan-3x-build-once/gemini-gpt-audit.png)

*Gemini's audit of GPT-5.5's plan. The “context window economics” miss is the one I'd never have caught on my own — humans read JSON differently than agents do.*

**What GPT-5.5 got right:**

1. **Persona match.** We sell API keys to developers building AI pipelines, not students trying to beat `turnitin.com`. An open-source GitHub repo speaks their language natively.
2. **Avoiding local ML support tickets.** Python dependency hell (PyTorch, CUDA versions, HuggingFace transformers) kills open-source adoption. If a free tool requires downloading a 5GB model and debugging GPU drivers, developers abandon it.
3. **Riding the MCP wave.** Packaging the analyzer as an MCP server gives it immediate distribution inside Claude Desktop, Cursor, and enterprise orchestrators.

**What GPT-5.5 got wrong:**

1. **"Web UI first" sequencing.** GPT sequenced the web editor before the repo, even though the repo ships faster and can power the web UI afterward.
2. **Context-window economics.** GPT designed the JSON schema as if a human were reading it. For an *agent* skill, returning sentence-by-sentence stylometric breakdowns bloats the context window and burns user tokens. Agent output has to be aggressively summarized (e.g., `risk_band: "high", primary_reason: "Low sentence variance"`).
3. **Assuming local ML is mandatory.** GPT assumed deep classifiers had to run locally, whereas the repo can run fast deterministic heuristics locally and hand heavy inference to VeracityAPI.

**What Opus got right:**

- Pure TypeScript analyzer shared across browser and Worker — the isomorphic architecture is the core technical unlock
- Browser-side Fast Scan so viral free-tool traffic never burns Worker CPU, D1, or model budget
- MCP server importing the exact same analyzer module
- `/tools/style-editor` as the canonical URL for cleaner SEO and tool taxonomy than bare `/editor`

**What Opus got wrong:**

- `contenteditable` editor — browser selection, input, and cursor-offset hell when a textarea overlay ships faster and breaks less
- Consumer "Hemingway alternative" persona — novelists do not buy VeracityAPI keys
- Full local writing-app ergonomics — scope creep for what should be a diagnostic inspector
- Public no-auth JSON endpoint — redundant once the browser bundle runs the pure-TS analyzer locally

## The Goldilocks plan

Gemini combined the surviving pieces into a single 25-section implementation spec:

- **Architecture (from Opus)**: Pure-TS analyzer shared across the browser bundle, Worker, and MCP tool, with browser-side Fast Scan protecting server compute.
- **Product strategy (from GPT-5.5)**: Developer linter positioning, textarea + mirrored highlight overlay, Fast-to-Deep Scan upsell, VeracityAPI action spine, and zero-retention privacy defaults.
- **Copy correction (from Gemini)**: Drop "open-sourced" claims until the analyzer package is actually published; call it "transparent heuristics" at launch.

## The one-shot

With the Goldilocks spec locked, GPT-5.5 stepped through all 14 implementation milestones via subagent-driven development: shared analyzer contracts → parser → dictionaries → metrics → scoring → browser bundle → public page → validation → endpoint → conversion path → MCP → docs → eval harness → feedback.

That made three consecutive one-shot builds through the same three-model loop:

1. **Veracity Chrome extension.** Opus planned a toolbar popup; Gemini overruled it for a persistent side panel on context-window and workflow grounds. Shipped on first deploy.
2. **Palmaura backend.** Clean one-shot on the Cloudflare Worker backend (though the iOS client still hit normal Swift, Xcode, and App Store review friction).
3. **VeracityAPI Text Linter.** 14 milestones executed straight from the Gemini-reconciled spec.

## Why three, not two

Left to plan alone, each frontier model defaults to a predictable house bias:

- **Opus 4.7** over-indexes on architectural purity, happily engineering an elegant system for the wrong customer.
- **GPT-5.5** over-indexes on commercial pragmatism, nailing the B2B funnel while cutting corners on technical primitives.
- **Gemini 3.1 Pro** is a sharper cold critic than primary architect — it spots where Opus and GPT-5.5 talk past each other and flags what neither caught.

Stopping at two models skips the referee. If you ask Opus to critique GPT-5.5 (or vice versa), both models defend their own initial framing. Gemini enters with no ego invested in either draft.

## The economic argument

Three planning passes consume 5,000–9,000 input tokens and a similar output budget per planner, plus 3,000–5,000 tokens for Gemini's audit — roughly **$2–$4 in API costs** total.

The implementation pass that follows runs 50,000–200,000 tokens, or **$20–$60 in API costs**. When a single-model spec ships the wrong architecture or product framing, rewriting it doubles the build bill to **$40–$120**. Spending $2–$4 up front to save a $20–$60 rebuild is the easiest trade in our stack.

## What this isn't

1. **Not a formal benchmark.** It is a workflow receipt across three production builds (Chrome extension, mobile backend, hosted SaaS tool).
2. **Model personas drift across releases.** Opus 4.7 won't always be the architecture purist and GPT-5.5 won't always be the funnel pragmatist. Re-audit role assignments when frontier checkpoints update.
3. **The referee still needs human review.** On an earlier build, Gemini favored Opus's UX framing when GPT-5.5's was clearly better, and I overruled it before code generation started.
4. **"One-shot" means one spec, not zero code review.** The first implementation pass compiles, runs, and clears milestone acceptance tests, with normal polish during review — never a thrown-away architecture.

## The takeaway

Single-model planning ships one model's blindspots. Three-model planning forces two competing priors onto the table and lets a cold third model assemble the spec neither would have written alone. The first time you run three planning passes for a single feature, it feels like overhead; by the third build, single-model planning feels like shipping blind.

— Bernard
