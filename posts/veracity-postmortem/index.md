---
title: "VeracityAPI: a one-afternoon, four-signup, zero-dollar post-mortem"
author: "Bernard Huang"
date: "2026-09-24"
modified: "2026-09-24"
canonical: "https://zonted.com/posts/veracity-postmortem/"
category: "Post-Mortems"
description: "VeracityAPI took an afternoon to build and made $0 in four months. The receipts, the six-cell scorecard, and why I killed it before the market could answer."
---

# VeracityAPI: a one-afternoon, four-signup, zero-dollar post-mortem

By Bernard Huang · 2026-09-24 · 5 min read

VeracityAPI took one afternoon to build. The next few weeks went to everything around it: an MCP server, SDKs on npm and PyPI, a Chrome extension, a text linter, and a shelf of free SEO tools. Four months after launch, the tally is seven accounts (me, two smoke tests, and four outside signups), zero paying customers, and $0 in revenue. Today I shut it down. Nothing killed it but me.

## TL;DR

I built a tool for the agent economy, marketed it with free tools, and walked away before anyone told me whether it was worth paying for. Veracity didn’t fail the market test. I never finished running it.

- **The build was the easy part.** One Cloudflare Worker, one D1 database, one LLM call. From $0.01 a call, with $1.50 of free credit and no card.
- **The marketing was more engineering.** Free detector and AI-visibility tools earned 4,025 Google impressions and 18 clicks in 90 days, at an average position of 32.
- **The sales motion never got going.** I warmed up an inbox for cold B2B outbound, then moved on to other projects.
- **Cause of death: opportunity cost.** Vibe trading was working, and a live API is a pile of moving parts that needs tending whether anyone calls it or not.
- **Total bill:** about $50–100 in hard costs, plus $200–400 in LLM tokens to build it.

