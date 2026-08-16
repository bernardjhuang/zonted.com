# Catalyst Desk

Static MVP published at https://zonted.com/grok-bot-trading/.

Three hunts (VOL / DIR / BIN) plus a public HELD slot. Shared plumbing, no shared gates.

This directory is an isolated surface. No site-nav item. No edits outside `grok-bot-trading/`.

Cloudflare Pages static files only. No Python server. No `POST /api/marks`.

Marks stay in the browser: `localStorage` key `catalyst-desk-marks`.

No orders. Public snapshot strips account ids, quantities, avg cost, and balances. Held book omitted.

Hover or keyboard-focus a header, tab, mark, or packet label for a short field explanation (`data-tip`). Missing numbers still render as —.

Footer: MVP · no orders · UNPROVEN.
