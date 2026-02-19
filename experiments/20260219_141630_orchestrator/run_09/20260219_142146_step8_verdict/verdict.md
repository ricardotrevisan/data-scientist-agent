# Verdict

- Experiment: `20260219_142146_step8_verdict`
- Candidate: `H01`
- Decision: **NO-GO**

## Why
- OOS baseline comparison: H01 (val+test) = `1703.0000` vs no-trade = `0.0000`
- Test performance: net_pnl = `658.0000`, profit_factor = `1.3359`
- Placebo check: base = `66.0000`, shuffled-label = `131.0000`, inverted-signal = `-66.0000`
- Sensitivity positive ratio (test): `100.00%`

## Rule Checks
- beats_baseline_oos: `True`
- test_profit_factor_ge_1.0: `True`
- placebo_outperforms_randomized_label: `False`
- inversion_not_equivalent: `False`
- sensitivity_positive_ratio_ge_0.5: `True`

## Next Action
- If NO-GO: redesign hypotheses and repeat Step 5 with stricter regime logic.