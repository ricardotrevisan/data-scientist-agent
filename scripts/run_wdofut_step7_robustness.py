#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Step 7 robustness for candidate H05 (spread shock short)."
    )
    parser.add_argument(
        "--input-features",
        default="./data/wdofut_prepared/wdofut_features_v1.parquet",
        help="Feature parquet path.",
    )
    parser.add_argument(
        "--output-root",
        default="./experiments",
        help="Base experiments folder.",
    )
    parser.add_argument(
        "--h05-spread-quantile",
        type=float,
        default=0.95,
        help="Primary spread quantile for H05 base signal.",
    )
    return parser.parse_args()


def split_temporal(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    n = len(df)
    i1 = int(0.6 * n)
    i2 = int(0.8 * n)
    return {"train": df.iloc[:i1].copy(), "val": df.iloc[i1:i2].copy(), "test": df.iloc[i2:].copy()}


def evaluate(signal: np.ndarray, y: np.ndarray, cost: float) -> dict[str, Any]:
    traded = signal != 0
    pnl = signal * y - traded.astype(float) * cost
    gp = pnl[pnl > 0].sum()
    gl = -pnl[pnl < 0].sum()
    pf = float(gp / gl) if gl > 0 else (float("inf") if gp > 0 else 0.0)
    return {
        "rows": int(len(y)),
        "trades": int(traded.sum()),
        "net_pnl": float(pnl.sum()),
        "profit_factor": pf,
        "hit_rate": float((pnl[traded] > 0).mean()) if traded.any() else 0.0,
    }


def h05_signal(df: pd.DataFrame, spread_q: float) -> np.ndarray:
    thr = float(df["spread_z_20"].quantile(spread_q))
    return np.where(df["spread_z_20"] >= thr, -1.0, 0.0)


def main() -> int:
    args = parse_args()
    in_path = Path(args.input_features).expanduser().resolve()
    if not in_path.exists():
        raise SystemExit(f"Input features parquet not found: {in_path}")

    df = pd.read_parquet(in_path)
    req = {"timestamp", "y_tb", "spread_z_20"}
    miss = sorted(req - set(df.columns))
    if miss:
        raise SystemExit(f"Missing required columns: {miss}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp", "y_tb", "spread_z_20"]).sort_values("timestamp").reset_index(drop=True)
    splits = split_temporal(df)

    # 1) Sensitivity grid
    spread_q_grid = [0.90, 0.93, 0.95, 0.97, 0.99]
    cost_grid = [0.0, 0.01, 0.02]
    sensitivity: list[dict[str, Any]] = []
    for q in spread_q_grid:
        for c in cost_grid:
            rec: dict[str, Any] = {"spread_quantile": q, "cost_per_trade": c, "metrics": {}}
            for sname, sdf in splits.items():
                sig = h05_signal(sdf, q)
                y = sdf["y_tb"].to_numpy(dtype=float)
                rec["metrics"][sname] = evaluate(sig, y, c)
            sensitivity.append(rec)

    # 2) Stability by day (test split)
    test_df = splits["test"].copy()
    test_df["day"] = test_df["timestamp"].dt.strftime("%Y-%m-%d")
    sig_test = h05_signal(test_df, args.h05_spread_quantile)
    test_df["signal"] = sig_test
    test_df["pnl"] = test_df["signal"] * test_df["y_tb"].astype(float)
    daily = []
    for day, g in test_df.groupby("day", sort=True):
        traded = g["signal"] != 0
        daily.append(
            {
                "day": day,
                "rows": int(len(g)),
                "trades": int(traded.sum()),
                "net_pnl": float(g["pnl"].sum()),
                "hit_rate": float((g.loc[traded, "pnl"] > 0).mean()) if traded.any() else 0.0,
            }
        )

    # 3) Placebo tests on test split
    y_test = test_df["y_tb"].to_numpy(dtype=float)
    base_sig = sig_test
    base = evaluate(base_sig, y_test, 0.0)

    rng = np.random.default_rng(42)
    y_shuf = y_test.copy()
    rng.shuffle(y_shuf)
    placebo_shuffle = evaluate(base_sig, y_shuf, 0.0)
    placebo_invert = evaluate(-base_sig, y_test, 0.0)

    robustness = {
        "candidate_id": "H05",
        "input_features": str(in_path),
        "h05_spread_quantile": args.h05_spread_quantile,
        "sensitivity_grid": sensitivity,
        "daily_test_stability": daily,
        "base_test_metrics": base,
    }
    placebo = {
        "candidate_id": "H05",
        "base_test_metrics": base,
        "label_shuffle_test_metrics": placebo_shuffle,
        "signal_inversion_test_metrics": placebo_invert,
    }

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.output_root).expanduser().resolve() / f"{ts}_step7_robustness"
    out_dir.mkdir(parents=True, exist_ok=True)

    rob_path = out_dir / "robustness.json"
    plc_path = out_dir / "placebo.json"
    rob_path.write_text(json.dumps(robustness, ensure_ascii=False, indent=2), encoding="utf-8")
    plc_path.write_text(json.dumps(placebo, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "experiment_dir": str(out_dir),
                "robustness_json": str(rob_path),
                "placebo_json": str(plc_path),
                "base_test_net_pnl": base["net_pnl"],
                "placebo_shuffle_net_pnl": placebo_shuffle["net_pnl"],
                "placebo_invert_net_pnl": placebo_invert["net_pnl"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
