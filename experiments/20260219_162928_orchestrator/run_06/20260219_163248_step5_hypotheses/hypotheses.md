# Step 5 Hypotheses

- Input: `/home/trevisan/repositories/open-data-scientist/experiments/20260219_162928_orchestrator/run_06/data/wdofut_features_v1.parquet`
- Cost per trade: `0.0`
- Thresholds: z=(0.05,0.90), spread=(0.03,0.90), vol_regime=(0.10,0.80)
- Top-K selected: `2`

## Top Candidates

### 1. H02 — Long after negative extreme z-score
- Rationale: Symmetric mean-reversion for downside stretch.
- Expected regime: Short-lived panic downticks.
- Validation net_pnl: 504.0
- Validation profit_factor: 1.355681016231475
- Validation hit_rate: 0.33537011173184356
- Test net_pnl: 767.0
- Test profit_factor: 1.4662613981762918
- Test hit_rate: 0.4231578947368421

### 2. H08 — Contrarian on ret_sum_5
- Rationale: Quick mean-reversion at very short lookback.
- Expected regime: Choppy microstructure periods.
- Validation net_pnl: 209.0
- Validation profit_factor: 1.0099183750949128
- Validation hit_rate: 0.31243209912793257
- Test net_pnl: -133.0
- Test profit_factor: 0.9950773558368495
- Test hit_rate: 0.3708685096286487
