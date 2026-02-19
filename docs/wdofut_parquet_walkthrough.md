# WDOFUT End-to-End Runbook

This runbook is the operational path from raw data to edge/alpha analysis with the agent.

Before running, read role boundaries:
- `docs/system_usage_map.md`

Important:
- For the current canonical operational path, prefer `RUNBOOK.md`.
- This document is kept as a practical walkthrough companion.

## 0. Current-state shortcut

If you already have `data/wdofut_prepared` validated, jump to:
- Step 4 (Docker interpreter up)
- Step 5 (start agent)
- Step 6 (prompt ladder for alpha/edge)

## 1. Environment + API key

```bash
cd /home/trevisan/repositories/open-data-scientist
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Create `.env` in repo root:

```env
OPENAI_API_KEY=your_openai_key_here
ODS_MODEL=gpt-5-mini
```

## 1.1 Contract + audit entrypoints

```bash
./.venv/bin/python3 scripts/run_wdofut_step0_contract.py \
  --contract ./docs/research_contract_wdofut.json \
  --output-json ./data/wdofut_prepared/step0_contract_resolved.json

./.venv/bin/python3 scripts/run_wdofut_step1_audit.py \
  --input-dir ./data/wdofut_prepared \
  --output-json ./data/wdofut_prepared/step1_audit_report.json
```

## 2. Data preparation (choose one path)

### 2A) One-command pipeline (raw archives -> prepared -> validate)

```bash
./.venv/bin/python3 scripts/wdofut_pipeline.py \
  --raw-dir ./data/raw \
  --work-dir ./data/raw_extracted \
  --output-dir ./data/wdofut_prepared \
  --start-date 2026-01-02 \
  --end-date 2026-02-03 \
  --max-files 200
```

### 2B) Raw parquet already available (no archive extraction)

```bash
./.venv/bin/python3 scripts/prepare_wdofut.py \
  --input ./data/raw/ticker=WDOFUT_F_0 \
  --output-dir ./data/wdofut_prepared \
  --start-date 2026-01-02 \
  --end-date 2026-02-03
```

## 3. Validation gate (required)

```bash
./.venv/bin/python3 scripts/parquet_remount_validate.py \
  --parquet-base ./data/wdofut_prepared \
  --full-json \
  --strict-floats
```

Pass criteria:
- `issue_counts` is empty.
- Exit code is `0`.

Optional strict drift check:

```bash
./.venv/bin/python3 scripts/parquet_remount_validate.py \
  --parquet-base ./data/wdofut_prepared \
  --full-json \
  --strict-floats \
  --enforce-shape
```

## 4. Start internal executor (Docker)

```bash
cd interpreter
docker-compose up --build -d
cd ..
curl -s http://localhost:8123/health
```

Expected:
- `{"status":"healthy"}` (or equivalent healthy response)

## 5. Run Step 2 first (label)

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

## 6. Run Steps 3–8 (scripted pipeline)

```bash
./.venv/bin/python3 scripts/run_wdofut_step3_baselines.py \
  --input-parquet ./data/wdofut_prepared/wdofut_labels_tb.parquet \
  --output-json ./data/wdofut_prepared/wdofut_baselines_metrics.json

./.venv/bin/python3 scripts/run_wdofut_step4_feature_scan.py \
  --input-parquet ./data/wdofut_prepared/wdofut_labels_tb.parquet \
  --output-features-parquet ./data/wdofut_prepared/wdofut_features_v1.parquet \
  --output-json ./data/wdofut_prepared/wdofut_feature_scan.json

./.venv/bin/python3 scripts/run_wdofut_step5_hypotheses.py \
  --input-parquet ./data/wdofut_prepared/wdofut_features_v1.parquet \
  --output-root ./experiments

./.venv/bin/python3 scripts/run_wdofut_step6_backtest.py \
  --input-features ./data/wdofut_prepared/wdofut_features_v1.parquet \
  --output-root ./experiments

./.venv/bin/python3 scripts/run_wdofut_step7_robustness.py \
  --input-features ./data/wdofut_prepared/wdofut_features_v1.parquet \
  --output-root ./experiments

./.venv/bin/python3 scripts/run_wdofut_step8_verdict.py \
  --baselines-json ./data/wdofut_prepared/wdofut_baselines_metrics.json \
  --output-root ./experiments
```

## 7. Optional orchestrator (auto-derive)

```bash
./.venv/bin/python3 scripts/run_wdofut_orchestrator.py \
  --auto-derive \
  --features-parquet ./data/wdofut_prepared/wdofut_features_v1.parquet \
  --baselines-json ./data/wdofut_prepared/wdofut_baselines_metrics.json \
  --cost-grid 0.0 0.01 \
  --spread-upper-grid 0.93 0.95 0.97 \
  --top-k-grid 2 3 \
  --num-windows-grid 4 6 \
  --min-test-profit-factor-grid 1.0 1.05 \
  --min-sensitivity-positive-ratio-grid 0.5 0.6 \
  --require-placebo-outperform-shuffle \
  --require-inversion-nonequivalent \
  --max-runs 20 \
  --output-root ./experiments
```

If you want each run to derive labels/features internally (Step 2 -> 8 per run), add:
- `--derive-labels`
- `--h-minutes-grid ...`
- `--up-barrier-grid ...`
- `--down-barrier-grid ...`
- `--price-col-grid ...`

## 8. Start the agent

```bash
open-data-scientist \
  --provider openai \
  --executor internal \
  --model gpt-5-mini \
  --temperature 0.0 \
  --max-output-tokens 4000 \
  --timeout 120 \
  --data-dir ./data/wdofut_prepared \
  --save-trace
```

## 9. Prompt ladder for edge/alpha generation

Use prompts in this order.

### Prompt 1: Baseline dataset audit

```text
List all files and parquet partitions. Report rows by day, schema (columns/dtypes), null rates, duplicate timestamps, and min/max timestamp per day. No plots.
```

### Prompt 2: Feature baseline

```text
Create a compact feature table with timestamp-indexed rows using available fields from feed/state/derived, plus spread, mid, and short-horizon returns (1, 2, 5, 10 steps). Report feature availability and summary stats by hour.
```

### Prompt 3: Edge candidates

```text
Search for edge candidates predicting forward returns using:
1) spread regime,
2) flow/imbalance proxies,
3) volatility/effort-vs-result signals.
Use simple, interpretable rules and report effect size, hit rate, and sample count.
```

### Prompt 4: Validation (anti-overfit)

```text
Validate top candidates with strict time split:
- train: earliest 60% of days
- validation: next 20%
- test: last 20%
Include transaction cost assumptions and reject candidates that fail on out-of-sample test.
```

### Prompt 5: Deployable shortlist

```text
Return only robust edges that survive test set with positive net expectancy after costs. For each edge provide rule definition, active hours, expected trades/day, and risk notes.
```

## 10. Optional combined dataframe cache

```bash
./.venv/bin/python3 scripts/load_prepared_to_df.py \
  --input-dir ./data/wdofut_prepared \
  --combined-parquet ./data/wdofut_combined.parquet
```

## 11. Troubleshooting

1. `OPENAI_API_KEY environment variable not set`
- Check `.env` in repo root.

2. Docker executor unavailable
- Re-run `docker-compose up --build -d` in `interpreter/`.

3. `No usable archives`
- Raw archives are invalid/empty; place valid files in `data/raw`.

4. Shape mismatch only (`--enforce-shape`)
- Treat as drift warning unless critical path/type checks fail.
