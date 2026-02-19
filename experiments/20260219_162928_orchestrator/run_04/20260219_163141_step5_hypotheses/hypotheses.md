# Step 5 Hypotheses

- Input: `/home/trevisan/repositories/open-data-scientist/experiments/20260219_162928_orchestrator/run_04/data/wdofut_features_v1.parquet`
- Cost per trade: `0.0`
- Thresholds: z=(0.05,0.90), spread=(0.03,0.90), vol_regime=(0.10,0.80)
- Top-K selected: `2`

## Top Candidates

### 1. H01 — Short after positive extreme z-score
- Rationale: Micro mean-reversion after stretched short-term move.
- Expected regime: High intrabar displacement without sustained follow-through.
- Validation net_pnl: 423.0
- Validation profit_factor: 1.1175979983319433
- Validation hit_rate: 0.35362420830401126
- Test net_pnl: -117.0
- Test profit_factor: 0.9725609756097561
- Test hit_rate: 0.383768276883213

### 2. H05 — Short when spread shock is extreme wide
- Rationale: Liquidity stress often coincides with adverse short-term drift.
- Expected regime: Spread expansion events.
- Validation net_pnl: 87.0
- Validation profit_factor: 1.5506329113924051
- Validation hit_rate: 0.4969574036511156
- Test net_pnl: 42.0
- Test profit_factor: 1.1917808219178083
- Test hit_rate: 0.45789473684210524
