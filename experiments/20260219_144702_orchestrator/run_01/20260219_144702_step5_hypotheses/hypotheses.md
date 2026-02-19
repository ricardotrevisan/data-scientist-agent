# Step 5 Hypotheses

- Input: `/home/trevisan/repositories/open-data-scientist/data/wdofut_prepared/wdofut_features_v1.parquet`
- Cost per trade: `0.0`
- Thresholds: z=(0.05,0.95), spread=(0.05,0.93), vol_regime=(0.15,0.85)
- Top-K selected: `2`

## Top Candidates

### 1. H01 — Short after positive extreme z-score
- Rationale: Micro mean-reversion after stretched short-term move.
- Expected regime: High intrabar displacement without sustained follow-through.
- Validation net_pnl: 477.0
- Validation profit_factor: 1.2375498007968126
- Validation hit_rate: 0.4303030303030303
- Test net_pnl: -135.0
- Test profit_factor: 0.9464922711058263
- Test hit_rate: 0.41458333333333336

### 2. H07 — Momentum on ret_sum_10
- Rationale: Simple continuation baseline at intermediate lookback.
- Expected regime: Directional short-term flow.
- Validation net_pnl: 342.0
- Validation profit_factor: 1.0107753867481648
- Validation hit_rate: 0.4105842452166123
- Test net_pnl: -604.0
- Test profit_factor: 0.9835323627242488
- Test hit_rate: 0.4375788452207666
