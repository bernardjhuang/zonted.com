# Robinhood L2 Launch Radar — Plan (superseded framing)

**Canonical implementation spec:** [`rh-launch-identification-spec.md`](./rh-launch-identification-spec.md)

This earlier plan sketched a DexScreener-first reverse-engineering approach. That is **rejected** by the frozen spec:

- Corpus = launchpad factory events only (Pons + later pools.trade).
- DexScreener is never the corpus, never a ranking input.
- Decision timestamps are T+3/5/10/20 minutes; later windows are labels only.
- Outcomes must be executable (depth-aware), not displayed mcap.

Implementation lives in [`rh-launch-radar/`](../rh-launch-radar/). Current workstream: **M0 harvest → M1 features/labels → M2 backtest**.
