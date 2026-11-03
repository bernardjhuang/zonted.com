# KXHIGHCHI 2026 YTD — Buy-No at first 90¢ Yes print

As-of **2026-08-19**. Settled event-days `KXHIGHCHI-26JAN01` through `KXHIGHCHI-26AUG18`.

## Judge / station

- Station: **KMDW Midway / CLIMDW** (not O'Hare).
- Confirmed from event `rules_primary`: 1380 / 1380 mention Midway/CLIMDW (1350 say Midway, 30 say CLIMDW); 0 mention O'Hare.
- Source agency in rules: NWS 1350, TWC 30 (TWC = Aug 14–18 after the 2026-08-14 switch).
- HIGHCHI series `settlement_sources`: NWS CLI `issuedby=MDW` (CLIMDW).
- KXHIGHCHI series settlement source is The Weather Company after **2026-08-14** (NWS→TWC, same station).

## Universe

- Settled 2026 markets: **1380**
- 2026 events: **230** (2026-01-01 .. 2026-08-18)
- Results: YES=230 NO=1150

## Coverage

- Tickers with `max_yes`: **1380** / 1380 (candle `price.high` 1380; trade fallback 0)
- Missing NO-with-volume max_yes: **0** (these bias die% **down**)
- YES still missing (last≥0.85 or volume): **0**
- `max_yes` is candle **price.high** (trade high), never yes_ask.high. Last-price fallback only for YES last≥0.96. Die% is **not** last-price-only.
- Candle `price.high` vs full trade tape: 1380 tickers agree (90-print flips = 0). `yes_ask.high`≥0.90 with `price.high`<0.90 on 1092 NOs — those are book, not trades.

## 2026 YTD ladder (Buy No at 100−X¢ on first X Yes print)

| X¢ Yes | n | die | die% | EV¢ | fee¢ | EV after fee¢ | candle n | trade-fb n | YES≥96 n |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 70 | 387 | 157 | 40.57 | +10.57 | 1.47 | +9.10 | 387 | 0 | 0 |
| 75 | 347 | 117 | 33.72 | +8.72 | 1.31 | +7.41 | 347 | 0 | 0 |
| 80 | 327 | 97 | 29.66 | +9.66 | 1.12 | +8.54 | 327 | 0 | 0 |
| 85 | 307 | 77 | 25.08 | +10.08 | 0.89 | +9.19 | 307 | 0 | 0 |
| 90 | 283 | 53 | 18.73 | +8.73 | 0.63 | +8.10 | 283 | 0 | 0 |
| 95 | 259 | 30 | 11.58 | +6.58 | 0.33 | +6.25 | 259 | 0 | 0 |

## 90¢ line vs NYC

- CHI 2026 YTD: n=283, die%=18.73, EV after fee=+8.10¢
- NYC 2026 YTD (given, not refetched): n=281, die%=18.1, EV after fee=+7.5¢
- Fee at 10¢ No = 0.63¢; breakeven die after fee = 10.63%. Observed 90-No die% = 18.73.

## Verdict: **+EV**

Pass only if 90-No is +EV after fee on 2026 YTD. Seasonal splits not claimed unless n per season ≥ ~80.

## Caveats

1. **Fill** — assumes a 10¢ No fill at the first 90¢ Yes print (candle `price.high` ≥ 0.90, or YES last≥0.96 fallback).
2. **Judge** — Midway (KMDW / CLIMDW), not O'Hare. Source agency changed NWS→TWC on 2026-08-14; station unchanged.
3. **Coverage** — `max_yes` from candle trade high (`price.high`), not `yes_ask.high` (book can sit at 0.99 with no trade). Last-price-only would miss spike-then-fade dies (Austin trap). Missing NO candles bias die% down.

