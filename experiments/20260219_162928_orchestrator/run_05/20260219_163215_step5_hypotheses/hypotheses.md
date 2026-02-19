# Step 5 Hypotheses

- Input: `/home/trevisan/repositories/open-data-scientist/experiments/20260219_162928_orchestrator/run_05/data/wdofut_features_v1.parquet`
- Cost per trade: `0.0`
- Thresholds: z=(0.05,0.90), spread=(0.03,0.90), vol_regime=(0.10,0.80)
- Top-K selected: `2`

## Top Candidates

### 1. H01 — Short after positive extreme z-score
- Rationale: Micro mean-reversion after stretched short-term move.
- Expected regime: High intrabar displacement without sustained follow-through.
- Validation net_pnl: 416.0
- Validation profit_factor: 1.1156197887715398
- Validation hit_rate: 0.3530964109781844
- Test net_pnl: -145.0
- Test profit_factor: 0.966058052434457
- Test hit_rate: 0.3819174532667037

### 2. H05 — Short when spread shock is extreme wide
- Rationale: Liquidity stress often coincides with adverse short-term drift.
- Expected regime: Spread expansion events.
- Validation net_pnl: 63.0
- Validation profit_factor: 1.3818181818181818
- Validation hit_rate: 0.46247464503042596
- Test net_pnl: 16.0
- Test profit_factor: 1.0701754385964912
- Test hit_rate: 0.4280701754385965
