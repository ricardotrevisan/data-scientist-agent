# Step 5 Hypotheses

- Input: `/home/trevisan/repositories/open-data-scientist/experiments/20260219_141630_orchestrator/run_18/data/wdofut_features_v1.parquet`
- Cost per trade: `0.0`
- Thresholds: z=(0.05,0.95), spread=(0.05,0.93), vol_regime=(0.15,0.85)
- Top-K selected: `3`

## Top Candidates

### 1. H01 — Short after positive extreme z-score
- Rationale: Micro mean-reversion after stretched short-term move.
- Expected regime: High intrabar displacement without sustained follow-through.
- Validation net_pnl: 425.0
- Validation profit_factor: 1.177157148812005
- Validation hit_rate: 0.489004329004329
- Test net_pnl: -20.0
- Test profit_factor: 0.9926605504587156
- Test hit_rate: 0.4696180555555556

### 2. H08 — Contrarian on ret_sum_5
- Rationale: Quick mean-reversion at very short lookback.
- Expected regime: Choppy microstructure periods.
- Validation net_pnl: 79.0
- Validation profit_factor: 1.0025107262037185
- Validation hit_rate: 0.4631059694042341
- Test net_pnl: 493.0
- Test profit_factor: 1.0142944127112992
- Test hit_rate: 0.4825635932240799

### 3. H05 — Short when spread shock is extreme wide
- Rationale: Liquidity stress often coincides with adverse short-term drift.
- Expected regime: Spread expansion events.
- Validation net_pnl: 57.0
- Validation profit_factor: 1.329479768786127
- Validation hit_rate: 0.5215419501133787
- Test net_pnl: 54.0
- Test profit_factor: 1.242152466367713
- Test hit_rate: 0.5236294896030246
