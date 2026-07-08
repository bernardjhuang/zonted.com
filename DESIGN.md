# Zonted design system

Derived from the 2026-07-07 design audit (branch `claude/design-audit`). This file is the
contract; `css/zonted.css` is the implementation. When they disagree, fix one of them —
don't fork a third opinion inline.

## Product intent

- **Who:** operators and builders who follow Bernard's autonomous-AI businesses; they come
  for receipts, not tutorials.
- **What:** an editorial lab notebook — long-form posts with real numbers, plus live
  surfaces (metrics, portfolio, games) that prove the notebook isn't fiction.
- **Character:** quality print editorial with a wry operator's voice. Playful only where a
  page is explicitly an artifact of play (games, portfolio dex, ai-stack board).

**At its best the site feels like:** a well-set trade journal someone actually runs their
company from — calm paper, confident serifs, monospace where machines talk, and the
occasional arcade room behind a clearly-marked door.

## Tokens (core, `css/zonted.css`)

| Token | Value | Role |
|---|---|---|
| `--paper` | `#fcfcfa` | page ground |
| `--ink` | `#1a1815` | text, structure |
| `--faded` | `#6b655c` | secondary text (4.6:1 on paper — do not lighten) |
| `--rule` | `#1a181522` | hairlines |
| `--ox` | oxblood accent | CTAs, live signals; hover deepens to `#581c87` |
| `--serif` | Source Serif 4 | body |
| `--display` | Fraunces | headlines, titles |
| `--mono` | IBM Plex Mono | eyebrows, timestamps, machine output |

**Known debt — the second vocabulary.** Post pages carry an inline copy of the article
styles with their own token names (`--bg/--text/--accent` etc. in every `posts/*/index.html`).
It works because the values match, but every article ships ~150 duplicated lines and a CSP
migration is blocked on it (see `_headers` comment). Merge plan is L3 §1 below. Until then:
**new page-level styles go in `zonted.css`; never invent a third token name.**

## The island rule

The core is light editorial. Three surfaces are sanctioned **dark islands** with their own
palettes: `/portfolio/` (trading-card dex), `/ai-stack/` (PCB board), `/games/*` (arcade).
Rules that keep islands coherent (trigger: `/portfolio/` audit finding — footer links at
3.48:1):

1. The shared nav and footer are **always paper**. `zn-footer` carries an explicit
   `background: var(--paper)` so islands can't sink its contrast.
2. Island typography may add display faces (Press Start 2P, Archivo Black) but body copy
   inside an island still uses the core three families.
3. Gradients, glow, scanlines, emoji: allowed **only** on islands. Editorial pages use the
   mono eyebrow, not emoji (trigger: `/metrics/` h2s shipped 💸/📊/🔎 — removed).

## Accessibility floor (all enforced by the audit battery)

- **Targets:** every nav/footer/UI link ≥24px in both dimensions. Pattern: real padding in
  roomy contexts (footer), padding-with-negative-margin where rhythm is tight (desktop nav
  — scoped `min-width: 721px`; the mobile drawer is already padded. Trigger: footer "X"
  measured 9px wide on every page).
- **Reflow at 200% zoom:** no horizontal scroll on editorial pages. Three canonical fixes,
  each earned on a real page: flex/grid children that contain inputs need `min-width: 0`
  (trigger: home/about subscribe module); wide data tables get
  `display:block; overflow-x:auto; min-width:0` (trigger: review posts' `.spec-table`,
  whose own `min-width` beat `max-width`); canvases get `max-width:100%; height:auto`
  (trigger: `/metrics/`). Data tables and the ai-stack board may scroll **in place** —
  never the page.
- **Contrast:** minimum 4.5:1 for text; `--faded` and `--text-dim` sit near the line —
  never lighten them, never put them on non-paper grounds.
- **Motion:** every animation lives behind `prefers-reduced-motion` (three guards in
  `zonted.css`; games include their own).
- **Focus:** site-wide `a:focus-visible, button:focus-visible` outline in `--ox`; the
  CSS-only hamburger keeps a visible focus ring via its label.
- **CLS:** content images carry `width`/`height`; list thumbnails are CSS-boxed
  (150×105) so missing attributes there are benign.

## Honesty is a design property

The brand promise is receipts. Decorative fiction is therefore a **defect**, same severity
as broken contrast (trigger: `/about/` shipped a "Zonted Substack, 8,420 subscribers"
pastiche while the real list was 29 on Resend, and listed dead projects as live). Mockups
and pastiches are welcome — the about page's inbox is the best thing on the site — but
their *content* must be true at time of writing, and stale-able numbers should be small,
dated, or linked to `/metrics/`.

## Copy rules

- Explain the user's next action, not the system (the portfolio legend is the sanctioned
  exception — collector-guide flavor is the point there).
- One CTA per intent per view (trigger: home had two "Read all" affordances; the header
  meta-link was removed, the closing CTA stays).
- Titles: search-facing `<title>` may differ from the on-page H1 (established AEO pattern).

## L3 register (proposed, not done)

1. **Merge the dual token systems** — extract the per-post inline styles into
   `css/article.css`, alias the old names during migration, then run a codemod across
   `posts/*/index.html`. Unblocks CSP. (~50 files, mechanical, needs a visual-diff pass.)
2. **Forced-dark defense** — editorial pages declare `color-scheme: light` + a
   `theme-color` pair so auto-darkening browsers don't mangle the paper.
3. **Portfolio legend** — consider collapsing the card-anatomy explainer behind a
   "how to read a card" toggle on narrow viewports.
4. **Navigation** — 7 items is the ceiling. If anything is added, Metrics is the first
   candidate to fold into About. Do not add an 8th item.
5. **Per-post OG cards** — 29 posts share one generic share image; a build-step generator
   (prototype exists at `/prototype/og/`) is the highest-leverage visual investment left.
