# Step 5 Hypotheses

- Input: `/home/trevisan/repositories/open-data-scientist/experiments/20260219_162928_orchestrator/run_03/data/wdofut_features_v1.parquet`
- Cost per trade: `0.0`
- Thresholds: z=(0.05,0.90), spread=(0.03,0.90), vol_regime=(0.10,0.80)
- Top-K selected: `2`

## Top Candidates

### 1. H02 — Long after negative extreme z-score
- Rationale: Symmetric mean-reversion for downside stretch.
- Expected regime: Short-lived panic downticks.
- Validation net_pnl: 512.0
- Validation profit_factor: 1.3613267466478476
- Validation hit_rate: 0.3367667597765363
- Test net_pnl: 778.0
- Test profit_factor: 1.4735240413877053
- Test hit_rate: 0.42473684210526313

### 2. H08 — Contrarian on ret_sum_5
- Rationale: Quick mean-reversion at very short lookback.
- Expected regime: Choppy microstructure periods.
- Validation net_pnl: 226.0
- Validation profit_factor: 1.010715471054004
- Validation hit_rate: 0.3129606248348357
- Test net_pnl: -119.0
- Test profit_factor: 0.995601552393273
- Test hit_rate: 0.3715720355349556
