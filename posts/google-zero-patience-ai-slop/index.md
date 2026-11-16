---
title: "81 Lines of Merge Conflict. -95% Traffic. Google Has Zero Patience for AI Slop."
author: "Bernard Huang"
date: "2026-05-15"
modified: "2026-05-15"
canonical: "https://zonted.com/posts/google-zero-patience-ai-slop/"
category: "AEO & Search"
description: "An AI agent shipped a merge conflict to tabiji.ai's production HTML for four hours. Google cut our search traffic by 95% within four days."
---

# 81 Lines of Merge Conflict. -95% Traffic. Google Has Zero Patience for AI Slop.

By Bernard Huang · 2026-05-15 · 5 min read

On May 10, 2026, one of my AI agents shipped a PR that left 81 lines of raw git conflict markers — `<<<<<<< HEAD`, `=======`, `>>>>>>> sha` — sitting in plain HTML on [tabiji.ai](https://tabiji.ai)'s main scams hub. Four hours later, we patched it. Four days later, Google had cut our organic search traffic by ~95%. We still haven't recovered.

## TL;DR

Four hours of unmerged git conflict markers on a top landing page triggered a site-wide Google quality demotion that wiped out 95% of [tabiji.ai](https://tabiji.ai)'s organic traffic.

- **The trigger** — 81 lines of raw `<<<<<<< HEAD` rendered in visible HTML on `/scams/`, our highest-traffic organic hub.
- **The demotion** — Both clicks and impressions collapsed despite 3,957 URLs staying indexed, zero manual actions, and no overlapping core update.
- **The corroborating mess** — A post-crash audit uncovered 1,244 broken internal links, 237 broken CDN images, and 32 latent DOM/schema bugs across the site.

## What broke

Tabiji.ai runs on a fleet of AI agents that write copy, build pages, produce videos, refactor code, and ship PRs. Here is the commit timeline from GitHub:

- **May 8 (PR #1490):** We found and patched merge-conflict residue on the scams hub. Thought we were clean.
- **May 10, 02:39 EDT:** A subsequent agent PR landed with fresh residue — 81 conflict marker lines stacked between the hero stat pills, rendering raw in the DOM to every visitor.
- **May 10, 06:39 EDT (PR #1513):** Emergency fix deployed. Total exposure window: four hours.

![Google Search Console performance chart for tabiji.ai showing organic clicks and impressions both collapsing from a peak of ~80 daily clicks and ~13K daily impressions to near zero in mid-May 2026](https://img.zonted.com/resources/google-zero-patience-ai-slop/gsc-traffic-cliff.png)

*GSC for tabiji.ai. Both clicks and impressions cliff after May 10 — Google didn't just stop ranking the pages, it stopped showing them.*

## What Google saw

On a normal day, `/scams/` is one of tabiji's strongest organic entry points, ranking for hundreds of “[city] scams to avoid” queries and feeding internal links across the site.

For four hours, Googlebot crawled that URL and saw raw git conflict syntax in the visible body. To Google's site-quality classifiers, the signal was unambiguous: *unmonitored, broken publisher.* By the next morning, the click curve bent downward. Within 96 hours, ~95% of our daily clicks were gone.

Look at the purple line in the chart above: **impressions cratered alongside clicks.** Google didn't just drop us a few positions — it stopped surfacing our pages in search results altogether.

## What it wasn't

Before blaming site-wide quality classifiers, I ruled out the standard causes:

**The pages are still indexed.** GSC shows 3,957 indexed URLs and climbing. Google still stores the pages; it just refuses to rank them.

![Google Search Console Indexing panel for tabiji.ai showing 3,957 indexed pages versus 3,007 not indexed, with the indexed-pages line trending upward through May 8, 2026](https://img.zonted.com/resources/google-zero-patience-ai-slop/gsc-indexing.png)

*GSC Indexing report. Indexed-page count is still going up. The crash isn't about whether Google has the pages — it's about whether Google shows them.*

**No security issues.** No malware or hacked-content flags.

![Google Search Console Security Issues panel showing 'No issues detected'](https://img.zonted.com/resources/google-zero-patience-ai-slop/gsc-security-issues.png)

**No manual penalty.** Zero human reviewer actions in GSC.

![Google Search Console Manual Actions panel showing 'No issues detected'](https://img.zonted.com/resources/google-zero-patience-ai-slop/gsc-manual-actions.png)

**No Google algorithm update during the cliff window.** Per [Google's Search Status dashboard](https://status.search.google.com/summary), the last announced ranking update finished March 27, 2026 — six weeks before our crash. No core update, spam update, or Discover update overlapped May 10.

![Google Search Status Dashboard listing the last four announced ranking events: March 2026 core update finishing March 27, March 2026 spam update March 24, February 2026 Discover update, and December 2025 core update. No active events during May 2026.](https://img.zonted.com/resources/google-zero-patience-ai-slop/search-status-ranking.png)

*Google's Search Status dashboard. The last completed ranking event finished 5 weeks before our crash. Nothing announced overlaps the cliff window.*

Pages indexed, no manual action, no core update. The 81 lines of conflict markers tripped an automated quality threshold, and the rest of the site's latent technical debt gave Google plenty of corroborating evidence.

## What else was wrong

When we audited the rest of the repo to see what else Googlebot was running into, the backlog was ugly:

- **PR #1530:** 479 broken hub-card links + 19 empty sections.
- **PR #1531:** 1,244 broken internal links across 379 unique targets.
- **PR #1535:** 24 latent bugs — entity double-encoding, duplicate DOM IDs, raw markdown leaking into rendered HTML.
- **PR #1536:** 8 more fixes for broken HTML, stray `console.log` calls, and security headers.
- **PR #1537:** 237 broken CDN image references + 6 missing schema blocks across 121 files.

None of those bugs alone tanks a domain. Together, they profile an automated publisher shipping faster than it validates. The merge conflict on `/scams/` was just the flare that drew attention to the rest of the mess.

## Why Google's bar quietly moved

Search is drowning in AI-generated listicles and programmatic review farms that publish faster than any human team can review. Google has adjusted its classifiers accordingly — especially for domains that scale page count rapidly.

When a slow, human-edited site ships a broken page, it looks like an isolated ops mistake. When a site publishing hundreds of programmatic pages a week ships raw git conflict markers, broken internal links, and leaked markdown, it matches the exact fingerprint of unmonitored AI slop.

Zonted is fine because it ships a handful of human-edited posts a week. [Tabiji.ai](https://tabiji.ai) ships hundreds of pages a week via autonomous agents. Google holds high-velocity sites to a zero-tolerance technical bar.

## The lesson

If your AI agents push directly to production, you need a hard pre-ship gate:

- A CI check that fails the build on `<<<<<<<`, unrendered markdown tokens, broken internal links, or duplicate DOM IDs (twenty minutes of setup).
- An independent audit agent that grades every PR before merge.
- A staging hold before high-traffic hubs deploy to production.

I didn't have those gates wired up on May 10. I do now — after paying 95% of our organic traffic as tuition.

AI agents will ship merge conflicts, stray `console.log`s, double-encoded entities, and broken links. The only question is whether your CI catches them before Googlebot does.
