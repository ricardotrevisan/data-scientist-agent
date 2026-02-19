# Verdict

- Experiment: `20260219_142724_step8_verdict`
- Candidate: `H01`
- Decision: **NO-GO**

## Why
- OOS baseline comparison: H01 (val+test) = `373.0000` vs no-trade = `0.0000`
- Test performance: net_pnl = `-18.0000`, profit_factor = `0.9932`
- Placebo check: base = `35.0000`, shuffled-label = `32.0000`, inverted-signal = `-35.0000`
- Sensitivity positive ratio (test): `60.00%`

## Rule Checks
- beats_baseline_oos: `True`
- test_profit_factor_ge_1.05: `False`
- placebo_outperforms_randomized_label: `True`
- inversion_not_equivalent: `False`
- sensitivity_positive_ratio_ge_0.5: `True`

## Next Action
- If NO-GO: redesign hypotheses and repeat Step 5 with stricter regime logic.