# Step 5 Hypotheses

- Input: `/home/trevisan/repositories/open-data-scientist/experiments/20260219_141630_orchestrator/run_12/data/wdofut_features_v1.parquet`
- Cost per trade: `0.0`
- Thresholds: z=(0.05,0.95), spread=(0.05,0.93), vol_regime=(0.15,0.85)
- Top-K selected: `3`

## Top Candidates

### 1. H01 — Short after positive extreme z-score
- Rationale: Micro mean-reversion after stretched short-term move.
- Expected regime: High intrabar displacement without sustained follow-through.
- Validation net_pnl: 1101.0
- Validation profit_factor: 1.734489659773182
- Validation hit_rate: 0.45021645021645024
- Test net_pnl: 674.0
- Test profit_factor: 1.333994053518335
- Test hit_rate: 0.4673611111111111

### 2. H07 — Momentum on ret_sum_10
- Rationale: Simple continuation baseline at intermediate lookback.
- Expected regime: Directional short-term flow.
- Validation net_pnl: 400.0
- Validation profit_factor: 1.0136995684635934
- Validation hit_rate: 0.37880591284315607
- Test net_pnl: -566.0
- Test profit_factor: 0.9838336522807117
- Test hit_rate: 0.4178190198932557

### 3. H05 — Short when spread shock is extreme wide
- Rationale: Liquidity stress often coincides with adverse short-term drift.
- Expected regime: Spread expansion events.
- Validation net_pnl: 92.0
- Validation profit_factor: 1.6618705035971224
- Validation hit_rate: 0.5238095238095238
- Test net_pnl: 88.0
- Test profit_factor: 1.4808743169398908
- Test hit_rate: 0.5122873345935728
