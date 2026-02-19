#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load prepared parquet dataset into a single pandas DataFrame."
    )
    parser.add_argument(
        "--input-dir",
        default="./data/wdofut_prepared",
        help="Prepared parquet directory (default: ./data/wdofut_prepared)",
    )
    parser.add_argument(
        "--start-date",
        default=None,
        help="Optional lower bound date YYYY-MM-DD for partition pruning",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Optional upper bound date YYYY-MM-DD for partition pruning",
    )
    parser.add_argument(
        "--columns",
        nargs="*",
        default=None,
        help="Optional column subset to load",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Optional cap on number of parquet files",
    )
    parser.add_argument(
        "--output-parquet",
        default=None,
        help="Optional output parquet path to persist combined dataframe",
    )
    parser.add_argument(
        "--output-pickle",
        default=None,
        help="Optional output pickle path to persist combined dataframe",
    )
    parser.add_argument(
        "--combined-parquet",
        default=None,
        help=(
            "Optional combined parquet cache path. "
            "If it exists, load directly from it. "
            "If missing, build from partitions and save to this path."
        ),
    )
    return parser.parse_args()


def day_in_window(day_value: str, start_date: str | None, end_date: str | None) -> bool:
    if start_date and day_value < start_date:
        return False
    if end_date and day_value > end_date:
        return False
    return True


def discover_parquet_files(
    input_dir: Path,
    start_date: str | None,
    end_date: str | None,
) -> list[Path]:
    files: list[Path] = []
    for path in sorted(input_dir.rglob("*.parquet")):
        if not path.is_file():
            continue
        day_parts = [part for part in path.parts if part.startswith("day=")]
        if day_parts:
            day_value = day_parts[-1].split("=", 1)[1]
            if not day_in_window(day_value, start_date, end_date):
                continue
        files.append(path)
    return files


def main() -> int:
    args = parse_args()
    combined_parquet_path = (
        Path(args.combined_parquet).expanduser().resolve()
        if args.combined_parquet
        else None
    )

    if combined_parquet_path and combined_parquet_path.exists():
        print(f"Loading combined parquet cache: {combined_parquet_path}")
        df = pd.read_parquet(combined_parquet_path, columns=args.columns)
    else:
        input_dir = Path(args.input_dir).expanduser().resolve()
        if not input_dir.exists():
            raise SystemExit(f"Input directory not found: {input_dir}")

        files = discover_parquet_files(input_dir, args.start_date, args.end_date)
        if args.max_files is not None:
            files = files[: args.max_files]
        if not files:
            raise SystemExit("No parquet files found for the selected filters.")

        print(f"Loading {len(files)} parquet file(s) from {input_dir}")
        frames = [pd.read_parquet(file_path, columns=args.columns) for file_path in files]
        df = pd.concat(frames, ignore_index=True)

        if combined_parquet_path:
            combined_parquet_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_parquet(combined_parquet_path, index=False)
            print(f"Saved combined parquet cache: {combined_parquet_path}")

    print(f"DataFrame shape: {df.shape}")
    print("Columns:")
    print(df.columns.tolist())
    print("Dtypes:")
    print(df.dtypes)
    print(df.head())

    if "timestamp" in df.columns:
        ts_series = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
        print(f"Timestamp min: {ts_series.min()}")
        print(f"Timestamp max: {ts_series.max()}")

    if args.output_parquet:
        out_path = Path(args.output_parquet).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(out_path, index=False)
        print(f"Saved combined parquet: {out_path}")

    if args.output_pickle:
        out_path = Path(args.output_pickle).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_pickle(out_path)
        print(f"Saved combined pickle: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
