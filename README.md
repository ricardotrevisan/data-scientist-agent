# Open Data Scientist

Scientific Strategy Research Platform for WDOFUT (Mini Dollar) and other market snapshot datasets.

This project combines:
- reproducible data engineering
- causal label construction
- protocol-driven out-of-sample validation
- AI-assisted strategy research and reporting

The goal is not generic chat analysis. The goal is auditable edge discovery.

## Positioning

Open Data Scientist is built for trading research teams that want:
- a deterministic pipeline for market microstructure data
- strict anti-leakage workflow
- clear separation between heavy compute and LLM reasoning
- lower API waste by moving batch computation into scripts

## Core Product Capabilities

1. **Research-grade data pipeline**
- Raw archives/parquet to partitioned prepared dataset
- Feature derivation (`mid`, `spread`, `log_return`)
- Structural and semantic validation gates

2. **Causal target engineering**
- Triple-barrier/event-style labels with strict future-window alignment
- Reproducible summary artifacts for protocol checkpoints

3. **Agentic analysis layer**
- ReAct CLI for hypothesis generation, diagnostics, and report drafting
- OpenAI-first provider support, Together optional
- Internal Docker executor for local, inspectable code execution

4. **Scientific workflow enforcement**
- Protocol-first process in `docs/research_protocol.md`
- Contract-first setup in `docs/research_contract_wdofut.json`
- End-to-end operational runbook in `RUNBOOK.md`

## First Read (Start Here)

- Primary runbook: `RUNBOOK.md`
- Responsibilities map: `docs/system_usage_map.md`
- Research protocol: `docs/research_protocol.md`
- End-to-end walkthrough: `docs/wdofut_parquet_walkthrough.md`
- Statistical progress snapshot: `docs/progress_statistical_snapshot.md`

## Architecture (Practical)

1. **Deterministic layer (`scripts/*`)**
- Use for ETL, validation, labels, baseline metrics.
- No LLM dependency required.

2. **Execution layer (`interpreter/*`)**
- Local Python runtime behind HTTP (`http://localhost:8123`).
- Used by `--executor internal`.
- Supports mounted data path execution.

3. **Reasoning layer (`open_data_scientist/*`)**
- ReAct orchestration and LLM calls.
- Best used for interpretation and strategy narrative after artifacts exist.

## Quickstart

### 1) Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### 2) Configure `.env`

```env
OPENAI_API_KEY=your_openai_key
ODS_MODEL=gpt-5-mini
OPENAI_LOG=error
```

### 3) Start internal executor

```bash
docker compose -f interpreter/docker-compose.yml up -d --build
curl -s http://localhost:8123/health
```

### 4) Prepare -> validate -> label

```bash
./.venv/bin/python3 scripts/run_wdofut_step0_contract.py \
  --contract ./docs/research_contract_wdofut.json \
  --output-json ./data/wdofut_prepared/step0_contract_resolved.json

./.venv/bin/python3 scripts/run_wdofut_step1_audit.py \
  --input-dir ./data/wdofut_prepared \
  --output-json ./data/wdofut_prepared/step1_audit_report.json

./.venv/bin/python3 scripts/prepare_wdofut.py \
  --input ./data/raw/ticker=WDOFUT_F_0 \
  --output-dir ./data/wdofut_prepared

./.venv/bin/python3 scripts/parquet_remount_validate.py \
  --parquet-base ./data/wdofut_prepared \
  --full-json \
  --strict-floats

./.venv/bin/python3 scripts/run_wdofut_step2_label.py \
  --input-dir ./data/wdofut_prepared \
  --h-minutes 5 \
  --price-col mid \
  --up-barrier 0.00035 \
  --down-barrier 0.00035 \
  --output-parquet ./data/wdofut_prepared/wdofut_labels_tb.parquet \
  --output-summary ./data/wdofut_prepared/wdofut_labels_tb_summary.json
```

### 5) Execute Steps 3–8 (scripted scientific pipeline)

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

### 6) Orchestrator (bounded multi-cycle, now with auto-derivation)

```bash
./.venv/bin/python3 scripts/run_wdofut_orchestrator.py \
  --features-parquet ./data/wdofut_prepared/wdofut_features_v1.parquet \
  --baselines-json ./data/wdofut_prepared/wdofut_baselines_metrics.json \
  --cost-grid 0.0 0.01 0.02 \
  --max-runs 3 \
  --output-root ./experiments
```

Auto-derivation over parameter grids:

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

Full in-run derivation (Step 2 -> 8 per run):

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

Artifacts are grouped under:
- `experiments/<orchestrator_id>/orchestrator_results.json`
- `experiments/<orchestrator_id>/run_XX/data/*`
- `experiments/<orchestrator_id>/run_XX/<timestamp>_step5_hypotheses/*`
- `experiments/<orchestrator_id>/run_XX/<timestamp>_step6_backtest/*`
- `experiments/<orchestrator_id>/run_XX/<timestamp>_step7_robustness/*`
- `experiments/<orchestrator_id>/run_XX/<timestamp>_step8_verdict/*`

### 7) Run the agent for interpretation/report

```bash
open-data-scientist \
  --provider openai \
  --executor internal \
  --model gpt-5-mini \
  --data-dir ./data/wdofut_prepared \
  --iterations 3
```

## Protocol Compliance

The default project direction follows:
- **Step 0:** research contract
- **Step 1:** dataset audit
- **Step 2:** causal label definition and implementation
- **Step 3+:** baselines, walk-forward, robustness, verdict

Reference:
- `docs/research_protocol.md`
- `docs/research_contract_wdofut.json`

## Notable Enhancements Delivered

- OpenAI-first provider abstraction (`open_data_scientist/utils/llm_providers.py`)
- Executor decoupling (`executors_internal.py`, `executors_together.py`, `executors_factory.py`)
- Mounted-data execution path for internal runtime
- Reduced avoidable API retries/fallback noise
- WDOFUT label builder (`scripts/run_wdofut_step2_label.py`)
- Step 0/1 deterministic entrypoint scripts (`run_wdofut_step0_contract.py`, `run_wdofut_step1_audit.py`)
- Full Step 3–8 scripted pipeline and verdict generation
- Bounded orchestrator for repeatable search cycles with automatic parameter derivation
- Single-source operational runbook (`RUNBOOK.md`)

## Optional Together Legacy Path

```bash
pip install -e ".[together]"
open-data-scientist --provider together --executor tci --model deepseek-ai/DeepSeek-V3
```

## Product Direction

This repo is evolving from “general data assistant” into a **scientific trading strategy research system**:
- deterministic by default
- protocol-governed
- reproducible artifacts
- LLM used where it adds leverage, not where it adds noise
