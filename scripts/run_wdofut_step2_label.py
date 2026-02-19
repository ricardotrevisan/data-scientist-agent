#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build causal triple-barrier labels for WDOFUT without leakage."
    )
    parser.add_argument(
        "--input-parquet",
        default="./data/wdofut_prepared/wdofut_combined.parquet",
        help="Combined parquet path (default: ./data/wdofut_prepared/wdofut_combined.parquet)",
    )
    parser.add_argument(
        "--input-dir",
        default="./data/wdofut_prepared",
        help="Partitioned parquet directory used when --input-parquet is missing.",
    )
    parser.add_argument(
        "--h-minutes",
        type=float,
        default=5.0,
        help="Forward horizon in minutes (default: 5.0)",
    )
    parser.add_argument(
        "--price-col",
        default="mid",
        choices=["mid", "last"],
        help="Reference price column (default: mid)",
    )
    parser.add_argument(
        "--up-barrier",
        type=float,
        default=0.00035,
        help="Upper log-return barrier u (default: 0.00035)",
    )
    parser.add_argument(
        "--down-barrier",
        type=float,
        default=0.00035,
        help="Lower log-return barrier d (default: 0.00035)",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=None,
        help="Optional cap for quick runs (after sorting by timestamp).",
    )
    parser.add_argument(
        "--output-parquet",
        default="./data/wdofut_prepared/wdofut_labels_tb.parquet",
        help="Output parquet for generated labels.",
    )
    parser.add_argument(
        "--output-summary",
        default="./data/wdofut_prepared/wdofut_labels_tb_summary.json",
        help="Output JSON summary path.",
    )
    return parser.parse_args()


def load_df(path: Path, price_col: str) -> pd.DataFrame:
    cols = ["timestamp", price_col, "spread", "log_return"]
    df = pd.read_parquet(path, columns=cols)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp", price_col]).sort_values("timestamp").reset_index(drop=True)
    return df


def load_from_dir(path: Path, price_col: str) -> pd.DataFrame:
    # Only read canonical prepared partitions to avoid re-ingesting generated
    # artifacts (labels/cache) placed in the same folder.
    files = sorted(path.glob("day=*/*.parquet"))
    if not files:
        raise SystemExit(f"No parquet files found under: {path}")
    cols = ["timestamp", price_col, "spread", "log_return"]
    frames = [pd.read_parquet(p, columns=cols) for p in files]
    df = pd.concat(frames, ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp", price_col]).sort_values("timestamp").reset_index(drop=True)
    return df


def build_label(
    df: pd.DataFrame,
    *,
    price_col: str,
    h_minutes: float,
    up_barrier: float,
    down_barrier: float,
) -> pd.DataFrame:
    ts = df["timestamp"].to_numpy(dtype="datetime64[ns]")
    px = df[price_col].to_numpy(dtype=float)
    n = len(df)
    out = np.zeros(n, dtype=np.int8)
    first_hit = np.array(["none"] * n, dtype=object)
    future_ts = np.full(n, np.datetime64("NaT"), dtype="datetime64[ns]")
    future_px = np.full(n, np.nan, dtype=float)

    horizon_ns = np.timedelta64(int(h_minutes * 60 * 1_000_000_000), "ns")
    end_idx = np.searchsorted(ts, ts + horizon_ns, side="right")

    for i in range(n):
        j = end_idx[i]
        if j <= i + 1:
            continue
        p0 = px[i]
        if p0 <= 0:
            continue
        fut = px[i + 1 : j]
        # Guard against invalid future prices to avoid inf/nan labels.
        valid = fut > 0
        if not np.any(valid):
            continue
        rel = np.log(fut[valid] / p0)
        valid_idx = np.nonzero(valid)[0]

        up_hits = np.where(rel >= up_barrier)[0]
        dn_hits = np.where(rel <= -down_barrier)[0]
        up0 = up_hits[0] if up_hits.size else None
        dn0 = dn_hits[0] if dn_hits.size else None

        if up0 is None and dn0 is None:
            continue
        if dn0 is None or (up0 is not None and up0 < dn0):
            hit_off = int(valid_idx[up0])
            out[i] = 1
            first_hit[i] = "up"
        else:
            hit_off = int(valid_idx[dn0])
            out[i] = -1
            first_hit[i] = "down"

        hit_idx = i + 1 + int(hit_off)
        future_ts[i] = ts[hit_idx]
        future_px[i] = px[hit_idx]

    result = df.copy()
    result["price_t"] = result[price_col]
    result["price_hit"] = future_px
    result["timestamp_hit"] = pd.to_datetime(future_ts, utc=True, errors="coerce")
    result["y_tb"] = out
    result["first_hit"] = first_hit
    return result


def summarize(df: pd.DataFrame) -> dict:
    y = df["y_tb"]
    counts = y.value_counts(dropna=False).sort_index()
    total = int(len(y))
    p_zero = float((y == 0).mean()) if total else 0.0
    skew = float(y.skew()) if total else 0.0
    sample = (
        df.loc[df["y_tb"] != 0, ["timestamp", "price_t", "price_hit", "y_tb", "first_hit"]]
        .head(5)
        .to_dict(orient="records")
    )
    return {
        "rows": total,
        "label_counts": {str(int(k)): int(v) for k, v in counts.items()},
        "pct_zero": p_zero,
        "skewness": skew,
        "examples": sample,
    }


def main() -> int:
    args = parse_args()
    in_path = Path(args.input_parquet).expanduser().resolve()
    if in_path.exists():
        df = load_df(in_path, args.price_col)
        input_ref = str(in_path)
    else:
        in_dir = Path(args.input_dir).expanduser().resolve()
        if not in_dir.exists():
            raise SystemExit(
                f"Input parquet not found: {in_path} and input dir not found: {in_dir}"
            )
        df = load_from_dir(in_dir, args.price_col)
        input_ref = str(in_dir)
    if args.max_rows is not None:
        df = df.head(args.max_rows).copy()

    labeled = build_label(
        df,
        price_col=args.price_col,
        h_minutes=args.h_minutes,
        up_barrier=args.up_barrier,
        down_barrier=args.down_barrier,
    )

    out_parquet = Path(args.output_parquet).expanduser().resolve()
    out_parquet.parent.mkdir(parents=True, exist_ok=True)
    labeled.to_parquet(out_parquet, index=False)

    summary = summarize(labeled)
    summary.update(
        {
            "input_reference": input_ref,
            "output_parquet": str(out_parquet),
            "h_minutes": args.h_minutes,
            "price_col": args.price_col,
            "up_barrier": args.up_barrier,
            "down_barrier": args.down_barrier,
        }
    )
    out_summary = Path(args.output_summary).expanduser().resolve()
    out_summary.parent.mkdir(parents=True, exist_ok=True)
    out_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
