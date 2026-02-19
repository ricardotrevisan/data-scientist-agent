# RUNBOOK (Single Source of Truth)

Use this file first when resuming in a new session.

## 1) Project in 5 lines

- Repo for WDOFUT snapshot research with reproducible data pipeline + agent analysis.
- Heavy deterministic steps run in `scripts/*`.
- Interactive interpretation/report runs in `open-data-scientist` agent.
- Internal executor uses Docker interpreter (`interpreter/`) with mounted data.
- Goal: edge research with protocol (`docs/research_protocol.md`) and auditable artifacts.

## 2) Official flow (must follow in order)

1. Run Step 0 contract validation
2. Run Step 1 dataset audit
3. Build labels (Step 2)
4. Run Step 3 baselines (OOS temporal)
5. Run Step 4 feature scan (causal, univariate)
6. Run Step 5 hypotheses
7. Run Step 6 backtest
8. Run Step 7 robustness/placebo
9. Run Step 8 verdict
10. (Optional) run orchestrator for bounded multi-cycle search

## 3) One command per step

### Step 0 — Environment

```bash
cd /home/trevisan/repositories/open-data-scientist
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Step 1 — Start interpreter (required for `--executor internal`)

```bash
docker compose -f interpreter/docker-compose.yml up -d --build
curl -s http://localhost:8123/health
```

Expected:

```json
{"status":"healthy"}
```

### Step 2 — Step 0 contract validation

```bash
./.venv/bin/python3 scripts/run_wdofut_step0_contract.py \
  --contract ./docs/research_contract_wdofut.json \
  --output-json ./data/wdofut_prepared/step0_contract_resolved.json
```

Expected output:
- `data/wdofut_prepared/step0_contract_resolved.json` with `"status": "ok"`

### Step 3 — Step 1 dataset audit

```bash
./.venv/bin/python3 scripts/run_wdofut_step1_audit.py \
  --input-dir ./data/wdofut_prepared \
  --output-json ./data/wdofut_prepared/step1_audit_report.json
```

Expected output:
- `data/wdofut_prepared/step1_audit_report.json`

### Step 4 — Prepare (if needed)

```bash
./.venv/bin/python3 scripts/prepare_wdofut.py \
  --input ./data/raw/ticker=WDOFUT_F_0 \
  --output-dir ./data/wdofut_prepared
```

Expected output folder:
- `data/wdofut_prepared/day=YYYY-MM-DD/...parquet`

### Step 5 — Validate

```bash
./.venv/bin/python3 scripts/parquet_remount_validate.py \
  --parquet-base ./data/wdofut_prepared \
  --full-json \
  --strict-floats
```

Success criteria:
- exit code `0`
- `issue_counts` empty

### Step 6 — Build labels (Protocol Step 2)

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

Expected outputs:
- `data/wdofut_prepared/wdofut_labels_tb.parquet`
- `data/wdofut_prepared/wdofut_labels_tb_summary.json`

### Step 7 — Step 3 baselines

```bash
./.venv/bin/python3 scripts/run_wdofut_step3_baselines.py \
  --input-parquet ./data/wdofut_prepared/wdofut_labels_tb.parquet \
  --output-json ./data/wdofut_prepared/wdofut_baselines_metrics.json
```

Expected output:
- `data/wdofut_prepared/wdofut_baselines_metrics.json`

### Step 8 — Step 4 feature scan

```bash
./.venv/bin/python3 scripts/run_wdofut_step4_feature_scan.py \
  --input-parquet ./data/wdofut_prepared/wdofut_labels_tb.parquet \
  --output-features-parquet ./data/wdofut_prepared/wdofut_features_v1.parquet \
  --output-json ./data/wdofut_prepared/wdofut_feature_scan.json
```

Expected outputs:
- `data/wdofut_prepared/wdofut_features_v1.parquet`
- `data/wdofut_prepared/wdofut_feature_scan.json`

### Step 9 — Step 5 hypotheses

```bash
./.venv/bin/python3 scripts/run_wdofut_step5_hypotheses.py \
  --input-parquet ./data/wdofut_prepared/wdofut_features_v1.parquet \
  --output-root ./experiments
