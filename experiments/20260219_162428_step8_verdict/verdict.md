# Verdict

- Experiment: `20260219_162428_step8_verdict`
- Candidate: `H05`
- Decision: **GO**

## Why
- OOS baseline comparison: H05 (val+test) = `188.0000` vs no-trade = `0.0000`
- Test performance: net_pnl = `100.0000`, profit_factor = `1.3067`
- Placebo check: base = `65.0000`, shuffled-label = `95.0000`, inverted-signal = `-65.0000`
- Sensitivity positive ratio (test): `100.00%`

## Rule Checks
- beats_baseline_oos: `True`
- test_profit_factor_ge_1.0: `True`
- placebo_outperforms_randomized_label: `True`
- inversion_not_equivalent: `True`
- sensitivity_positive_ratio_ge_0.5: `True`

## Next Action
- If NO-GO: redesign hypotheses and repeat Step 5 with stricter regime logic.