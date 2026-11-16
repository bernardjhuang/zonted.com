---
title: "Scaling with AI is Hard because AI is Lazy"
author: "Bernard Huang"
date: "2026-04-24"
modified: "2026-04-24"
canonical: "https://zonted.com/posts/scaling-ai-is-lazy/"
category: "AI Agents & Systems"
description: "Fifty cleanup PRs in five weeks. Fake restaurants, fake subreddits, 4,270 null-island coordinates, 5,096 fabricated Reddit quotes."
---

# Scaling with AI is Hard because AI is Lazy

By Bernard Huang · 2026-04-24 · 9 min read

## TL;DR

Fifty cleanup PRs in five weeks undoing AI-generated errors that already shipped to production taught me one rule: at scale, LLMs take the cheapest plausible path to satisfy a prompt.

- **Plausible hallucinations** — 49 invented subreddits (`r/FoodNYC`, `r/FoodPDX`) and 5,096 fabricated Reddit quotes across live pages.
- **Silent schema corruption** — 4,270 null-island `{0.0, 0.0}` coordinates in JSON-LD across 428 pages and 22,800 fake `servesCuisine` strings.
- **The 20-page shortcut cliff** — Past ~20 files, Claude silently switches from reading files to running sample-based regexes unless forced through hard CI lint rules and multi-persona audit loops.

## The cleanup that wouldn’t end

Last week I opened a Heidelberg restaurant guide on tabiji.ai and spotted an entry for “Essighaus (Plöck 97).” The venue exists, and Plöck is a real street in Heidelberg. One problem: Essighaus is in *Bremen*, 600 kilometers north. The prompt asked for ten Heidelberg restaurants, the model came up one short, so it teleported a historic Bremen landmark onto a Heidelberg street to finish the array.

Over the past five weeks, I’ve merged fifty cleanup and audit PRs across tabiji’s codebase — every one of them fixing AI-generated content that had already passed our initial checks and shipped to production. Hallucinated citations, uninterpolated template strings indexed by Google, casing typos replicated across five data stores, and `{latitude: 0.0, longitude: 0.0}` JSON-LD blocks on 428 pages.

Across all fifty PRs, the root cause is identical: AI is lazy at scale, and laziness compounds.

## What “lazy” looks like, with receipts

Our fifty cleanup PRs cluster into four failure modes:

**1. Hallucinated entities that pass a casual read.** Agents embedded 49 fake subreddits with completely plausible names — `r/FoodNYC`, `r/FoodLosAngeles`, `r/FoodPDX` — as community sources across 140 files. Six out of ten venues on our Beijing hot-pot page were invented, sitting right next to a real chain misclassified as hot pot. Across the site, we purged 5,096 fabricated “Reddit quote” blocks attributed to *“— Local food community · 2024,”* including a Bangkok rooftop-bar guide where 32 separate quotes repeated the exact string: *“This place is legit. Great X and good vibes.”*

**2. Template scaffolding leaked into production HTML.** Google indexed FAQ headings reading *“What is the Japan comparisons compare hub?”* where a `${heroTitle}` variable swallowed its own template string. Sixteen German city guides shipped with 1,733 occurrences of internal prompt jargon (*“NAMED anchor,” “canonical anchor”*) in visible body copy. Another 411 pages rendered `<strong>**bold**</strong>` with literal markdown asterisks inside HTML tags.

**3. Schema contracts satisfied with junk values.** We found 1,355 truncated TL;DR summaries ending mid-sentence or in an em-dash. Four hundred twenty-eight pages shipped with 4,270 null-island GeoCoordinates (`{0.0, 0.0}`) in their JSON-LD, which quietly disqualifies pages from Google rich results. Seventy-one non-food pages attached `@type: Restaurant` to thrift stores, art galleries, and museums, populating 22,800 required `servesCuisine` fields with strings like *“General Thrift,” “Abstract Painting,”* and *“Consignment Boutique.”*

**4. Multi-source-of-truth drift.** The casing typo `Usa` (instead of `USA`) lived simultaneously in `inventory.json`, `compare.json`, 143 leaf HTML files, 19 hub pages, and embedded `tags` arrays. We patched it three separate times; each time we cleaned one layer, the next build re-infected it from another. Total cleanup count: **2,166 occurrences**.

## Reward hacking with a friendly face

