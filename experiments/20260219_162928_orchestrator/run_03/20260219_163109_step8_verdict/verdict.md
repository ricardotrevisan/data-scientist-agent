# Verdict

- Experiment: `20260219_163109_step8_verdict`
- Candidate: `H02`
- Decision: **NO-GO**

## Why
- OOS baseline comparison: H02 (val+test) = `1260.0000` vs no-trade = `0.0000`
- Test performance: net_pnl = `769.0000`, profit_factor = `1.4756`
- Placebo check: base = `-185.0000`, shuffled-label = `-188.0000`, inverted-signal = `185.0000`
- Sensitivity positive ratio (test): `0.00%`

## Rule Checks
- beats_baseline_oos: `True`
- test_profit_factor_ge_1.05: `True`
- placebo_outperforms_randomized_label: `True`
- inversion_not_equivalent: `True`
- sensitivity_positive_ratio_ge_0.5: `False`

## Next Action
- If NO-GO: redesign hypotheses and repeat Step 5 with stricter regime logic.