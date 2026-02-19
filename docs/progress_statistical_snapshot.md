# WDOFUT Research Progress Snapshot (Steps 0–8)

This file summarizes what has been completed so far, with method and statistics.

## Scope Completed

- Step 0: research contract definition.
- Step 1: dataset audit and integrity checks.
- Step 2: causal label construction (`y_tb`) with triple-barrier.
- Step 3: mandatory temporal OOS baselines.
- Step 4: causal feature set v1 + univariate scan against `y_tb`.
- Step 5: hypothesis generation and top-3 candidate selection.
- Step 6: walk-forward backtest for top-3 candidates.
- Step 7: robustness and placebo for selected candidate.
- Step 8: final GO/NO-GO verdict package.

Protocol reference: `docs/research_protocol.md`

---

## Method (what was done)

### Step 0 — Research contract

Contract file:
- `docs/research_contract_wdofut.json`

Current fixed parameters used in runs:
- horizon: `5 minutes`
- price column: `mid`
- label type: triple-barrier event (`y_tb`)
- split policy: temporal `60/20/20`
- current baseline cost assumption: `0.0`

### Step 1 — Dataset audit / integrity

Audit sources:
- `scripts/parquet_remount_validate.py`
- direct dataset inventory run (rows/day, schema, nulls, duplicates)

Validated prepared dataset:
- base: `data/wdofut_prepared`
- parquet files: `18,967`
- total rows: `558,895`
- duplicate `ts` rows: `0`
- critical nulls:
  - `ts`: `0`
  - `timestamp`: `0`
  - `spread`: `0`
  - `mid`: `0`
  - `log_return`: `18,955` (expected warmup/availability behavior)

Day range observed:
- first day: `2026-01-02`
- last day: `2026-02-03`

Integrity status:
- validation gate passed with `--full-json --strict-floats` and empty issue counts.

### Step 2 — Causal label (`y_tb`)

Label script:
- `scripts/run_wdofut_step2_label.py`

Definition used:
- Horizon: `H = 5 minutes`
- Price: `mid`
- Triple-barrier:
  - upper `u = 0.00035` (log-return)
  - lower `d = 0.00035` (log-return)
- Label rule:
  - `+1` if upper barrier is touched first in `(t, t+H]`
  - `-1` if lower barrier is touched first in `(t, t+H]`
  - `0` if neither barrier is touched inside horizon

Anti-leakage:
- features anchored at `t` or earlier
- label computed strictly from future window `(t, t+H]`

Command used:

```bash
./.venv/bin/python3 scripts/run_wdofut_step2_label.py \
  --input-dir ./data/wdofut_prepared \
  --h-minutes 5 \
  --price-col mid \
  --up-barrier 0.00035 \
  --down-barrier 0.00035 \
  --output-parquet ./data/wdofut_prepared/wdofut_labels_tb.parquet \
  --output-summary ./data/wdofut_prepared/wdofut_labels_tb_summary.json
```

### Step 3 — Temporal OOS baselines

Baseline script:
- `scripts/run_wdofut_step3_baselines.py`

Split:
- train 60% / val 20% / test 20% (temporal order)

Baselines:
1. `no_trade`
2. `lagged_return_sign`
3. `spread_vol_rule`

Cost assumption:
- `cost_per_trade = 0.0` (current run)

Command used:

```bash
./.venv/bin/python3 scripts/run_wdofut_step3_baselines.py \
  --input-parquet ./data/wdofut_prepared/wdofut_labels_tb.parquet \
  --output-json ./data/wdofut_prepared/wdofut_baselines_metrics.json
```

### Step 4 — Causal feature set + univariate scan

Feature script:
- `scripts/run_wdofut_step4_feature_scan.py`

Feature families:
- lagged returns: `ret_lag1`, `ret_lag2`
- momentum windows: `ret_sum_5`, `ret_sum_10`, `ret_sum_20`
- volatility: `vol_5`, `vol_20`, `vol_60`
- normalization/regime: `zret_20`, `vol_regime_20_over_60`
- liquidity/spread: `spread_lag1`, `spread_delta1`, `spread_z_20`

Scores:
- Pearson correlation vs `y_tb`
- Spearman correlation vs `y_tb`
- Q4-Q1 mean-`y_tb` difference

Command used:

```bash
./.venv/bin/python3 scripts/run_wdofut_step4_feature_scan.py \
  --input-parquet ./data/wdofut_prepared/wdofut_labels_tb.parquet \
  --output-features-parquet ./data/wdofut_prepared/wdofut_features_v1.parquet \
  --output-json ./data/wdofut_prepared/wdofut_feature_scan.json
```

---

## Statistical Results (current)

### Step 1 audit summary

Key audit metrics:
- rows: `558,895`
- partitions (days): `23`
- duplicate timestamp rows: `0`
- timestamp coverage per day: generally session-consistent (UTC intraday ranges)

Interpretation:
- dataset quality is sufficient to proceed to supervised research stages.

### Step 2 label summary

Source:
- `data/wdofut_prepared/wdofut_labels_tb_summary.json`

Results:
- rows: `558,895`
- label counts:
  - `-1`: `217,739`
  - `0`: `135,751`
  - `+1`: `205,405`
- `% zero`: `0.2428917775`
- skewness: `0.0425971684`

Interpretation:
- class distribution is reasonably balanced between `-1` and `+1`, with ~24.3% neutral.