```

Expected outputs:
- `experiments/<ts>_step5_hypotheses/hypotheses_full.json`
- `experiments/<ts>_step5_hypotheses/candidates_top3.json`
- `experiments/<ts>_step5_hypotheses/hypotheses.md`

### Step 10 — Step 6 backtest

```bash
./.venv/bin/python3 scripts/run_wdofut_step6_backtest.py \
  --input-features ./data/wdofut_prepared/wdofut_features_v1.parquet \
  --output-root ./experiments
```

Expected outputs:
- `experiments/<ts>_step6_backtest/metrics.json`
- `experiments/<ts>_step6_backtest/metrics_by_window.json`
- `experiments/<ts>_step6_backtest/trades.parquet`

### Step 11 — Step 7 robustness

```bash
./.venv/bin/python3 scripts/run_wdofut_step7_robustness.py \
  --input-features ./data/wdofut_prepared/wdofut_features_v1.parquet \
  --output-root ./experiments
```

Expected outputs:
- `experiments/<ts>_step7_robustness/robustness.json`
- `experiments/<ts>_step7_robustness/placebo.json`

### Step 12 — Step 8 verdict

```bash
./.venv/bin/python3 scripts/run_wdofut_step8_verdict.py \
  --baselines-json ./data/wdofut_prepared/wdofut_baselines_metrics.json \
  --output-root ./experiments
```

Expected outputs:
- `experiments/<ts>_step8_verdict/summary.json`
- `experiments/<ts>_step8_verdict/verdict.md`

### Step 13 — Orchestrator (bounded multi-cycle)

```bash
./.venv/bin/python3 scripts/run_wdofut_orchestrator.py \
  --features-parquet ./data/wdofut_prepared/wdofut_features_v1.parquet \
  --baselines-json ./data/wdofut_prepared/wdofut_baselines_metrics.json \
  --cost-grid 0.0 0.01 0.02 \
  --max-runs 3 \
  --output-root ./experiments
```

Expected output:
- `experiments/<ts>_orchestrator/orchestrator_results.json`

### Step 13A — Orchestrator with auto-derivation grids

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

### Step 13B — Orchestrator deriving labels/features inside each run

```bash
./.venv/bin/python3 scripts/run_wdofut_orchestrator.py \
  --auto-derive \
  --derive-labels \
  --label-input-dir ./data/wdofut_prepared \
  --cost-grid 0.0 0.01 \
  --h-minutes-grid 3 5 \
  --up-barrier-grid 0.00025 0.00035 \
  --down-barrier-grid 0.00025 0.00035 \
  --price-col-grid mid \
  --spread-upper-grid 0.93 0.95 0.97 \
  --top-k-grid 3 \
  --num-windows-grid 4 6 \
  --min-test-profit-factor-grid 1.0 1.05 \
  --min-sensitivity-positive-ratio-grid 0.5 0.6 \
  --require-placebo-outperform-shuffle \
  --require-inversion-nonequivalent \
  --max-runs 20 \
  --output-root ./experiments
