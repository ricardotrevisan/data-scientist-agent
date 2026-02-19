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
        description="Step 4: Build causal feature set and run univariate scan vs y_tb."
    )
    parser.add_argument(
        "--input-parquet",
        default="./data/wdofut_prepared/wdofut_labels_tb.parquet",
        help="Input labeled parquet path.",
    )
    parser.add_argument(
        "--output-features-parquet",
        default="./data/wdofut_prepared/wdofut_features_v1.parquet",
        help="Output parquet with engineered causal features.",
    )
    parser.add_argument(
        "--output-json",
        default="./data/wdofut_prepared/wdofut_feature_scan.json",
        help="Output JSON with univariate ranking.",
    )
    return parser.parse_args()


def temporal_split(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    n = len(df)
    i1 = int(0.6 * n)
    i2 = int(0.8 * n)
    return {
        "train": df.iloc[:i1].copy(),
        "val": df.iloc[i1:i2].copy(),
        "test": df.iloc[i2:].copy(),
    }


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.sort_values("timestamp").reset_index(drop=True)

    # Causal core series (strictly <= t)
    ret = out["log_return"].astype(float).fillna(0.0)
    spread = out["spread"].astype(float).ffill().fillna(0.0)

    out["ret_lag1"] = ret.shift(1)
    out["ret_lag2"] = ret.shift(2)
    out["ret_sum_5"] = ret.shift(1).rolling(5, min_periods=5).sum()
    out["ret_sum_10"] = ret.shift(1).rolling(10, min_periods=10).sum()
    out["ret_sum_20"] = ret.shift(1).rolling(20, min_periods=20).sum()

    out["vol_5"] = ret.shift(1).rolling(5, min_periods=5).std(ddof=0)
    out["vol_20"] = ret.shift(1).rolling(20, min_periods=20).std(ddof=0)
    out["vol_60"] = ret.shift(1).rolling(60, min_periods=60).std(ddof=0)

    mu20 = ret.shift(1).rolling(20, min_periods=20).mean()
    sd20 = ret.shift(1).rolling(20, min_periods=20).std(ddof=0)
    out["zret_20"] = np.where(sd20 > 0, (out["ret_lag1"] - mu20) / sd20, np.nan)

    out["spread_lag1"] = spread.shift(1)
    out["spread_delta1"] = spread.shift(1) - spread.shift(2)
    s_mu20 = spread.shift(1).rolling(20, min_periods=20).mean()
    s_sd20 = spread.shift(1).rolling(20, min_periods=20).std(ddof=0)
    out["spread_z_20"] = np.where(s_sd20 > 0, (out["spread_lag1"] - s_mu20) / s_sd20, np.nan)

    v = out["vol_20"]
    v_mu60 = v.shift(1).rolling(60, min_periods=60).mean()
    out["vol_regime_20_over_60"] = np.where(v_mu60 > 0, v / v_mu60, np.nan)

    return out


def feature_score(series: pd.Series, y: pd.Series) -> dict[str, float]:
    mask = series.notna() & y.notna()
    x = series[mask]
    yt = y[mask]
    if len(x) < 100:
        return {"rows": float(len(x)), "pearson": 0.0, "spearman": 0.0, "q4_q1_y_diff": 0.0}

    pear = float(x.corr(yt, method="pearson"))
    spear = float(x.corr(yt, method="spearman"))

    q1, q4 = x.quantile(0.25), x.quantile(0.75)
    low = yt[x <= q1]
    high = yt[x >= q4]
    qdiff = float(high.mean() - low.mean()) if len(low) and len(high) else 0.0
    return {"rows": float(len(x)), "pearson": pear, "spearman": spear, "q4_q1_y_diff": qdiff}


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
    df = df.dropna(subset=["timestamp", "y_tb"]).copy()

    feat = build_features(df)
    feature_cols = [
        "ret_lag1",
        "ret_lag2",
        "ret_sum_5",
        "ret_sum_10",
        "ret_sum_20",
        "vol_5",
        "vol_20",
        "vol_60",
        "zret_20",
        "spread_lag1",
        "spread_delta1",
        "spread_z_20",
        "vol_regime_20_over_60",
    ]

    splits = temporal_split(feat)
    report: dict[str, Any] = {
        "input_parquet": str(in_path),
        "rows_total": int(len(feat)),
        "feature_count": len(feature_cols),
        "features": feature_cols,
        "split": {"train_ratio": 0.6, "val_ratio": 0.2, "test_ratio": 0.2},
        "scores": {},
        "ranking_test_abs_spearman": [],
    }

    for f in feature_cols:
        report["scores"][f] = {}
        for sname, sdf in splits.items():
            report["scores"][f][sname] = feature_score(sdf[f], sdf["y_tb"])

    ranking = []
    for f in feature_cols:
        s = report["scores"][f]["test"]["spearman"]
        ranking.append((f, abs(float(s)), float(s), float(report["scores"][f]["test"]["q4_q1_y_diff"])))
    ranking.sort(key=lambda x: x[1], reverse=True)
    report["ranking_test_abs_spearman"] = [
        {"feature": f, "abs_spearman_test": a, "spearman_test": s, "q4_q1_y_diff_test": qd}
        for f, a, s, qd in ranking
    ]

    out_feat = Path(args.output_features_parquet).expanduser().resolve()
    out_feat.parent.mkdir(parents=True, exist_ok=True)
    keep_cols = ["timestamp", "y_tb"] + feature_cols
    feat[keep_cols].to_parquet(out_feat, index=False)

    out_json = Path(args.output_json).expanduser().resolve()
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