### Step 3 baseline summary (OOS = val + test)

Source:
- `data/wdofut_prepared/wdofut_baselines_metrics.json`

Results:
- `no_trade`
  - OOS rows: `223,558`
  - trades: `0`
  - net_pnl: `0.0`

- `lagged_return_sign`
  - OOS trades: `100,920`
  - net_pnl: `-415.0`
  - OOS hit_rate: `0.4216`

- `spread_vol_rule`
  - OOS trades: `44,929`
  - net_pnl: `-151.0`
  - OOS hit_rate: `0.3941`

Interpretation:
- none of the baseline rules beat `no_trade` in OOS under current setup.

### Step 4 feature scan summary (test split)

Source:
- `data/wdofut_prepared/wdofut_feature_scan.json`

Top by absolute Spearman (test):
1. `spread_z_20`: `|rho| = 0.0145`
2. `ret_sum_20`: `|rho| = 0.0056`
3. `ret_sum_10`: `|rho| = 0.0049`
4. `vol_20`: `|rho| = 0.0045`
5. `vol_60`: `|rho| = 0.0044`

Interpretation:
- univariate signal strength is weak (all near zero), which is expected at this stage.
- this is a clean baseline for Step 5 hypothesis-driven rule testing.

---

## Artifacts Produced

- `data/wdofut_prepared/wdofut_labels_tb.parquet`
- `data/wdofut_prepared/wdofut_labels_tb_summary.json`
- `data/wdofut_prepared/wdofut_baselines_metrics.json`
- `data/wdofut_prepared/wdofut_features_v1.parquet`
- `data/wdofut_prepared/wdofut_feature_scan.json`

---

## Next Protocol Step

Step 5:
- generate rule-based hypotheses
- implement and backtest top candidates
- keep temporal OOS discipline and compare against Step 3 baselines

---

## Steps 5–8 (executed)

### Step 5 — Rule-based hypotheses and candidate selection

Objective:
- define 10 microstructure hypotheses
- select top 3 by plausibility and overfit risk

Method:
- use Step 4 features as signal primitives
- define explicit entry/exit rules
- keep rules interpretable and causal

Produced artifacts:
- `experiments/20260219_122302_step5_hypotheses/hypotheses.md`
- `experiments/20260219_122302_step5_hypotheses/hypotheses_full.json`
- `experiments/20260219_122302_step5_hypotheses/candidates_top3.json`

Top-3 selected:
- `H01` — Short after positive extreme z-score
- `H07` — Momentum on ret_sum_10
- `H05` — Short when spread shock is extreme wide

### Step 6 — Walk-forward backtest with constraints

Objective:
- run event-driven backtests for top candidates
- evaluate on temporal train/val/test and rolling windows

Method:
- fixed execution assumptions from contract
- enforce no leakage in rule evaluation
- compare directly against Step 3 baseline metrics

Produced artifacts:
- `experiments/20260219_122825_step6_backtest/metrics.json`
- `experiments/20260219_122825_step6_backtest/metrics_by_window.json`
- `experiments/20260219_122825_step6_backtest/trades.parquet`

Validation/Test snapshot:
- `H01`: val `+440`, test `-117`
- `H07`: val `+342`, test `-604`
- `H05`: val `+47`, test `+30`

Candidate for Step 7:
- `H05`

### Step 7 — Robustness and anti-false-edge checks

Objective:
- reject unstable or non-causal apparent edges

Method:
- parameter sensitivity sweep (small grid)
- stability by day/session/regime
- block bootstrap confidence intervals
- placebo tests (label shuffle and/or sign inversion)

Produced artifacts:
- `experiments/20260219_130039_step7_robustness/robustness.json`
- `experiments/20260219_130039_step7_robustness/placebo.json`

Key robustness findings (`H05`):
- base test net_pnl: `+3.0`
- shuffled-label placebo net_pnl: `+19.0` (strong warning)
- inverted-signal net_pnl: `-3.0`
- sensitivity best test net_pnl: `+57.0` at quantile `0.90`, cost `0.0`

### Step 8 — Final decision package

Objective:
- produce binary outcome: continue vs discard

Decision logic:
- GO only if OOS beats baselines consistently and survives robustness
- NO-GO otherwise

Produced artifacts:
- `experiments/20260219_130700_step8_verdict/verdict.md`
- `experiments/20260219_130700_step8_verdict/summary.json`

Decision:
- **NO-GO**

Reason (high level):
- baseline beat is not robust enough under placebo checks
- observed edge magnitude is small and unstable

---

## Orchestrator Runs (bounded search)

Script:
- `scripts/run_wdofut_orchestrator.py`

Recent run:
- `experiments/20260219_131512_orchestrator/orchestrator_results.json`

Results:
- runs executed: `3`
- best valid (GO): `None`
- run summaries:
  - cost `0.00`: NO-GO, `H05` test net `+30.0`, PF `1.1310`
  - cost `0.01`: NO-GO, `H05` test net `+24.35`, PF `1.1049`
  - cost `0.02`: NO-GO, `H05` test net `+18.70`, PF `1.0795`

## Current Status (as of now)

- Step 0: complete
- Step 1: complete
- Step 2: complete
- Step 3: complete
- Step 4: complete
- Step 5: complete
- Step 6: complete
- Step 7: complete
- Step 8: complete
- Current decision: **NO-GO**
