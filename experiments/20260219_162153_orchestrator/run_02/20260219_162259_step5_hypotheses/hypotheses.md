# Step 5 Hypotheses

- Input: `/home/trevisan/repositories/open-data-scientist/experiments/20260219_162153_orchestrator/run_02/data/wdofut_features_v1.parquet`
- Cost per trade: `0.0`
- Thresholds: z=(0.05,0.90), spread=(0.03,0.90), vol_regime=(0.10,0.80)
- Top-K selected: `2`

## Top Candidates

### 1. H01 — Short after positive extreme z-score
- Rationale: Micro mean-reversion after stretched short-term move.
- Expected regime: High intrabar displacement without sustained follow-through.
- Validation net_pnl: 626.0
- Validation profit_factor: 1.1499760421657883
- Validation hit_rate: 0.422237860661506
- Test net_pnl: -153.0
- Test profit_factor: 0.9679379715004192
- Test hit_rate: 0.4274477142328336

### 2. H05 — Short when spread shock is extreme wide
- Rationale: Liquidity stress often coincides with adverse short-term drift.
- Expected regime: Spread expansion events.
- Validation net_pnl: 87.0
- Validation profit_factor: 1.4860335195530727
- Validation hit_rate: 0.539553752535497
- Test net_pnl: 59.0
- Test profit_factor: 1.2521367521367521
- Test hit_rate: 0.5140350877192983