Veracity joins [Kapiko](https://zonted.com/posts/kapiko-postmortem/) and [PalmAura](https://zonted.com/posts/palmaura-postmortem/) in the [graveyard](https://zonted.com/games/graveyard/).

## The bet: tools for agents

I still believe the premise. The future of commerce, and of the internet, is an agent economy: software calling software, with people setting goals instead of clicking buttons. If that’s where things are going, durable businesses will sell to agents—tools an agent can discover, call, and pay for without a human in the loop.

The second half of the premise was slop. The more publishing agents take over, the more AI slop enters the ecosystem: generic text, synthetic images, cloned voices, the confident paragraph that says nothing. An agent publishing on your behalf needs a pre-flight check to catch its own slop before it goes live.

In May I wrote the launch post, [Build for Agents, Price Per Call](https://zonted.com/posts/build-for-agents-price-per-call/), and held the idea up against four tests. Does it stay valuable as agents take over? As agents get smarter? Is the surface agent-first? Is it metered, with a free tier? On paper, Veracity passed all four.

The product changed on the very first planning message. Slo, the agent in my Hermes setup, talked me out of the original idea: an AI-content *detection* API. Detectors are probabilistic, adversarial, and easy to overclaim. We reframed it as risk scoring with evidence—one call in, one action out (`allow`, `revise`, `human_review`, or `reject`) plus the receipts behind it. The homepage put it best: *“We don’t care who wrote it. We care whether it’s shippable.”*

## What I shipped

![The VeracityAPI homepage: the headline ‘Detect AI slop before it ships,’ an eyebrow reading ‘For developers shipping AI features, $1.50 free credit, no card,’ and badges for OpenAPI 3.1, MCP-ready, llms.txt and agents.json.](https://img.zonted.com/resources/portfolio/veracity.png)

*veracityapi.com. Read the line above the headline: for developers shipping AI features. The API was built for agents. The pitch was aimed at people.*

The core really did take an afternoon: one Cloudflare Worker, one D1 database, one LLM call. Pricing ran from $0.01 a call for up to 4,000 characters to $0.12 for 100,000, with $1.50 of free credit and no card required. No subscriptions, no seats, no “talk to sales.” An agent could go from discovery to its first call without asking anyone.

Then I kept building, because building was the fun part:

- a REST API with an OpenAPI 3.1 spec, plus `llms.txt` and `agents.json` so machines could find it
- an MCP server, and SDKs on npm and PyPI
- a Chrome extension, which came out in one shot
- a text linter, planned by three models with the [plan-3× loop](https://zonted.com/posts/plan-3x-build-once/)
- evals, a benchmark repo, and a stack of free tools: AI-text detectors, a fake-review checker, integration guides

A [stakes-priming audit](https://zonted.com/posts/stakes-priming/) caught six ship-blocking bugs, including duplicate JSON keys on the homepage. By early June, Veracity was the most complete product I had never sold.

## The receipts

| Built | One afternoon in May 2026 |
| --- | --- |
| Surfaces | API, MCP server, npm and PyPI SDKs, Chrome extension, text linter, free tools |
| Accounts | 7: me, 2 smoke tests, 4 outside signups (all on free credit) |
| Paying customers | 0 |
| Revenue | $0 |
| Last API call | June 10, the day PixelForge launched |
| Google Search, 90 days | 4,025 impressions, 18 clicks, average position 32 |
| Tracked visits, 90 days | 24, and 22 of them came from zonted.com |
| Cost | About $50–100 in hard costs, $200–400 in LLM tokens |

The visit count understates reality because Google Analytics only fired after cookie consent. Even so, 22 of the 24 recorded visits came from links on this site. Almost nobody found Veracity unless I sent them there.

*VeracityAPI in Google Search Console, per week, May 25 to August 22, 2026. The last bar covers six days.*

**Weekly numbers**

| Week of | Impressions | Clicks |
| --- | --- | --- |
| May 25 | 102 | 1 |
| Jun 1 | 103 | 2 |
| Jun 8 | 260 | 0 |
| Jun 15 | 314 | 1 |
| Jun 22 | 409 | 0 |
| Jun 29 | 203 | 3 |
| Jul 6 | 245 | 0 |
| Jul 13 | 246 | 3 |
| Jul 20 | 246 | 1 |
| Jul 27 | 528 | 4 |
| Aug 3 | 332 | 2 |
| Aug 10 | 566 | 0 |
| Aug 17 (6 days) | 471 | 1 |
| Total | 4,025 | 18 |

The chart is the part I keep staring at. Google impressions climbed all summer, from about 100 a week in late May to more than 500 a week in August, while the product sat untouched. Clicks never followed. An average position of 32 is page four, and nobody reads page four.

Look at which pages drew those 18 clicks. Of the top five, two were AI-detector pages and a third was a fake-review checker. The searches that found Veracity were looking for detection—the exact product Slo had talked me out of on day one. Nobody was searching for what I actually built: a risk score with evidence, sold to agents.

## Free tools and a warm inbox

I’ve done SEO for fifteen years, so I marketed Veracity the way I know how: engineering as marketing. Build free tools that people search for (detectors, checkers, AI-visibility utilities), get them ranked, and let the product sell itself to whoever shows up.

It half worked. Google indexed the tools and kept showing them. But free tools attract people who want a free tool. Someone pasting a paragraph into an AI-text detector wants a verdict on that paragraph, not an API key for a pipeline they don’t have. The tool answered their question and they left. Engineering as marketing got me impressions. It never got me intent.

The channel that could have answered the real question was the oldest one: talk to buyers. A developer tool gets sold one conversation at a time, to the engineering lead who is tired of shipping slop. I got as far as warming up an inbox for cold B2B outbound with Lemwarm, which trades friendly emails with other inboxes for a few weeks so a new domain doesn’t land in spam. Then I wandered off to other projects before sending a single cold email.

## How it scored

Every project gets the same six-cell rubric I used on [Kapiko](https://zonted.com/posts/kapiko-postmortem/). Here’s Veracity, scored with hindsight.

Barrier to entryLOW I said it in the launch post: anyone with the same stack can build the same product tomorrow. I built it in an afternoon. So can anyone, and Copyleaks and GPTZero already sell detection APIs.   Channel durabilityMEDIUM An API is exactly where the agent economy points. But the channel I actually used to find customers, free-tool SEO, is the first thing AI answers eat.   Market sizeHIGH Slop grows with every agent deployed, so the problem gets bigger every quarter. Whether anyone pays to check before they publish is a separate question.   Product durabilityMEDIUM Detection is probabilistic and adversarial, which is why Slo talked me out of it. Risk scoring with evidence ages better, but every model release moves the target.   GTM / marketingHIGH Developer tools are sold one conversation at a time. Building agent-first let me skip the human sales motion, and humans still hold the credit cards.   Business modelMEDIUM Metered pricing suits agents. But at a cent a call, a team running 1,000 checks a month is a $10 customer. You need thousands of pipelines before it pays rent.

One green, three amber, two red. The two reds are the same two Kapiko had: a low barrier to entry and a hard go-to-market. Anyone can build it, so getting found is the whole job. I’ve now learned that lesson twice, which is once more than a lesson should take.

## Cause of death

Kapiko was killed by a Suno wrapper that broke every 36 hours. PalmAura was killed by Apple. Veracity is the first grave with no outside cause of death. Nothing broke. Nobody rejected it. I stopped working on it.

Two things pulled me away. The first was opportunity cost. Over the summer, [vibe trading](https://zonted.com/posts/vibe-trading/) (equities and prediction markets, run with AI analysts) started working, and an hour there paid off faster than an hour spent hunting for Veracity’s first customer.

The second was upkeep. A content site can sit untouched for months. An API can’t. Veracity meant Workers, API calls, keys, a database, billing, and an email domain: moving parts that need tending whether or not anyone is calling them. When something else is working, that overhead is the first thing you stop paying.

Underneath both was a quieter doubt: I wasn’t sure anyone wanted it. That’s the uncomfortable truth, because I never found out. The launch post said the agent economy “doesn’t have credit cards.” I read that as a reason to build for agents. I should have read it as a warning. If the agent can’t pay, a person has to, and I never sat down with that person. The homepage said *developers shipping AI features* the whole time. I built everything except the conversation with one of them.

## What comes with me

A few hundred dollars was cheap tuition. Four things outlive the product:

- **The plan-3× loop.** Three models plan, one builds. It was born planning a Veracity feature, and it went on to ship the [PalmAura](https://zonted.com/posts/palmaura-postmortem/) backend and [PixelForge](https://zonted.com/posts/pixelforge-launch/).
- **Stakes priming.** The audit prompt I first tested on Veracity outlived it.
- **A fifth test for the agent economy.** My four tests asked whether a product survives the future. None asked whether anyone pays for it today. The fifth: can you name the person who holds the credit card, and have you talked to them?
- **A teardown checklist.** The build took an afternoon. The shutdown list ran past a dozen items: a Worker, a database, two GitHub repos, three packages, MCP listings, Stripe, Resend, analytics, an ads account, a Chrome app, and a domain. Every surface you ship is a surface you’ll have to bury.

## To the graveyard

I don’t know if Veracity was a bad idea. I know I never ran the one test that would have told me. For a few hundred dollars and a few weeks of building, I can live with “don’t know” and spend my time on what’s working.

The thesis outlives the product. Agents will become the biggest consumers of software, and the slop will keep coming. The next time I build for agents, I’ll find the person with the credit card first and build second.

So Veracity goes to [the graveyard](https://zonted.com/games/graveyard/), playable like the rest, next to Kapiko and PalmAura. Three graves now, and the bench is still long.
