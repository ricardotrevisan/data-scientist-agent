#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Step 3 temporal OOS baselines on WDOFUT labeled data."
    )
    parser.add_argument(
        "--input-parquet",
        default="./data/wdofut_prepared/wdofut_labels_tb.parquet",
        help="Input labeled parquet (default: ./data/wdofut_prepared/wdofut_labels_tb.parquet)",
    )
    parser.add_argument(
        "--cost-per-trade",
        type=float,
        default=0.0,
        help="Flat cost applied whenever signal != 0 (default: 0.0)",
    )
    parser.add_argument(
        "--output-json",
        default="./data/wdofut_prepared/wdofut_baselines_metrics.json",
        help="Output metrics JSON path.",
    )
    return parser.parse_args()


def split_temporal(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    n = len(df)
    i1 = int(n * 0.6)
    i2 = int(n * 0.8)
    return {
        "train": df.iloc[:i1].copy(),
        "val": df.iloc[i1:i2].copy(),
        "test": df.iloc[i2:].copy(),
    }


def max_drawdown(cum_pnl: np.ndarray) -> float:
    if cum_pnl.size == 0:
        return 0.0
    running_max = np.maximum.accumulate(cum_pnl)
    dd = running_max - cum_pnl
    return float(dd.max(initial=0.0))


def evaluate(signal: np.ndarray, y: np.ndarray, cost_per_trade: float) -> dict[str, Any]:
    traded = signal != 0
    pnl = signal * y - traded.astype(float) * cost_per_trade
    cum = np.cumsum(pnl)
    gross_profit = pnl[pnl > 0].sum()
    gross_loss = -pnl[pnl < 0].sum()
    if gross_loss == 0:
        pf = float("inf") if gross_profit > 0 else 0.0
    else:
        pf = float(gross_profit / gross_loss)

    trade_count = int(traded.sum())
    wins = int((pnl[traded] > 0).sum()) if trade_count else 0
    hit_rate = float(wins / trade_count) if trade_count else 0.0
    turnover = float(np.abs(np.diff(signal, prepend=0)).sum())

    std = pnl.std(ddof=0)
    sharpe = float((pnl.mean() / std) * np.sqrt(len(pnl))) if std > 0 else 0.0

    return {
        "rows": int(len(y)),
        "trades": trade_count,
        "net_pnl": float(pnl.sum()),
        "sharpe": sharpe,
        "profit_factor": pf,
        "max_drawdown": max_drawdown(cum),
        "hit_rate": hit_rate,
        "turnover": turnover,
    }


def build_baselines(df: pd.DataFrame) -> dict[str, np.ndarray]:
    y = df["y_tb"].to_numpy(dtype=float)
    lag_ret = df["log_return"].fillna(0.0).to_numpy(dtype=float)

    # 1) no-trade
    b1 = np.zeros_like(y, dtype=float)

    # 2) past return sign
    b2 = np.sign(lag_ret).astype(float)

    # 3) spread/vol regime gate + past return sign
    spread = df["spread"].to_numpy(dtype=float)
    vol = np.abs(lag_ret)
    spread_thr = float(np.nanmedian(spread))
    vol_thr = float(np.nanquantile(vol, 0.75))
    gate = (spread <= spread_thr) & (vol <= vol_thr)
    b3 = np.where(gate, np.sign(lag_ret), 0.0).astype(float)

    return {
        "no_trade": b1,
        "lagged_return_sign": b2,
        "spread_vol_rule": b3,
    }


def main() -> int:
    args = parse_args()
    in_path = Path(args.input_parquet).expanduser().resolve()
    if not in_path.exists():
        raise SystemExit(f"Input parquet not found: {in_path}")

    df = pd.read_parquet(in_path)
    required = {"timestamp", "y_tb", "log_return", "spread"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp", "y_tb"]).sort_values("timestamp").reset_index(drop=True)

    splits = split_temporal(df)
    metrics: dict[str, Any] = {
        "input_parquet": str(in_path),
        "cost_per_trade": args.cost_per_trade,
        "split": {"train_ratio": 0.6, "val_ratio": 0.2, "test_ratio": 0.2},
        "baselines": {},
    }

    for split_name, sdf in splits.items():
        y = sdf["y_tb"].to_numpy(dtype=float)
        signals = build_baselines(sdf)
        for bname, sig in signals.items():
            metrics["baselines"].setdefault(bname, {})[split_name] = evaluate(
                sig, y, args.cost_per_trade
            )

    # OOS aggregate = val + test
    for bname in list(metrics["baselines"].keys()):
        val = metrics["baselines"][bname]["val"]
        test = metrics["baselines"][bname]["test"]
        rows = val["rows"] + test["rows"]
        trades = val["trades"] + test["trades"]
        net_pnl = val["net_pnl"] + test["net_pnl"]
        turnover = val["turnover"] + test["turnover"]
        metrics["baselines"][bname]["oos_val_test"] = {
            "rows": rows,
            "trades": trades,
            "net_pnl": net_pnl,
            "hit_rate": ((val["hit_rate"] * val["trades"]) + (test["hit_rate"] * test["trades"])) / trades
            if trades
            else 0.0,
            "turnover": turnover,
        }

    out_path = Path(args.output_json).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
