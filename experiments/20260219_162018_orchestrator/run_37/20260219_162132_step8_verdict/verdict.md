# Verdict

- Experiment: `20260219_162132_step8_verdict`
- Candidate: `H01`
- Decision: **NO-GO**

## Why
- OOS baseline comparison: H01 (val+test) = `656.0000` vs no-trade = `0.0000`
- Test performance: net_pnl = `-273.0000`, profit_factor = `0.9441`
- Placebo check: base = `57.0000`, shuffled-label = `43.0000`, inverted-signal = `-57.0000`
- Sensitivity positive ratio (test): `86.67%`

## Rule Checks
- beats_baseline_oos: `True`
- test_profit_factor_ge_1.0: `False`
- placebo_outperforms_randomized_label: `True`
- inversion_not_equivalent: `True`
- sensitivity_positive_ratio_ge_0.5: `True`

## Next Action
- If NO-GO: redesign hypotheses and repeat Step 5 with stricter regime logic.