```

Result layout is now run-scoped:
- `experiments/<orchestrator_id>/orchestrator_results.json`
- `experiments/<orchestrator_id>/run_XX/data/wdofut_labels_tb.parquet` (when `--derive-labels`)
- `experiments/<orchestrator_id>/run_XX/data/wdofut_baselines_metrics.json` (when `--derive-labels`)
- `experiments/<orchestrator_id>/run_XX/data/wdofut_features_v1.parquet` (when `--derive-labels`)
- `experiments/<orchestrator_id>/run_XX/<timestamp>_step5_hypotheses/*`
- `experiments/<orchestrator_id>/run_XX/<timestamp>_step6_backtest/*`
- `experiments/<orchestrator_id>/run_XX/<timestamp>_step7_robustness/*`
- `experiments/<orchestrator_id>/run_XX/<timestamp>_step8_verdict/*`

### Step 14 — Agent (interpretation/report only)

```bash
open-data-scientist \
  --provider openai \
  --executor internal \
  --model gpt-5-mini \
  --data-dir ./data/wdofut_prepared \
  --iterations 3
```

## 4) Where each component is used

- Deterministic pipeline: `scripts/*`
- Agent loop: `open_data_scientist/*`
- Execution runtime: `interpreter/*`
- Protocol: `docs/research_protocol.md`
- Contract template: `docs/research_contract_wdofut.json`
- System map: `docs/system_usage_map.md`
- Statistical snapshot: `docs/progress_statistical_snapshot.md`

## 5) Fast diagnostics (if something breaks)

### A) Docker not reachable

```bash
docker compose -f interpreter/docker-compose.yml ps
curl -s http://localhost:8123/health
```

### B) Agent starts but sees empty data

Check mount path in container:

```bash
curl -sS -X POST http://localhost:8123/execute \
  -H 'Content-Type: application/json' \
  -d '{"code":"import os; print(os.getcwd()); print(os.listdir()[:5])","workdir":"/app/data/wdofut_prepared"}'
```

### C) Too much API spend

- Keep `--iterations` low (e.g., `3`)
- Keep `--max-output-tokens` controlled
- Use scripts for heavy compute, not the agent
- Set in `.env`:

```env
OPENAI_LOG=error
```

## 6) If you are lost tomorrow

Run exactly this sequence:

```bash
source .venv/bin/activate
docker compose -f interpreter/docker-compose.yml up -d --build
./.venv/bin/python3 scripts/run_wdofut_step0_contract.py --contract ./docs/research_contract_wdofut.json --output-json ./data/wdofut_prepared/step0_contract_resolved.json
./.venv/bin/python3 scripts/run_wdofut_step1_audit.py --input-dir ./data/wdofut_prepared --output-json ./data/wdofut_prepared/step1_audit_report.json
./.venv/bin/python3 scripts/parquet_remount_validate.py --parquet-base ./data/wdofut_prepared --full-json --strict-floats
./.venv/bin/python3 scripts/run_wdofut_step2_label.py --input-dir ./data/wdofut_prepared --output-parquet ./data/wdofut_prepared/wdofut_labels_tb.parquet --output-summary ./data/wdofut_prepared/wdofut_labels_tb_summary.json
./.venv/bin/python3 scripts/run_wdofut_step3_baselines.py --input-parquet ./data/wdofut_prepared/wdofut_labels_tb.parquet --output-json ./data/wdofut_prepared/wdofut_baselines_metrics.json
./.venv/bin/python3 scripts/run_wdofut_step4_feature_scan.py --input-parquet ./data/wdofut_prepared/wdofut_labels_tb.parquet --output-features-parquet ./data/wdofut_prepared/wdofut_features_v1.parquet --output-json ./data/wdofut_prepared/wdofut_feature_scan.json
./.venv/bin/python3 scripts/run_wdofut_step5_hypotheses.py --input-parquet ./data/wdofut_prepared/wdofut_features_v1.parquet --output-root ./experiments
./.venv/bin/python3 scripts/run_wdofut_step6_backtest.py --input-features ./data/wdofut_prepared/wdofut_features_v1.parquet --output-root ./experiments
./.venv/bin/python3 scripts/run_wdofut_step7_robustness.py --input-features ./data/wdofut_prepared/wdofut_features_v1.parquet --output-root ./experiments
./.venv/bin/python3 scripts/run_wdofut_step8_verdict.py --baselines-json ./data/wdofut_prepared/wdofut_baselines_metrics.json --output-root ./experiments
```

That is the canonical recovery path.

## 7) Known pitfalls (real incidents)

1. `--combined_parquet` fails  
Use `--combined-parquet` (hyphen, not underscore).

2. Label rows unexpectedly increase  
Cause: reading generated parquet artifacts from same folder.  
Current fix: `run_wdofut_step2_label.py` reads only `day=*/*.parquet`.

3. Agent sees empty directory with internal executor  
Check mounted path and `workdir` handling with:

```bash
curl -sS -X POST http://localhost:8123/execute \
  -H 'Content-Type: application/json' \
  -d '{"code":"import os; print(os.getcwd()); print(os.listdir()[:5])","workdir":"/app/data/wdofut_prepared"}'
```

4. API spend spikes with no progress  
Keep deterministic compute in scripts and set:

```env
OPENAI_LOG=error
```
