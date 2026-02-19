#!/usr/bin/env python3
from __future__ import annotations

import argparse
import itertools
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Orchestrate constrained Step 5->8 search cycles."
    )
    parser.add_argument(
        "--features-parquet",
        default="./data/wdofut_prepared/wdofut_features_v1.parquet",
        help="Input features parquet for Step 5/6/7 when not deriving labels/features in-run.",
    )
    parser.add_argument(
        "--baselines-json",
        default="./data/wdofut_prepared/wdofut_baselines_metrics.json",
        help="Step 3 baselines metrics JSON when not deriving labels/features in-run.",
    )
    parser.add_argument(
        "--derive-labels",
        action="store_true",
        help="Run Step 2->4 inside each run_scope to derive labels/features from raw prepared data.",
    )
    parser.add_argument(
        "--label-input-parquet",
        default="./data/wdofut_prepared/wdofut_combined.parquet",
        help="Step 2 input parquet path (used if exists).",
    )
    parser.add_argument(
        "--label-input-dir",
        default="./data/wdofut_prepared",
        help="Step 2 input dir fallback.",
    )
    parser.add_argument(
        "--output-root",
        default="./experiments",
        help="Base experiments folder.",
    )
    parser.add_argument(
        "--cost-grid",
        nargs="*",
        type=float,
        default=[0.0, 0.01, 0.02],
        help="Cost per trade grid used across cycles.",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=3,
        help="Maximum search runs (bounded).",
    )
    parser.add_argument(
        "--auto-derive",
        action="store_true",
        help="Enable automatic hypothesis parameter derivation over threshold grids.",
    )
    parser.add_argument("--z-upper-grid", nargs="*", type=float, default=[0.95], help="Grid for zret upper quantile.")
    parser.add_argument("--z-lower-grid", nargs="*", type=float, default=[0.05], help="Grid for zret lower quantile.")
    parser.add_argument("--spread-upper-grid", nargs="*", type=float, default=[0.95], help="Grid for spread upper quantile.")
    parser.add_argument("--spread-lower-grid", nargs="*", type=float, default=[0.05], help="Grid for spread lower quantile.")
    parser.add_argument("--vol-upper-grid", nargs="*", type=float, default=[0.85], help="Grid for vol regime upper quantile.")
    parser.add_argument("--vol-lower-grid", nargs="*", type=float, default=[0.15], help="Grid for vol regime lower quantile.")
    parser.add_argument("--top-k-grid", nargs="*", type=int, default=[3], help="Grid for Step 5 top-k.")
    parser.add_argument("--num-windows-grid", nargs="*", type=int, default=[6], help="Grid for Step 6 num windows.")
    parser.add_argument("--h-minutes-grid", nargs="*", type=float, default=[5.0], help="Grid for Step 2 label horizon minutes.")
    parser.add_argument("--up-barrier-grid", nargs="*", type=float, default=[0.00035], help="Grid for Step 2 up barrier.")
    parser.add_argument("--down-barrier-grid", nargs="*", type=float, default=[0.00035], help="Grid for Step 2 down barrier.")
    parser.add_argument("--price-col-grid", nargs="*", default=["mid"], help="Grid for Step 2 price column.")
    parser.add_argument("--min-test-profit-factor-grid", nargs="*", type=float, default=[1.0], help="Grid for Step 8 min test PF.")
    parser.add_argument("--min-sensitivity-positive-ratio-grid", nargs="*", type=float, default=[0.6], help="Grid for Step 8 min sensitivity positive ratio.")
    parser.add_argument("--require-placebo-outperform-shuffle", action="store_true", help="Enable strict placebo gate in Step 8.")
    parser.add_argument("--require-inversion-nonequivalent", action="store_true", help="Enable strict inversion gate in Step 8.")
    return parser.parse_args()


