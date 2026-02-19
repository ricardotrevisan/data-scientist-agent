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
        description="Step 6: walk-forward backtest for top Step 5 hypotheses."
    )
    parser.add_argument(
        "--input-features",
        default="./data/wdofut_prepared/wdofut_features_v1.parquet",
        help="Feature parquet from Step 4.",
    )
    parser.add_argument(
        "--input-candidates",
        default="",
        help="Path to candidates_top3.json from Step 5. If empty, uses latest in experiments/",
    )
    parser.add_argument(
        "--cost-per-trade",
        type=float,
        default=0.0,
        help="Flat cost for each non-zero signal observation.",
    )
    parser.add_argument(
        "--num-windows",
        type=int,
        default=6,
        help="Number of chronological walk-forward windows (default: 6).",
    )
    parser.add_argument(
        "--output-root",
        default="./experiments",
        help="Base output folder.",
    )
    parser.add_argument("--z-upper-quantile", type=float, default=0.95, help="Upper quantile for zret_20 extremes.")
    parser.add_argument("--z-lower-quantile", type=float, default=0.05, help="Lower quantile for zret_20 extremes.")
    parser.add_argument("--spread-upper-quantile", type=float, default=0.95, help="Upper quantile for spread_z_20 extremes.")
    parser.add_argument("--spread-lower-quantile", type=float, default=0.05, help="Lower quantile for spread_z_20 extremes.")
    parser.add_argument("--vol-regime-upper-quantile", type=float, default=0.85, help="Upper quantile for vol_regime_20_over_60 high-vol regime.")
    parser.add_argument("--vol-regime-lower-quantile", type=float, default=0.15, help="Lower quantile for vol_regime_20_over_60 low-vol regime.")
    return parser.parse_args()


def find_latest_candidates(base: Path) -> Path:
    matches = sorted(base.glob("*_step5_hypotheses/candidates_top3.json"))
    if not matches:
        raise SystemExit("No Step 5 candidates_top3.json found under experiments/")
    return matches[-1]


