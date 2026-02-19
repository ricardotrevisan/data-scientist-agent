# Step 5 Hypotheses

- Input: `/home/trevisan/repositories/open-data-scientist/experiments/20260219_141630_orchestrator/run_02/data/wdofut_features_v1.parquet`
- Cost per trade: `0.0`
- Thresholds: z=(0.05,0.95), spread=(0.05,0.93), vol_regime=(0.15,0.85)
- Top-K selected: `3`

## Top Candidates

### 1. H01 — Short after positive extreme z-score
- Rationale: Micro mean-reversion after stretched short-term move.
- Expected regime: High intrabar displacement without sustained follow-through.
- Validation net_pnl: 374.0
- Validation profit_factor: 1.1790330301579703
- Validation hit_rate: 0.4264935064935065
- Test net_pnl: -51.0
- Test profit_factor: 0.9798498617147372
- Test hit_rate: 0.4305555555555556

### 2. H08 — Contrarian on ret_sum_5
- Rationale: Quick mean-reversion at very short lookback.
- Expected regime: Choppy microstructure periods.
- Validation net_pnl: 100.0
- Validation profit_factor: 1.0035459735470373
- Validation hit_rate: 0.4154946119740435
- Test net_pnl: 209.0
- Test profit_factor: 1.0064577926090719
- Test hit_rate: 0.4493323401202891

### 3. H05 — Short when spread shock is extreme wide
- Rationale: Liquidity stress often coincides with adverse short-term drift.
- Expected regime: Spread expansion events.
- Validation net_pnl: 53.0
- Validation profit_factor: 1.3173652694610778
- Validation hit_rate: 0.4988662131519274
- Test net_pnl: 31.0
- Test profit_factor: 1.1409090909090909
- Test hit_rate: 0.47448015122873344
