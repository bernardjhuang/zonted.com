# Robinhood Launch Radar

Research system for ranking Robinhood Chain token launches by probability of becoming a **high-value, executable** winner.

Canonical spec: [`docs/rh-launch-identification-spec.md`](../docs/rh-launch-identification-spec.md)

Hard constraints baked in:

- Corpus = launchpad factory events (Pons first). DexScreener is never a ranking input.
- Point-in-time features with `available_at`; leakage tests fail closed.
- Decision timestamps: T+3/5/10/20 minutes after first executable liquidity.
- No signing path / wallets / keys in this codebase.

## Setup

```bash
export BLOCKSCOUT_PRO_API_KEY=proapi_…   # or ~/.config/trading/blockscout.env
pip install -e '.[dev]'
```

## Pipeline

```bash
cd rh-launch-radar
PYTHONPATH=src python -m rh_radar.harvest --chunk 40000
PYTHONPATH=src python -m rh_radar.stamp --every 20000
PYTHONPATH=src python -m rh_radar.features --limit 400
PYTHONPATH=src python -m rh_radar.labels --limit 400
PYTHONPATH=src python -m rh_radar.profile_funnel
PYTHONPATH=src python -m rh_radar.backtest --decision-offset 600
```

## Current milestone focus

M0 funnel harvest → M1 early features/labels → M2 scorecard backtest vs baselines B1–B4.