def split_temporal(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    n = len(df)
    i1 = int(0.6 * n)
    i2 = int(0.8 * n)
    return {"train": df.iloc[:i1].copy(), "val": df.iloc[i1:i2].copy(), "test": df.iloc[i2:].copy()}


def max_drawdown(cum_pnl: np.ndarray) -> float:
    if cum_pnl.size == 0:
        return 0.0
    runmax = np.maximum.accumulate(cum_pnl)
    dd = runmax - cum_pnl
    return float(dd.max(initial=0.0))


def eval_signal(signal: np.ndarray, y: np.ndarray, cost_per_trade: float) -> dict[str, Any]:
    traded = signal != 0
    pnl = signal * y - traded.astype(float) * cost_per_trade
    cum = np.cumsum(pnl)
    gp = pnl[pnl > 0].sum()
    gl = -pnl[pnl < 0].sum()
    pf = float(gp / gl) if gl > 0 else (float("inf") if gp > 0 else 0.0)
    std = pnl.std(ddof=0)
    sharpe = float((pnl.mean() / std) * np.sqrt(len(pnl))) if std > 0 else 0.0
    trades = int(traded.sum())
    hit = float((pnl[traded] > 0).mean()) if trades else 0.0
    turnover = float(np.abs(np.diff(signal, prepend=0)).sum())
    return {
        "rows": int(len(y)),
        "trades": trades,
        "net_pnl": float(pnl.sum()),
        "sharpe": sharpe,
        "profit_factor": pf,
        "max_drawdown": max_drawdown(cum),
        "hit_rate": hit,
        "turnover": turnover,
    }


def build_signal(
    hid: str,
    d: pd.DataFrame,
    *,
    z_upper_q: float,
    z_lower_q: float,
    spread_upper_q: float,
    spread_lower_q: float,
    vol_upper_q: float,
    vol_lower_q: float,
) -> np.ndarray:
    z = d["zret_20"]
    s = d["spread_z_20"]
    vr = d["vol_regime_20_over_60"]
    ret10 = d["ret_sum_10"]
    ret20 = d["ret_sum_20"]
    rl1 = d["ret_lag1"]
    sd1 = d["spread_delta1"]

    z95 = float(z.quantile(z_upper_q))
    z05 = float(z.quantile(z_lower_q))
    s95 = float(s.quantile(spread_upper_q))
    s05 = float(s.quantile(spread_lower_q))
    vr85 = float(vr.quantile(vol_upper_q))
    vr15 = float(vr.quantile(vol_lower_q))

    if hid == "H01":
        return np.where(z >= z95, -1.0, 0.0)
    if hid == "H02":
        return np.where(z <= z05, 1.0, 0.0)
    if hid == "H03":
        return np.where(vr <= vr15, np.sign(ret20).astype(float), 0.0)
    if hid == "H04":
        return np.where(vr >= vr85, -np.sign(ret20).astype(float), 0.0)
    if hid == "H05":
        return np.where(s >= s95, -1.0, 0.0)
    if hid == "H06":
        return np.where(s <= s05, 1.0, 0.0)
    if hid == "H07":
        return np.sign(ret10.fillna(0.0)).astype(float).to_numpy()
    if hid == "H08":
        return -np.sign(d["ret_sum_5"].fillna(0.0)).astype(float).to_numpy()
    if hid == "H09":
        return np.where(sd1 < 0, np.sign(rl1).astype(float), 0.0)
    if hid == "H10":
        return np.where((d["vol_20"] > d["vol_60"]) & (rl1 != 0), np.sign(rl1).astype(float), 0.0)
    raise ValueError(f"Unsupported hypothesis id: {hid}")


def build_windows(df: pd.DataFrame, num_windows: int) -> list[pd.DataFrame]:
    n = len(df)
    if num_windows < 1:
        return [df]
    step = n // num_windows
    windows: list[pd.DataFrame] = []
    for i in range(num_windows):
        a = i * step
        b = (i + 1) * step if i < num_windows - 1 else n
        windows.append(df.iloc[a:b].copy())
    return windows


def main() -> int:
    args = parse_args()
    feat_path = Path(args.input_features).expanduser().resolve()
    if not feat_path.exists():
        raise SystemExit(f"Input features parquet not found: {feat_path}")

    exp_root = Path(args.output_root).expanduser().resolve()
    cand_path = Path(args.input_candidates).expanduser().resolve() if args.input_candidates else find_latest_candidates(exp_root)
    if not cand_path.exists():
        raise SystemExit(f"Candidates file not found: {cand_path}")

    candidates = json.loads(cand_path.read_text(encoding="utf-8"))
    ids = [c["id"] for c in candidates]

    df = pd.read_parquet(feat_path)
    req = {"timestamp", "y_tb", "ret_sum_10", "ret_sum_20", "ret_sum_5", "ret_lag1", "zret_20", "spread_z_20", "spread_delta1", "vol_20", "vol_60", "vol_regime_20_over_60"}
    miss = sorted(req - set(df.columns))
    if miss:
        raise SystemExit(f"Missing required columns in features parquet: {miss}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp", "y_tb"]).sort_values("timestamp").reset_index(drop=True)
    splits = split_temporal(df)
    windows = build_windows(df, args.num_windows)

    out_metrics: dict[str, Any] = {
        "input_features": str(feat_path),
        "input_candidates": str(cand_path),
        "candidate_ids": ids,
        "cost_per_trade": args.cost_per_trade,
        "thresholds": {
            "z_upper_quantile": args.z_upper_quantile,
            "z_lower_quantile": args.z_lower_quantile,
            "spread_upper_quantile": args.spread_upper_quantile,
            "spread_lower_quantile": args.spread_lower_quantile,
            "vol_regime_upper_quantile": args.vol_regime_upper_quantile,
            "vol_regime_lower_quantile": args.vol_regime_lower_quantile,
        },
        "split": {"train_ratio": 0.6, "val_ratio": 0.2, "test_ratio": 0.2},
        "metrics": {},
    }
    out_windows: dict[str, Any] = {"num_windows": args.num_windows, "candidates": {}}

    trades_frames: list[pd.DataFrame] = []

    for hid in ids:
        out_metrics["metrics"][hid] = {}
        for sname, sdf in splits.items():
            sig = build_signal(
                hid,
                sdf,
                z_upper_q=args.z_upper_quantile,
                z_lower_q=args.z_lower_quantile,
                spread_upper_q=args.spread_upper_quantile,
                spread_lower_q=args.spread_lower_quantile,
                vol_upper_q=args.vol_regime_upper_quantile,
                vol_lower_q=args.vol_regime_lower_quantile,
            )
            y = sdf["y_tb"].to_numpy(dtype=float)
            out_metrics["metrics"][hid][sname] = eval_signal(sig, y, args.cost_per_trade)

        out_windows["candidates"][hid] = []
        for i, wdf in enumerate(windows, start=1):
            sig = build_signal(
                hid,
                wdf,
                z_upper_q=args.z_upper_quantile,
                z_lower_q=args.z_lower_quantile,
                spread_upper_q=args.spread_upper_quantile,
                spread_lower_q=args.spread_lower_quantile,
                vol_upper_q=args.vol_regime_upper_quantile,
                vol_lower_q=args.vol_regime_lower_quantile,
            )
            y = wdf["y_tb"].to_numpy(dtype=float)
            m = eval_signal(sig, y, args.cost_per_trade)
            m["window"] = i
            m["start"] = str(wdf["timestamp"].iloc[0]) if not wdf.empty else ""
            m["end"] = str(wdf["timestamp"].iloc[-1]) if not wdf.empty else ""
            out_windows["candidates"][hid].append(m)

            traded = sig != 0
            if traded.any():
                pnl = sig * y - traded.astype(float) * args.cost_per_trade
                tdf = pd.DataFrame(
                    {
                        "timestamp": wdf["timestamp"].to_numpy(),
                        "candidate_id": hid,
                        "signal": sig,
                        "y_tb": y,
                        "pnl": pnl,
                        "window": i,
                    }
                )
                trades_frames.append(tdf.loc[traded].copy())

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = exp_root / f"{ts}_step6_backtest"
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = out_dir / "metrics.json"
    windows_path = out_dir / "metrics_by_window.json"
    trades_path = out_dir / "trades.parquet"

    metrics_path.write_text(json.dumps(out_metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    windows_path.write_text(json.dumps(out_windows, ensure_ascii=False, indent=2), encoding="utf-8")
    if trades_frames:
        pd.concat(trades_frames, ignore_index=True).to_parquet(trades_path, index=False)
    else:
        pd.DataFrame(columns=["timestamp", "candidate_id", "signal", "y_tb", "pnl", "window"]).to_parquet(trades_path, index=False)

    print(
        json.dumps(
            {
                "experiment_dir": str(out_dir),
                "metrics_json": str(metrics_path),
                "metrics_by_window_json": str(windows_path),
                "trades_parquet": str(trades_path),
                "candidate_ids": ids,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
