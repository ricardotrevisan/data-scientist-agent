# Step 5 Hypotheses

- Input: `/home/trevisan/repositories/open-data-scientist/experiments/20260219_162928_orchestrator/run_07/data/wdofut_features_v1.parquet`
- Cost per trade: `0.0`
- Thresholds: z=(0.05,0.90), spread=(0.03,0.90), vol_regime=(0.10,0.80)
- Top-K selected: `2`

## Top Candidates

### 1. H01 — Short after positive extreme z-score
- Rationale: Micro mean-reversion after stretched short-term move.
- Expected regime: High intrabar displacement without sustained follow-through.
- Validation net_pnl: 1847.0
- Validation profit_factor: 1.7999133824166307
- Validation hit_rate: 0.3655876143560873
- Test net_pnl: 1293.0
- Test profit_factor: 1.4136276391554703
- Test hit_rate: 0.40893947806774017

### 2. H05 — Short when spread shock is extreme wide
- Rationale: Liquidity stress often coincides with adverse short-term drift.
- Expected regime: Spread expansion events.
- Validation net_pnl: 132.0
- Validation profit_factor: 2.073170731707317
- Validation hit_rate: 0.5172413793103449
- Test net_pnl: 103.0
- Test profit_factor: 1.5819209039548023
- Test hit_rate: 0.49122807017543857
