# System Usage Map (Who Uses What)

This is the canonical map of responsibilities in this repo.

## 1) What each layer is for

### `scripts/*` (deterministic data pipeline)
Use scripts for heavy, repeatable, non-interactive steps:
- data extraction/preparation
- parquet validation
- label construction
- baseline metrics generation

These steps should not depend on LLM calls.

Main scripts:
- `scripts/run_wdofut_step0_contract.py`
- `scripts/run_wdofut_step1_audit.py`
- `scripts/prepare_wdofut.py`
- `scripts/parquet_remount_validate.py`
- `scripts/load_prepared_to_df.py`
- `scripts/run_wdofut_step2_label.py`
- `scripts/run_wdofut_step3_baselines.py`
- `scripts/run_wdofut_step4_feature_scan.py`
- `scripts/run_wdofut_step5_hypotheses.py`
- `scripts/run_wdofut_step6_backtest.py`
- `scripts/run_wdofut_step7_robustness.py`
- `scripts/run_wdofut_step8_verdict.py`
- `scripts/run_wdofut_orchestrator.py`

### `open-data-scientist` CLI (agent orchestration)
Use the agent for:
- exploratory analysis
- hypothesis generation
- interpretation of outputs
- report writing

Do not use the agent as the primary engine for heavy batch ETL/label computation.

### `interpreter/*` (execution runtime)
Local Python execution backend for agent actions.
- runs as Docker service
- for `--executor internal`
- executes code against mounted data path (`/app/data/...`) or uploaded files (`/app/custom_data`)

### LLM provider (`openai`/`together`)
Reasoning/narrative layer only.
It receives prompts and execution summaries, not your full raw parquet payload.

## 2) Standard operating flow (recommended)

1. Prepare dataset (script)
2. Validate contract + dataset audit (script)
3. Validate dataset structure (script)
4. Build labels/features/baselines (script)
5. Run Step 5->8 pipeline (script)
6. Run agent on prepared artifacts for interpretation/report

This minimizes API waste and maximizes reproducibility.

## 3) Decision table: where to run each task

- Task: unzip/extract/process parquet partitions  
  Tool: `scripts/*`

- Task: schema/null/dup checks  
  Tool: `scripts/parquet_remount_validate.py`

- Task: contract validation and required fields checks  
  Tool: `scripts/run_wdofut_step0_contract.py`

- Task: deterministic dataset audit summary  
  Tool: `scripts/run_wdofut_step1_audit.py`

- Task: define/build `y` labels with strict alignment  
  Tool: `scripts/run_wdofut_step2_label.py`

- Task: temporal OOS baselines  
  Tool: `scripts/run_wdofut_step3_baselines.py`

- Task: causal feature scan and ranking  
  Tool: `scripts/run_wdofut_step4_feature_scan.py`

- Task: Step 5->8 hypothesis/backtest/robustness/verdict  
  Tool: `scripts/run_wdofut_step5_hypotheses.py`, `scripts/run_wdofut_step6_backtest.py`, `scripts/run_wdofut_step7_robustness.py`, `scripts/run_wdofut_step8_verdict.py`

- Task: bounded multi-cycle search  
  Tool: `scripts/run_wdofut_orchestrator.py`

- Task: investigate candidate edges from prepared outputs  
  Tool: `open-data-scientist` agent

- Task: generate natural-language summary/report  
  Tool: `open-data-scientist` agent

## 4) Minimal commands (working path)

### 4.1 Environment

```bash
cd /home/trevisan/repositories/open-data-scientist
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 4.2 Start interpreter (internal executor)

```bash
docker compose -f interpreter/docker-compose.yml up -d --build
curl -s http://localhost:8123/health
```

Expected health response:

```json
{"status":"healthy"}
```

### 4.3 Data pipeline (prepare -> validate -> label)

```bash
# A) prepare
./.venv/bin/python3 scripts/run_wdofut_step0_contract.py \
  --contract ./docs/research_contract_wdofut.json \
  --output-json ./data/wdofut_prepared/step0_contract_resolved.json

./.venv/bin/python3 scripts/run_wdofut_step1_audit.py \
  --input-dir ./data/wdofut_prepared \
  --output-json ./data/wdofut_prepared/step1_audit_report.json

