# Verdict

- Experiment: `20260219_163324_step8_verdict`
- Candidate: `H01`
- Decision: **GO**

## Why
- OOS baseline comparison: H01 (val+test) = `3150.0000` vs no-trade = `0.0000`
- Test performance: net_pnl = `1329.0000`, profit_factor = `1.4115`
- Placebo check: base = `195.0000`, shuffled-label = `200.0000`, inverted-signal = `-195.0000`
- Sensitivity positive ratio (test): `100.00%`

## Rule Checks
- beats_baseline_oos: `True`
- test_profit_factor_ge_1.05: `True`
- placebo_outperforms_randomized_label: `True`
- inversion_not_equivalent: `True`
- sensitivity_positive_ratio_ge_0.5: `True`

## Next Action
- If NO-GO: redesign hypotheses and repeat Step 5 with stricter regime logic.