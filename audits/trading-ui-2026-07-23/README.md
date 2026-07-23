# Trading UI audit and simplification

Audit date: July 23, 2026

This folder records the before/after review for `/trading/`.

- [`audit.md`](audit.md): original six-surface readability and usability audit.
- [`implementation-plan-v2.md`](implementation-plan-v2.md): reviewed implementation plan, including generator ownership and contract corrections.
- [`mobile-before.png`](mobile-before.png): original mobile contact sheet.
- [`mobile-after.png`](mobile-after.png): final exact-390px Playwright contact sheet.

## Result

The original seven-tab page and a concurrently added Congress feed now resolve to six decision-oriented surfaces: Portfolio, Momentum, VWAP, Congress, 13F, and Crypto. Large chart and universe payloads load from external JSON only when requested.

| Gate | Result |
| --- | ---: |
| Initial HTML | 145,939 bytes |
| Mobile Lighthouse performance | 97–98 on all six routes |
| Lighthouse accessibility | 100 on all six routes |
| Lighthouse best practices | 100 on all six routes |
| Lighthouse SEO | 100 on all six routes |
| Page-level overflow at 390px | None |

## Reproduce

From the repository root, serve the static site and run:

```sh
python3 -m http.server 8877 --bind 127.0.0.1
python3 scripts/test-trading-ui.py
python3 scripts/smoke-trading-ui.py
```

The browser smoke requires Python Playwright and Chrome (or `CHROME_BIN`).
