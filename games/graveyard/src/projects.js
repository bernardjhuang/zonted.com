export const projects = [
  {
    slug: 'kapiko',
    name: 'KAPIKO',
    type: 'AI Music',
    born: '2026',
    died: '2026',
    pages: [
      'AI-crafted ambient music for the soul.',
      'Generative ambient music for focus and calm. Curated by AI, mixed for stillness. Press play, get out of your own way.',
      'Killed by the Suno wrapper — Suno has no public API, so it broke every 1-2 days. You cannot cron a business that needs babysitting that often.',
    ],
    link: { label: 'Read the full post-mortem →', href: '/posts/kapiko-postmortem/' },
  },
  {
    slug: 'palmaura',
    name: 'PALMAURA',
    type: 'iOS App',
    born: '2026',
    died: '2026',
    pages: [
      'Palm reading in your pocket — photograph your palm, get a daily read.',
      'The build was the easy part: backend one-shot on Cloudflare Workers, the Swift app out in a couple of shots. Five builds in two weeks. The product worked.',
      'Killed by Apple — rejected twice under Guideline 4.3(b), "Design – Spam." A saturated category and a closed door: "there are already enough of these apps on the App Store." Zero users ever saw it.',
    ],
    link: { label: 'Read the full post-mortem →', href: '/posts/palmaura-postmortem/' },
  },
  {
    slug: 'veracity',
    name: 'VERACITY',
    type: 'API',
    born: '2026',
    died: '2026',
    pages: [
      'Detect AI slop before it ships — a pre-publish check that agents call before they publish, train on, or moderate content.',
      'The build was one afternoon: a Cloudflare Worker, a D1 database, one LLM call. Then an MCP server, SDKs, a Chrome extension, and a shelf of free SEO tools.',
      'Killed by its maker — opportunity cost. Trading was working, the API needed upkeep, and it never found a buyer. Four outside signups, $0 in revenue.',
    ],
    link: { label: 'Read the full post-mortem →', href: '/posts/veracity-postmortem/' },
  },
];
