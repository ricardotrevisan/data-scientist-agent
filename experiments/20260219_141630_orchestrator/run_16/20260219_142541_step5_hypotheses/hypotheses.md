# Step 5 Hypotheses

- Input: `/home/trevisan/repositories/open-data-scientist/experiments/20260219_141630_orchestrator/run_16/data/wdofut_features_v1.parquet`
- Cost per trade: `0.0`
- Thresholds: z=(0.05,0.95), spread=(0.05,0.93), vol_regime=(0.15,0.85)
- Top-K selected: `3`

## Top Candidates

### 1. H01 — Short after positive extreme z-score
- Rationale: Micro mean-reversion after stretched short-term move.
- Expected regime: High intrabar displacement without sustained follow-through.
- Validation net_pnl: 344.0
- Validation profit_factor: 1.2156739811912225
- Validation hit_rate: 0.33575757575757575
- Test net_pnl: -199.0
- Test profit_factor: 0.9100768187980117
- Test hit_rate: 0.34965277777777776

### 2. H07 — Momentum on ret_sum_10
- Rationale: Simple continuation baseline at intermediate lookback.
- Expected regime: Directional short-term flow.
- Validation net_pnl: 351.0
- Validation profit_factor: 1.013765785551808
- Validation hit_rate: 0.3308248544186344
- Test net_pnl: 231.0
- Test profit_factor: 1.0072909762333113
- Test hit_rate: 0.387117903930131

### 3. H05 — Short when spread shock is extreme wide
- Rationale: Liquidity stress often coincides with adverse short-term drift.
- Expected regime: Spread expansion events.
- Validation net_pnl: 37.0
- Validation profit_factor: 1.2450331125827814
- Validation hit_rate: 0.42630385487528344
- Test net_pnl: 2.0
- Test profit_factor: 1.01
- Test hit_rate: 0.3818525519848771
