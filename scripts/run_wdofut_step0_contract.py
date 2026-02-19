#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_TOP = {
    "dataset",
    "label",
    "execution",
    "costs",
    "validation",
    "metrics",
    "kill_switch",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Step 0: validate and resolve research contract."
    )
    parser.add_argument(
        "--contract",
        default="./docs/research_contract_wdofut.json",
        help="Contract JSON path.",
    )
    parser.add_argument(
        "--output-json",
        default="./data/wdofut_prepared/step0_contract_resolved.json",
        help="Output resolved contract JSON path.",
    )
    return parser.parse_args()


def require_path(d: dict[str, Any], path: str) -> bool:
    cur: Any = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return True


def main() -> int:
    args = parse_args()
    in_path = Path(args.contract).expanduser().resolve()
    if not in_path.exists():
        raise SystemExit(f"Contract file not found: {in_path}")

    contract = json.loads(in_path.read_text(encoding="utf-8"))
    if not isinstance(contract, dict):
        raise SystemExit("Contract JSON must be an object.")

    missing_top = sorted(REQUIRED_TOP - set(contract.keys()))
    required_paths = [
        "dataset.ticker",
        "dataset.period_start",
        "dataset.period_end",
        "label.horizon",
        "label.target_type",
        "label.price_col",
        "validation.train_ratio",
        "validation.val_ratio",
        "validation.test_ratio",
        "label_params.up_barrier",
        "label_params.down_barrier",
    ]
    missing_paths = [p for p in required_paths if not require_path(contract, p)]

    ratios = contract.get("validation", {})
    tr = float(ratios.get("train_ratio", 0.0))
    vr = float(ratios.get("val_ratio", 0.0))
    ter = float(ratios.get("test_ratio", 0.0))
    ratio_sum = tr + vr + ter

    status = "ok"
    issues: list[str] = []
    if missing_top:
        status = "error"
        issues.append(f"missing_top_keys={missing_top}")
    if missing_paths:
        status = "error"
        issues.append(f"missing_paths={missing_paths}")
    if abs(ratio_sum - 1.0) > 1e-6:
        status = "error"
        issues.append(f"validation ratios must sum to 1.0, got {ratio_sum}")

    resolved = {
        "status": status,
        "issues": issues,
        "contract_path": str(in_path),
        "contract": contract,
    }

    out_path = Path(args.output_json).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(resolved, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(resolved, ensure_ascii=False, indent=2))

    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
