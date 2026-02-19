#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Step 8: produce GO/NO-GO verdict from Step 3/6/7 artifacts."
    )
    parser.add_argument(
        "--baselines-json",
        default="./data/wdofut_prepared/wdofut_baselines_metrics.json",
        help="Step 3 baseline metrics JSON.",
    )
    parser.add_argument(
        "--step6-metrics-json",
        default="",
        help="Step 6 metrics.json path (if empty, auto-detect latest).",
    )
    parser.add_argument(
        "--step7-robustness-json",
        default="",
        help="Step 7 robustness.json path (if empty, auto-detect latest).",
    )
    parser.add_argument(
        "--step7-placebo-json",
        default="",
        help="Step 7 placebo.json path (if empty, auto-detect latest).",
    )
    parser.add_argument(
        "--output-root",
        default="./experiments",
        help="Base experiments folder.",
    )
    parser.add_argument("--candidate-id", default="H05", help="Candidate hypothesis id to evaluate (default: H05).")
    parser.add_argument("--min-test-profit-factor", type=float, default=1.0, help="Minimum test profit factor gate.")
    parser.add_argument(
        "--min-sensitivity-positive-ratio",
        type=float,
        default=0.6,
        help="Minimum positive-ratio across sensitivity test net_pnl.",
    )
    parser.add_argument(
        "--require-placebo-outperform-shuffle",
        action="store_true",
        help="If set, require base placebo net_pnl > shuffled-label placebo net_pnl.",
    )
    parser.add_argument(
        "--require-inversion-nonequivalent",
        action="store_true",
        help="If set, require base placebo net_pnl > abs(inverted-signal placebo net_pnl).",
    )
    return parser.parse_args()


def latest(pattern: str) -> Path:
    matches = sorted(Path(".").glob(pattern))
    if not matches:
        raise SystemExit(f"No files matched pattern: {pattern}")
    return matches[-1].resolve()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"File not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    args = parse_args()
    baselines_path = Path(args.baselines_json).expanduser().resolve()

    step6_path = (
        Path(args.step6_metrics_json).expanduser().resolve()
        if args.step6_metrics_json
        else latest("experiments/*_step6_backtest/metrics.json")
    )
    rob_path = (
        Path(args.step7_robustness_json).expanduser().resolve()
        if args.step7_robustness_json
        else latest("experiments/*_step7_robustness/robustness.json")
    )
    plc_path = (
        Path(args.step7_placebo_json).expanduser().resolve()
        if args.step7_placebo_json
        else latest("experiments/*_step7_robustness/placebo.json")
    )

    b = load_json(baselines_path)
    s6 = load_json(step6_path)
    r7 = load_json(rob_path)
    p7 = load_json(plc_path)

    # Baseline gate (OOS): must beat no_trade net_pnl=0
    no_trade_oos = b["baselines"]["no_trade"]["oos_val_test"]["net_pnl"]
    candidate_id = args.candidate_id
    if candidate_id not in s6["metrics"]:
        raise SystemExit(f"Candidate id '{candidate_id}' not present in step6 metrics.")
    cand_val = s6["metrics"][candidate_id]["val"]["net_pnl"]
    cand_test = s6["metrics"][candidate_id]["test"]["net_pnl"]
    cand_test_pf = s6["metrics"][candidate_id]["test"]["profit_factor"]
    cand_beats_baseline = (cand_val + cand_test) > no_trade_oos

    # Robustness gates
    base_test = p7["base_test_metrics"]["net_pnl"]
    shuffle_test = p7["label_shuffle_test_metrics"]["net_pnl"]
    invert_test = p7["signal_inversion_test_metrics"]["net_pnl"]
    placebo_ok = (base_test > shuffle_test) if args.require_placebo_outperform_shuffle else True
    inversion_ok = (base_test > abs(invert_test)) if args.require_inversion_nonequivalent else True

    # Sensitivity gate: avoid fragile strategies
    grid = r7["sensitivity_grid"]
    test_net_values = [g["metrics"]["test"]["net_pnl"] for g in grid]
    robust_positive_ratio = sum(1 for x in test_net_values if x > 0) / len(test_net_values) if test_net_values else 0.0
    sensitivity_ok = robust_positive_ratio >= args.min_sensitivity_positive_ratio

    rules = {
        "beats_baseline_oos": cand_beats_baseline,
        f"test_profit_factor_ge_{args.min_test_profit_factor}": cand_test_pf >= args.min_test_profit_factor,
        "placebo_outperforms_randomized_label": placebo_ok,
        "inversion_not_equivalent": inversion_ok,
        f"sensitivity_positive_ratio_ge_{args.min_sensitivity_positive_ratio}": sensitivity_ok,
    }
    decision = "GO" if all(rules.values()) else "NO-GO"

    summary = {
        "decision": decision,
        "candidate": candidate_id,
        "inputs": {
            "baselines_json": str(baselines_path),
            "step6_metrics_json": str(step6_path),
            "step7_robustness_json": str(rob_path),
            "step7_placebo_json": str(plc_path),
        },
        "evidence": {
            "baseline_oos_net_pnl_no_trade": no_trade_oos,
            "candidate_val_net_pnl": cand_val,
            "candidate_test_net_pnl": cand_test,
            "candidate_test_profit_factor": cand_test_pf,
            "placebo_base_test_net_pnl": base_test,
            "placebo_shuffle_test_net_pnl": shuffle_test,
            "placebo_invert_test_net_pnl": invert_test,
            "sensitivity_test_positive_ratio": robust_positive_ratio,
        },
        "thresholds": {
            "min_test_profit_factor": args.min_test_profit_factor,
            "min_sensitivity_positive_ratio": args.min_sensitivity_positive_ratio,
            "require_placebo_outperform_shuffle": bool(args.require_placebo_outperform_shuffle),
            "require_inversion_nonequivalent": bool(args.require_inversion_nonequivalent),
        },
        "rules": rules,
    }

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.output_root).expanduser().resolve() / f"{ts}_step8_verdict"
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_path = out_dir / "summary.json"
    verdict_path = out_dir / "verdict.md"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Verdict",
        "",
        f"- Experiment: `{ts}_step8_verdict`",
        f"- Candidate: `{candidate_id}`",
        f"- Decision: **{decision}**",
        "",
        "## Why",
        f"- OOS baseline comparison: {candidate_id} (val+test) = `{cand_val + cand_test:.4f}` vs no-trade = `{no_trade_oos:.4f}`",
        f"- Test performance: net_pnl = `{cand_test:.4f}`, profit_factor = `{cand_test_pf:.4f}`",
        f"- Placebo check: base = `{base_test:.4f}`, shuffled-label = `{shuffle_test:.4f}`, inverted-signal = `{invert_test:.4f}`",
        f"- Sensitivity positive ratio (test): `{robust_positive_ratio:.2%}`",
        "",
        "## Rule Checks",
    ]
    for k, v in rules.items():
        md.append(f"- {k}: `{v}`")
    md.extend(["", "## Next Action", "- If NO-GO: redesign hypotheses and repeat Step 5 with stricter regime logic."])
    verdict_path.write_text("\n".join(md), encoding="utf-8")

    print(
        json.dumps(
            {
                "experiment_dir": str(out_dir),
                "summary_json": str(summary_path),
                "verdict_md": str(verdict_path),
                "decision": decision,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
