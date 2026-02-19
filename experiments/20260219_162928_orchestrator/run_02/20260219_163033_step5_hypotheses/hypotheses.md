# Step 5 Hypotheses

- Input: `/home/trevisan/repositories/open-data-scientist/experiments/20260219_162928_orchestrator/run_02/data/wdofut_features_v1.parquet`
- Cost per trade: `0.0`
- Thresholds: z=(0.05,0.90), spread=(0.03,0.90), vol_regime=(0.10,0.80)
- Top-K selected: `2`

## Top Candidates

### 1. H01 — Short after positive extreme z-score
- Rationale: Micro mean-reversion after stretched short-term move.
- Expected regime: High intrabar displacement without sustained follow-through.
- Validation net_pnl: 407.0
- Validation profit_factor: 1.112836151926809
- Validation hit_rate: 0.3530964109781844
- Test net_pnl: -165.0
- Test profit_factor: 0.9615205223880597
- Test hit_rate: 0.3815472885434018

### 2. H08 — Contrarian on ret_sum_5
- Rationale: Quick mean-reversion at very short lookback.
- Expected regime: Choppy microstructure periods.
- Validation net_pnl: 83.0
- Validation profit_factor: 1.00340932429657
- Validation hit_rate: 0.35863405467304815
- Test net_pnl: 126.0
- Test profit_factor: 1.0042550317438876
- Test hit_rate: 0.41022457650499367
