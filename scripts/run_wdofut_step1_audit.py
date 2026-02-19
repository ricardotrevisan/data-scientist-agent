#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

import pyarrow.dataset as ds


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Step 1: deterministic dataset audit for prepared WDOFUT parquet."
    )
    parser.add_argument(
        "--input-dir",
        default="./data/wdofut_prepared",
        help="Prepared parquet directory.",
    )
    parser.add_argument(
        "--output-json",
        default="./data/wdofut_prepared/step1_audit_report.json",
        help="Output audit JSON path.",
    )
    return parser.parse_args()


def describe(vs: list[float]) -> dict[str, float] | None:
    if not vs:
        return None
    s = sorted(vs)
    n = len(s)
    q = lambda p: s[min(n - 1, max(0, int((n - 1) * p)))]
    return {
        "count": float(n),
        "min": float(s[0]),
        "p25": float(q(0.25)),
        "mean": float(mean(s)),
        "p50": float(q(0.5)),
        "p75": float(q(0.75)),
        "max": float(s[-1]),
    }


def main() -> int:
    args = parse_args()
    base = Path(args.input_dir).expanduser().resolve()
    if not base.exists():
        raise SystemExit(f"Input directory not found: {base}")

    files = sorted(base.glob("day=*/*.parquet"))
    if not files:
        raise SystemExit(f"No day-partition parquet files under: {base}")

    dataset = ds.dataset([str(p) for p in files], format="parquet", partitioning="hive")
    schema = {f.name: str(f.type) for f in dataset.schema}

    rows_per_day: dict[str, int] = {}
    minmax_day: dict[str, dict[str, str | None]] = {}
    for ddir in sorted(base.glob("day=*")):
        day = ddir.name.split("=", 1)[1]
        dset = ds.dataset(str(ddir), format="parquet")
        cnt = 0
        lo = None
        hi = None
        col_name = "timestamp" if "timestamp" in schema else "ts"
        for b in dset.to_batches(columns=[col_name]):
            col = b.column(0).to_pylist()
            cnt += len(col)
            for v in col:
                if v is None:
                    continue
                sv = str(v)
                if lo is None or sv < lo:
                    lo = sv
                if hi is None or sv > hi:
                    hi = sv
        rows_per_day[day] = cnt
        minmax_day[day] = {"min": lo, "max": hi}

    cols = [c for c in ["ts", "timestamp", "spread", "mid", "log_return"] if c in schema]
    scanner = dataset.scanner(columns=cols)
    null_counts = {c: 0 for c in cols}
    duplicate_ts_rows = 0
    seen_ts = set()
    rows_total = 0
    values = {c: [] for c in ["spread", "mid", "log_return"] if c in cols}
    min_ts = None
    max_ts = None

    for b in scanner.to_batches():
        rows_total += b.num_rows
        for c in cols:
            arr = b.column(c)
            null_counts[c] += arr.null_count
        if "ts" in cols:
            for v in b.column(cols.index("ts")).to_pylist():
                if v is None:
                    continue
                if min_ts is None or v < min_ts:
                    min_ts = v
                if max_ts is None or v > max_ts:
                    max_ts = v
                if v in seen_ts:
                    duplicate_ts_rows += 1
                else:
                    seen_ts.add(v)
        for c in values:
            values[c].extend([x for x in b.column(cols.index(c)).to_pylist() if x is not None])

    stats = {c: describe(values[c]) for c in values}
    out = {
        "input_dir": str(base),
        "parquet_files": len(files),
        "rows_total": rows_total,
        "schema": schema,
        "rows_per_day": rows_per_day,
        "null_counts": null_counts,
        "duplicate_ts_rows": duplicate_ts_rows,
        "min_ts": min_ts,
        "max_ts": max_ts,
        "minmax_timestamp_by_day": minmax_day,
        "stats": stats,
    }

    out_path = Path(args.output_json).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