def run_cmd(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        raise RuntimeError(f"Command failed ({proc.returncode}): {' '.join(cmd)}\nSTDOUT:\n{out}\nSTDERR:\n{err}")
    # Step scripts print JSON payload; parse last JSON object.
    try:
        return json.loads(out.splitlines()[-1] if "\n" not in out else out[out.rfind("{"):])
    except Exception:
        try:
            return json.loads(out)
        except Exception:
            return {"raw_stdout": out, "raw_stderr": err}


def latest(path_glob: str) -> Path:
    files = sorted(Path(".").glob(path_glob))
    if not files:
        raise FileNotFoundError(f"No files matching: {path_glob}")
    return files[-1].resolve()


def main() -> int:
    args = parse_args()
    features = Path(args.features_parquet).expanduser().resolve()
    baselines = Path(args.baselines_json).expanduser().resolve()
    out_root = Path(args.output_root).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    if not args.derive_labels:
        if not features.exists():
            raise SystemExit(f"Missing features parquet: {features}")
        if not baselines.exists():
            raise SystemExit(f"Missing baselines metrics: {baselines}")

    py = sys.executable
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    run_dir = out_root / f"{ts}_orchestrator"
    run_dir.mkdir(parents=True, exist_ok=True)

    results: list[dict[str, Any]] = []
    run_id = 0

    if args.auto_derive:
        param_space = list(
            itertools.product(
                args.cost_grid,
                args.z_upper_grid,
                args.z_lower_grid,
                args.spread_upper_grid,
                args.spread_lower_grid,
                args.vol_upper_grid,
                args.vol_lower_grid,
                args.top_k_grid,
                args.num_windows_grid,
                args.h_minutes_grid,
                args.up_barrier_grid,
                args.down_barrier_grid,
                args.price_col_grid,
                args.min_test_profit_factor_grid,
                args.min_sensitivity_positive_ratio_grid,
            )
        )
    else:
        param_space = [
            (
                c,
                args.z_upper_grid[0],
                args.z_lower_grid[0],
                args.spread_upper_grid[0],
                args.spread_lower_grid[0],
                args.vol_upper_grid[0],
                args.vol_lower_grid[0],
                args.top_k_grid[0],
                args.num_windows_grid[0],
                args.h_minutes_grid[0],
                args.up_barrier_grid[0],
                args.down_barrier_grid[0],
                args.price_col_grid[0],
                args.min_test_profit_factor_grid[0],
                args.min_sensitivity_positive_ratio_grid[0],
            )
            for c in args.cost_grid
        ]

    for (
        cost,
        z_upper_q,
        z_lower_q,
        spread_upper_q,
        spread_lower_q,
        vol_upper_q,
        vol_lower_q,
        top_k,
        num_windows,
        h_minutes,
        up_barrier,
        down_barrier,
        price_col,
        min_test_pf,
        min_sens_pos_ratio,
    ) in param_space:
        if run_id >= args.max_runs:
            break
        run_id += 1
        run_scope = run_dir / f"run_{run_id:02d}"
        run_scope.mkdir(parents=True, exist_ok=True)
        run_data = run_scope / "data"
        run_data.mkdir(parents=True, exist_ok=True)

        features_path = features
        baselines_path = baselines
        if args.derive_labels:
            labels_parquet = run_data / "wdofut_labels_tb.parquet"
            labels_summary = run_data / "wdofut_labels_tb_summary.json"
            baselines_path = run_data / "wdofut_baselines_metrics.json"
            features_path = run_data / "wdofut_features_v1.parquet"
            feature_scan_json = run_data / "wdofut_feature_scan.json"

            run_cmd(
                [
                    py,
                    "scripts/run_wdofut_step2_label.py",
                    "--input-parquet",
                    str(Path(args.label_input_parquet).expanduser().resolve()),
                    "--input-dir",
                    str(Path(args.label_input_dir).expanduser().resolve()),
                    "--h-minutes",
                    str(h_minutes),
                    "--price-col",
                    str(price_col),
                    "--up-barrier",
                    str(up_barrier),
                    "--down-barrier",
                    str(down_barrier),
                    "--output-parquet",
                    str(labels_parquet),
                    "--output-summary",
                    str(labels_summary),
                ]
            )
            run_cmd(
                [
                    py,
                    "scripts/run_wdofut_step3_baselines.py",
                    "--input-parquet",
                    str(labels_parquet),
                    "--cost-per-trade",
                    str(cost),
                    "--output-json",
                    str(baselines_path),
                ]
            )
            run_cmd(
                [
                    py,
                    "scripts/run_wdofut_step4_feature_scan.py",
                    "--input-parquet",
                    str(labels_parquet),
                    "--output-features-parquet",
                    str(features_path),
                    "--output-json",
                    str(feature_scan_json),
                ]
            )

        step5 = run_cmd(
            [
                py,
                "scripts/run_wdofut_step5_hypotheses.py",
                "--input-parquet",
                str(features_path),
                "--cost-per-trade",
                str(cost),
                "--top-k",
                str(top_k),
                "--z-upper-quantile",
                str(z_upper_q),
                "--z-lower-quantile",
                str(z_lower_q),
                "--spread-upper-quantile",
                str(spread_upper_q),
                "--spread-lower-quantile",
                str(spread_lower_q),
                "--vol-regime-upper-quantile",
                str(vol_upper_q),
                "--vol-regime-lower-quantile",
                str(vol_lower_q),
                "--output-root",
                str(run_scope),
            ]
        )
        cand_path = step5["top_candidates_json"]

        step6 = run_cmd(
            [
                py,
                "scripts/run_wdofut_step6_backtest.py",
                "--input-features",
                str(features_path),
                "--input-candidates",
                str(cand_path),
                "--cost-per-trade",
                str(cost),
                "--num-windows",
                str(num_windows),
                "--z-upper-quantile",
                str(z_upper_q),
                "--z-lower-quantile",
                str(z_lower_q),
                "--spread-upper-quantile",
                str(spread_upper_q),
                "--spread-lower-quantile",
                str(spread_lower_q),
                "--vol-regime-upper-quantile",
                str(vol_upper_q),
                "--vol-regime-lower-quantile",
                str(vol_lower_q),
                "--output-root",
                str(run_scope),
            ]
        )

        step7 = run_cmd(
            [
                py,
                "scripts/run_wdofut_step7_robustness.py",
                "--input-features",
                str(features_path),
                "--h05-spread-quantile",
                str(spread_upper_q),
                "--output-root",
                str(run_scope),
            ]
        )

        candidate_id = (
            (step5.get("top_candidates") or [{}])[0].get("id")
            if isinstance(step5.get("top_candidates"), list)
            else "H05"
        ) or "H05"

        step8_cmd = [
            py,
            "scripts/run_wdofut_step8_verdict.py",
            "--baselines-json",
            str(baselines_path),
            "--step6-metrics-json",
            str(step6["metrics_json"]),
            "--step7-robustness-json",
            str(step7["robustness_json"]),
            "--step7-placebo-json",
            str(step7["placebo_json"]),
            "--candidate-id",
            str(candidate_id),
            "--min-test-profit-factor",
            str(min_test_pf),
            "--min-sensitivity-positive-ratio",
            str(min_sens_pos_ratio),
        ]
        if args.require_placebo_outperform_shuffle:
            step8_cmd.append("--require-placebo-outperform-shuffle")
        if args.require_inversion_nonequivalent:
            step8_cmd.append("--require-inversion-nonequivalent")
        step8_cmd.extend(["--output-root", str(run_scope)])
        step8 = run_cmd(step8_cmd)

        summary = json.loads(Path(step8["summary_json"]).read_text(encoding="utf-8"))
        results.append(
            {
                "run_id": run_id,
                "cost_per_trade": cost,
                "thresholds": {
                    "z_upper_quantile": z_upper_q,
                    "z_lower_quantile": z_lower_q,
                    "spread_upper_quantile": spread_upper_q,
                    "spread_lower_quantile": spread_lower_q,
                    "vol_regime_upper_quantile": vol_upper_q,
                    "vol_regime_lower_quantile": vol_lower_q,
                },
                "label_params": {
                    "h_minutes": h_minutes,
                    "price_col": price_col,
                    "up_barrier": up_barrier,
                    "down_barrier": down_barrier,
                },
                "search_params": {
                    "top_k": top_k,
                    "num_windows": num_windows,
                    "candidate_id": candidate_id,
                    "min_test_profit_factor": min_test_pf,
                    "min_sensitivity_positive_ratio": min_sens_pos_ratio,
                    "require_placebo_outperform_shuffle": bool(args.require_placebo_outperform_shuffle),
                    "require_inversion_nonequivalent": bool(args.require_inversion_nonequivalent),
                    "derive_labels": bool(args.derive_labels),
                },
                "decision": step8["decision"],
                "step5_dir": step5["experiment_dir"],
                "step6_dir": step6["experiment_dir"],
                "step7_dir": step7["experiment_dir"],
                "step8_dir": step8["experiment_dir"],
                "run_scope": str(run_scope),
                "candidate": summary.get("candidate"),
                "evidence": summary.get("evidence", {}),
                "rules": summary.get("rules", {}),
            }
        )

    leaderboard = sorted(
        results,
        key=lambda r: (
            1 if r["decision"] == "GO" else 0,
            float(r["evidence"].get("h05_test_net_pnl", 0.0)),
        ),
        reverse=True,
    )

    output = {
        "created_at_utc": ts,
        "runs_executed": len(results),
        "search_space": {
            "auto_derive": bool(args.auto_derive),
            "derive_labels": bool(args.derive_labels),
            "cost_grid": args.cost_grid,
            "z_upper_grid": args.z_upper_grid,
            "z_lower_grid": args.z_lower_grid,
            "spread_upper_grid": args.spread_upper_grid,
            "spread_lower_grid": args.spread_lower_grid,
            "vol_upper_grid": args.vol_upper_grid,
            "vol_lower_grid": args.vol_lower_grid,
            "top_k_grid": args.top_k_grid,
            "num_windows_grid": args.num_windows_grid,
            "h_minutes_grid": args.h_minutes_grid,
            "up_barrier_grid": args.up_barrier_grid,
            "down_barrier_grid": args.down_barrier_grid,
            "price_col_grid": args.price_col_grid,
            "min_test_profit_factor_grid": args.min_test_profit_factor_grid,
            "min_sensitivity_positive_ratio_grid": args.min_sensitivity_positive_ratio_grid,
            "require_placebo_outperform_shuffle": bool(args.require_placebo_outperform_shuffle),
            "require_inversion_nonequivalent": bool(args.require_inversion_nonequivalent),
        },
        "leaderboard": leaderboard,
        "best_valid": next((r for r in leaderboard if r["decision"] == "GO"), None),
    }

    out_json = run_dir / "orchestrator_results.json"
    out_json.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"run_dir": str(run_dir), "results_json": str(out_json), "runs_executed": len(results)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
