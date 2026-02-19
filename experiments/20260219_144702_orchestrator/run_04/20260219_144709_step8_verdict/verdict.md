# Verdict

- Experiment: `20260219_144709_step8_verdict`
- Candidate: `H01`
- Decision: **NO-GO**

## Why
- OOS baseline comparison: H01 (val+test) = `323.0000` vs no-trade = `0.0000`
- Test performance: net_pnl = `-117.0000`, profit_factor = `0.9521`
- Placebo check: base = `31.0000`, shuffled-label = `18.0000`, inverted-signal = `-31.0000`
- Sensitivity positive ratio (test): `86.67%`

## Rule Checks
- beats_baseline_oos: `True`
- test_profit_factor_ge_1.0: `False`
- placebo_outperforms_randomized_label: `True`
- inversion_not_equivalent: `True`
- sensitivity_positive_ratio_ge_0.6: `True`

## Next Action
- If NO-GO: redesign hypotheses and repeat Step 5 with stricter regime logic.