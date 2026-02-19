# Step 5 Hypotheses

- Input: `/home/trevisan/repositories/open-data-scientist/experiments/20260219_141630_orchestrator/run_06/data/wdofut_features_v1.parquet`
- Cost per trade: `0.0`
- Thresholds: z=(0.05,0.95), spread=(0.05,0.93), vol_regime=(0.15,0.85)
- Top-K selected: `3`

## Top Candidates

### 1. H02 — Long after negative extreme z-score
- Rationale: Symmetric mean-reversion for downside stretch.
- Expected regime: Short-lived panic downticks.
- Validation net_pnl: 394.0
- Validation profit_factor: 1.2142468733007068
- Validation hit_rate: 0.38983938547486036
- Test net_pnl: 819.0
- Test profit_factor: 1.4296956977964324
- Test hit_rate: 0.4780701754385965

### 2. H08 — Contrarian on ret_sum_5
- Rationale: Quick mean-reversion at very short lookback.
- Expected regime: Choppy microstructure periods.
- Validation net_pnl: 314.0
- Validation profit_factor: 1.012379750827945
- Validation hit_rate: 0.3769856417182958
- Test net_pnl: -115.0
- Test profit_factor: 0.9962265389158682
- Test hit_rate: 0.41881862826242894

### 3. H06 — Long when spread is unusually compressed
- Rationale: Tighter spread can favor continuation with lower friction.
- Expected regime: High-liquidity micro regime.
- Validation net_pnl: 70.0
- Validation profit_factor: 1.9210526315789473
- Validation hit_rate: 0.5509433962264151
- Test net_pnl: 31.0
- Test profit_factor: 1.2818181818181817
- Test hit_rate: 0.4504792332268371