./.venv/bin/python3 scripts/prepare_wdofut.py \
  --input ./data/raw/ticker=WDOFUT_F_0 \
  --output-dir ./data/wdofut_prepared

# B) validate
./.venv/bin/python3 scripts/parquet_remount_validate.py \
  --parquet-base ./data/wdofut_prepared \
  --full-json --strict-floats

# C) label (etapa 2 do protocolo)
./.venv/bin/python3 scripts/run_wdofut_step2_label.py \
  --input-dir ./data/wdofut_prepared \
  --h-minutes 5 \
  --price-col mid \
  --up-barrier 0.00035 \
  --down-barrier 0.00035 \
  --output-parquet ./data/wdofut_prepared/wdofut_labels_tb.parquet \
  --output-summary ./data/wdofut_prepared/wdofut_labels_tb_summary.json
```

### 4.4 Step 3 to Step 8 pipeline

```bash
# Step 3 baselines
./.venv/bin/python3 scripts/run_wdofut_step3_baselines.py \
  --input-parquet ./data/wdofut_prepared/wdofut_labels_tb.parquet \
  --output-json ./data/wdofut_prepared/wdofut_baselines_metrics.json

# Step 4 feature scan
./.venv/bin/python3 scripts/run_wdofut_step4_feature_scan.py \
  --input-parquet ./data/wdofut_prepared/wdofut_labels_tb.parquet \
  --output-features-parquet ./data/wdofut_prepared/wdofut_features_v1.parquet \
  --output-json ./data/wdofut_prepared/wdofut_feature_scan.json

# Step 5 hypotheses
./.venv/bin/python3 scripts/run_wdofut_step5_hypotheses.py \
  --input-parquet ./data/wdofut_prepared/wdofut_features_v1.parquet \
  --output-root ./experiments

# Step 6 backtest
./.venv/bin/python3 scripts/run_wdofut_step6_backtest.py \
  --input-features ./data/wdofut_prepared/wdofut_features_v1.parquet \
  --output-root ./experiments

# Step 7 robustness
./.venv/bin/python3 scripts/run_wdofut_step7_robustness.py \
  --input-features ./data/wdofut_prepared/wdofut_features_v1.parquet \
  --output-root ./experiments

# Step 8 verdict
./.venv/bin/python3 scripts/run_wdofut_step8_verdict.py \
  --baselines-json ./data/wdofut_prepared/wdofut_baselines_metrics.json \
  --output-root ./experiments
```

### 4.5 Orchestrator (bounded search + auto-derivation)

```bash
./.venv/bin/python3 scripts/run_wdofut_orchestrator.py \
  --features-parquet ./data/wdofut_prepared/wdofut_features_v1.parquet \
  --baselines-json ./data/wdofut_prepared/wdofut_baselines_metrics.json \
  --cost-grid 0.0 0.01 0.02 \
  --max-runs 3 \
  --output-root ./experiments
```

Auto-derivation across grids:

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

Full run-scoped derivation (`Step 2 -> 8` per run):

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

Artifacts are grouped per experiment id and run:
- `experiments/<orchestrator_id>/orchestrator_results.json`
- `experiments/<orchestrator_id>/run_XX/data/*`
- `experiments/<orchestrator_id>/run_XX/<timestamp>_step5_hypotheses/*`
- `experiments/<orchestrator_id>/run_XX/<timestamp>_step6_backtest/*`
- `experiments/<orchestrator_id>/run_XX/<timestamp>_step7_robustness/*`
- `experiments/<orchestrator_id>/run_XX/<timestamp>_step8_verdict/*`

### 4.6 Optional combined cache

```bash
./.venv/bin/python3 scripts/load_prepared_to_df.py \
  --input-dir ./data/wdofut_prepared \
  --combined-parquet ./data/wdofut_prepared/wdofut_combined.parquet
```

### 4.7 Run agent (interpretation/report)

```bash
open-data-scientist \
  --provider openai \
  --executor internal \
  --model gpt-5-mini \
  --data-dir ./data/wdofut_prepared \
  --iterations 3
```

### 4.8 Stop interpreter

```bash
docker compose -f interpreter/docker-compose.yml down
```

## 5) Anti-confusion rules

- If a step must be reproducible and numeric, implement in script.
- If a step must be explanatory and iterative, use the agent.
- Never block progress waiting for agent to perform bulk ETL.
