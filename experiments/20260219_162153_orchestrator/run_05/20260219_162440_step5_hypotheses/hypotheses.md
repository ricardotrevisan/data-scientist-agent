# Step 5 Hypotheses

- Input: `/home/trevisan/repositories/open-data-scientist/experiments/20260219_162153_orchestrator/run_05/data/wdofut_features_v1.parquet`
- Cost per trade: `0.0`
- Thresholds: z=(0.05,0.90), spread=(0.03,0.90), vol_regime=(0.10,0.80)
- Top-K selected: `2`

## Top Candidates

### 1. H01 — Short after positive extreme z-score
- Rationale: Micro mean-reversion after stretched short-term move.
- Expected regime: High intrabar displacement without sustained follow-through.
- Validation net_pnl: 620.0
- Validation profit_factor: 1.1484674329501916
- Validation hit_rate: 0.42188599577762137
- Test net_pnl: -179.0
- Test profit_factor: 0.9625679631953158
- Test hit_rate: 0.42596705533962614

### 2. H08 — Contrarian on ret_sum_5
- Rationale: Quick mean-reversion at very short lookback.
- Expected regime: Choppy microstructure periods.
- Validation net_pnl: 123.0
- Validation profit_factor: 1.0043617021276596
- Validation hit_rate: 0.4158175999060399
- Test net_pnl: 207.0
- Test profit_factor: 1.0063894805074545
- Test hit_rate: 0.44975997351431884