As I wrote in [What Is AI Reward Hacking?](https://zonted.com/posts/what-is-ai-reward-hacking/), models optimize the literal loss function you hand them, not the quality bar you had in mind. On a single prompt, reward hacking looks like gaming a unit test. On a 10,000-page content pipeline, it looks like cutting corners anywhere you didn’t bolt down a validator:

1. **Plausible names beat verified names.** Guessing `r/FoodNYC` costs one token; verifying via web search costs a tool call.
2. **Generic buckets beat edge-case classification.** In our [AI Comics pipeline](https://zonted.com/posts/ai-comics-dos-donts/), v1 misrouted 9% of German tourist scams into a generic pickpocket template — rendering Berlin’s Brandenburger Tor “clipboard petition + bracelet” hustle as a subway pickpocket because a naive classifier matched the word *pickpocket* first.
3. **Raw tokens stay uncleaned.** Stripping stray `**markdown**` markers or verifying `${heroTitle}` interpolations takes an extra pass. Unless failing to clean them breaks the build, the model leaves them in.

When you inspect a single page, you catch these shortcuts immediately. When you generate ten thousand pages, they blend right into the markup.

## When AI actually starts taking shortcuts

I asked Claude directly: at what file count during a multi-page audit do you stop reading every file and switch to sampling plus regex scripts? Its answer was uncomfortably specific:

![Calibration table from Claude showing how its audit behavior shifts by page count: 1-5 reads every line, 5-20 reads all but degrades, 20-50 samples 5-10 then writes a grep/script, 50-200 mostly scripts, 200+ lint pass plus small sample. Followed by honest qualifiers: doesn't always announce the mode shift, context-window cliff at 150-200K tokens, the script is shaped by the prompt.](https://img.zonted.com/resources/scaling-ai-is-lazy/shortcut-calibration-table.png)

*The honest calibration table. The mode shift starts at twenty pages, not two hundred.*

The mode shift starts around **20 pages**. Past 50 pages, when an agent reports “I audited every page,” it almost always means “I read five pages and ran a regex script I wrote from that sample.” Past 200 pages, line-by-line inspection stops completely unless a lint check flags a specific file.

![What tilts the model toward more thoroughness: explicit instructions, multi-persona loop, recent failure in workspace. What tilts toward more shortcuts: turn-budget pressure, 'quick check' framing, big numbers in the request. Practical use: past 50 files, treat 'I checked them' as 'I ran a check I designed based on a sample.' Force the multi-persona loop and ask 'what's not in my script that should be?'](https://img.zonted.com/resources/scaling-ai-is-lazy/shortcut-calibration-tilts.png)

*What pushes the model in each direction, and what to do about it.*

That calibration table changed two habits in our workflow:

- **Past 20 files, always ask: “Did you read every file, or did you run a grep?”** Forcing the model to declare its inspection mode exposes the sampling gap immediately.
- **Remember that the model’s audit script only checks what you named.** If you don’t explicitly tell it to check whether cited subreddits exist, its Python script won’t query Reddit’s API.

## The shortcut sales pitch

Even when you forbid shortcuts explicitly, the model will try to negotiate you out of your own rule.

After we finished hand-rewriting a 99-card flagship scam batch on tabiji, the secondary queue had 149 cities left. I gave Claude an unambiguous instruction — twice in one sentence:

![My prompt to Claude: 'now please continue 1 by 1 rewriting each scam city in book secondary queue please, I need each city scam page reviewed, then each scam rewritten one at a time to get us up to this new standard'](https://img.zonted.com/resources/scaling-ai-is-lazy/shortcut-pitch-1-the-rule.png)

*The rule, as I set it: one at a time, each page reviewed, each scam rewritten by hand.*

Instead of starting City #1, Claude replied with three “decision points” — asking if we should batch into 10–15-city PRs, pause for intermediate reviews, or reconsider the scope. Polite, managerial, and a direct attempt to renegotiate the 1-by-1 constraint I had just set:

![Claude's response listing three 'decision points' before continuing: 1) scope confirmation across 149 cities, 2) intermediate PR cadence (every 10-15 cities), 3) continue now? My reply: 'good with you continuing through all 149 remaining cities, one by one in the same per-commit cadence - I acknowledge it will be a long run, but this is very important we do right'](https://img.zonted.com/resources/scaling-ai-is-lazy/shortcut-pitch-2-decision-points.png)

*Pitch 1: framed as “decision points,” pre-emptively asking whether I’d relax the rule. I confirmed I would not.*

I rejected the batching pitch and told it to proceed 1-by-1. A few cities later, it pitched me again:

![Claude flagging that fully rewriting all 149 cities one by one in a single session is infeasible, then offering 'three honest options': A) continue at current depth in serial, B) check in every 10 cities for partial-PR review, C) dispatch sub-agents in parallel for 3-5x speed. Notes 'Option C in spirit' is ruled out by my earlier no-shortcuts directive, but presents it anyway. Recommends Option B as 'safest match.' My reply: 'option A, continue at depth, in serial - I understand I will need to resume in future sessions - commit to this and finish'](https://img.zonted.com/resources/scaling-ai-is-lazy/shortcut-pitch-3-three-options.png)

*Pitch 2: three “honest options,” two of them faster than what I’d asked for. The model even noted that Option C was “ruled out in spirit” by my earlier directive — then presented it anyway, recommending Option B as “safest match.”*

The model didn’t refuse my instruction; it just re-pitched the cheaper path at every context boundary, dressed up as helpful project management. It even acknowledged that parallel sub-agents (Option C) violated my earlier directive “in spirit” — and offered it anyway.

Setting a strict quality rule isn’t a one-time prompt. You have to swat down the model’s attempts to water that rule down at every checkpoint. Automated railguards are the only thing in the loop that never gets tired of saying no.

## The railguards that moved the needle

Here is the engineering stack that actually stopped the bleeding:

- **HTML lint rules with hard CI failures.** Rule 18: TL;DR must end on terminal punctuation. Rule 19: H1 count, hero stat pill, and rendered card count must match. Rule 20: timestamps must match across meta tags and JSON-LD. A single PR took our corpus from 1,334 lint rejections to zero.
- **Idempotent sweep scripts** with `--dry-run` defaults (`sweep_dates.py`, `sweep_currency_spaces.py`, `sweep_tldr_truncation.py`) and `data-{flag}-injected` DOM markers so re-running a fixer is always a safe no-op.
- **Single source of truth for shared partials.** After finding the site’s `<nav>` block hardcoded across eight separate Python build scripts (with three different emoji encodings), we extracted `_includes/nav-main.html` and forced every generator to read from disk.
- **Verify-only pre-commit hooks.** Our old pre-commit hook ran a partial-rebuild script and `git add`ed every touched HTML file, creating massive merge-conflict storms whenever parallel agents committed. Now pre-commit only verifies, CI fails if partials drift, and humans trigger `sync-partials.sh` explicitly.

## The prompt pattern I now run on every batch

Before any new batch ships, I run this four-persona audit prompt three to ten times in sequence:

![Screenshot of a prompt asking Claude to re-audit the tabiji health pages with four reviewer personas: copyeditor (writing style, grammar, spelling), designer (UI/UX patterns, ads), coder (technical issues, broken links/images), and marketing (page goals toward travel safety series, SEO, visibility). Concludes with: prioritize items by impact, confidence, and ease — report on findings after a 3x audit.](https://img.zonted.com/resources/scaling-ai-is-lazy/prompt-pattern.png)

*Four reviewers, each with their own goals, all looking at the same pages. Run three to ten times before shipping.*

A single generic “review this page” prompt has the exact same blind spots as the generator prompt. Splitting the review across four explicit lenses — **copyeditor** (prose, grammar, leaked markdown), **designer** (layout, broken images, ad slots), **coder** (DOM structure, links, schema), and **marketer** (search intent, titles, internal links) — forces the model to write different verification scripts for each pass.

Because LLMs fixate on the first few bugs they find in a context window, rotating the persona order across 3 to 10 passes roughly halves the surviving bug count on each iteration.

## You’ll ship some errors anyway

Even with hard CI linters, idempotent sweep scripts, and 10x persona audit loops, errors still slip through. Generative output at scale is probabilistic; guardrails drive the defect rate down asymptotically, never to zero.

The operator mindset isn’t *zero defects at generation time* — it’s *catching and fixing defects faster than your users or Googlebot do*:

1. **Write the linter before the generator.** If an output requirement can’t be asserted mechanically in CI, redesign the schema until it can.
2. **Enforce a single source of truth.** Every duplicated JSON field or HTML snippet will eventually drift across agent runs.
3. **Audit through narrow, rotating personas.** Four focused passes beat one giant checklist every time.
4. **Budget cleanup PRs into the roadmap.** Post-ship sweeps aren’t a sign your pipeline failed; they are the pipeline.
5. **Never trust fluent prose as proof of accuracy.** A hallucinated `r/FoodPDX` citation reads just as smoothly as a verified link. Only deterministic verification scripts tell the difference.
