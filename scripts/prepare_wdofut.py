#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd


DATE_RE = re.compile(r"(20\d{2}[-_]?([01]\d)[-_]?([0-3]\d))")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare WDOFUT parquet snapshots for analysis."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input path: parquet directory, raw archive directory, or .tar.zst archive",
    )
    parser.add_argument(
        "--work-dir",
        default="./data/raw_extracted",
        help="Extraction directory for archives (default: ./data/raw_extracted)",
    )
    parser.add_argument(
        "--output-dir",
        default="./data/wdofut_prepared",
        help="Output directory for normalized parquet (default: ./data/wdofut_prepared)",
    )
    parser.add_argument(
        "--extract-only",
        action="store_true",
        help="Extract archives only, do not prepare parquet output",
    )
    parser.add_argument(
        "--fail-on-invalid-archive",
        action="store_true",
        help="Fail immediately when an archive is invalid/empty (default: skip invalid archives)",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Optional cap on number of parquet files to process",
    )
    parser.add_argument(
        "--columns",
        nargs="*",
        default=None,
        help="Optional list of columns to read from parquet files",
    )
    parser.add_argument(
        "--timestamp-col",
        default=None,
        help="Timestamp column override (auto-detected if omitted)",
    )
    parser.add_argument(
        "--start-date",
        default=None,
        help="Optional lower bound date filter (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Optional upper bound date filter (YYYY-MM-DD, inclusive)",
    )
    return parser.parse_args()


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def archive_extract_dir(archive_path: Path, work_dir: Path) -> Path:
    base = archive_path.name
    for suffix in (".tar.zst", ".tzst", ".zst", ".tar"):
        if base.lower().endswith(suffix):
            base = base[: -len(suffix)]
            break
    target = work_dir / base
    ensure_dir(target)
    return target


def extract_archive(archive_path: Path, work_dir: Path) -> Path:
    if archive_path.stat().st_size < 128:
        raise RuntimeError(
            f"Archive looks too small ({archive_path.stat().st_size} bytes): {archive_path}. "
            "This usually means an incomplete/corrupt download."
        )

    target_dir = archive_extract_dir(archive_path, work_dir)
    lower_name = archive_path.name.lower()
    if lower_name.endswith(".tar"):
        list_cmd = ["tar", "-tf", str(archive_path)]
        extract_cmd = ["tar", "-xf", str(archive_path), "-C", str(target_dir)]
    elif lower_name.endswith(".tar.zst") or lower_name.endswith(".tzst") or lower_name.endswith(".zst"):
        list_cmd = ["tar", "--zstd", "-tf", str(archive_path)]
        extract_cmd = ["tar", "--zstd", "-xf", str(archive_path), "-C", str(target_dir)]
    else:
        raise RuntimeError(
            f"Unsupported archive format: {archive_path}. Supported: .tar, .tar.zst, .tzst"
        )

    list_result = subprocess.run(list_cmd, capture_output=True, text=True)
    if list_result.returncode != 0:
        raise RuntimeError(
            f"Archive listing failed.\nCommand: {' '.join(list_cmd)}\n{list_result.stderr}"
        )
    members = [line for line in list_result.stdout.splitlines() if line.strip()]
    if not members:
        raise RuntimeError(
            f"Archive has no entries: {archive_path}. "
            "Check if source file is empty or not a valid tar.zst payload."
        )

    result = subprocess.run(extract_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"Archive extraction failed.\nCommand: {' '.join(extract_cmd)}\n{result.stderr}"
        )
    return target_dir


def discover_archives(root: Path) -> list[Path]:
    archives: set[Path] = set()
    for pattern in ("*.tar.zst", "*.tzst", "*.tar", "*.zst"):
        archives.update(root.rglob(pattern))
    return sorted(p for p in archives if p.is_file())


def discover_parquet_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.parquet") if p.is_file())


def resolve_source_roots(
    input_path: Path,
    work_dir: Path,
    fail_on_invalid_archive: bool = False,
) -> tuple[list[Path], list[Path], list[str]]:
    ensure_dir(work_dir)

    extracted_roots: list[Path] = []
    source_roots: list[Path] = []
    skipped_archives: list[str] = []

    if input_path.is_file():
        name = input_path.name.lower()
        if name.endswith(".tar.zst") or name.endswith(".tzst") or name.endswith(".tar") or name.endswith(".zst"):
            try:
                extracted = extract_archive(input_path, work_dir)
            except Exception as exc:
                if fail_on_invalid_archive:
                    raise
                skipped_archives.append(f"{input_path}: {exc}")
                return [], [], skipped_archives
            extracted_roots.append(extracted)
            source_roots.append(extracted)
            return source_roots, extracted_roots, skipped_archives
        raise ValueError("Input file must be .tar, .tar.zst, .tzst or .zst archive")

    if not input_path.is_dir():
        raise ValueError("Input path does not exist")

    archives = discover_archives(input_path)
    for archive in archives:
        try:
            extracted = extract_archive(archive, work_dir)
            extracted_roots.append(extracted)
        except Exception as exc:
            msg = f"{archive}: {exc}"
            if fail_on_invalid_archive:
                raise RuntimeError(msg) from exc
            print(f"Skipping invalid archive: {msg}")
            skipped_archives.append(msg)

    if extracted_roots:
        source_roots.extend(extracted_roots)

    if discover_parquet_files(input_path):
        source_roots.append(input_path)

    unique_roots = sorted(set(source_roots))
    return unique_roots, extracted_roots, skipped_archives


def detect_timestamp_column(df: pd.DataFrame, forced: str | None) -> str:
    if forced:
        if forced not in df.columns:
            raise ValueError(f"Provided timestamp column '{forced}' not found")
        return forced

    candidates = ["timestamp", "ts", "datetime", "date_time", "time"]
    lowered = {col.lower(): col for col in df.columns}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    raise ValueError("Could not auto-detect timestamp column")


def normalize_dataframe(df: pd.DataFrame, timestamp_col: str) -> tuple[pd.DataFrame, str]:
    df = df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    timestamp_col = timestamp_col.lower()

    df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True, errors="coerce")
    df = df.dropna(subset=[timestamp_col])
    df = df.sort_values(timestamp_col)
    df = df.drop_duplicates(subset=[timestamp_col], keep="last")

    if "bid" in df.columns and "ask" in df.columns:
        df["mid"] = (df["bid"] + df["ask"]) / 2.0
        df["spread"] = df["ask"] - df["bid"]

    if "last" in df.columns:
        safe_last = df["last"].where(df["last"] > 0)
        df["log_return"] = np.log(safe_last).diff()

    return df, timestamp_col


def apply_date_window(
    df: pd.DataFrame,
    timestamp_col: str,
    start_date: str | None,
    end_date: str | None,
) -> pd.DataFrame:
    if not start_date and not end_date:
        return df

    filtered = df
    if start_date:
        start_ts = pd.to_datetime(start_date, utc=True)
        filtered = filtered[filtered[timestamp_col] >= start_ts]

    if end_date:
        end_exclusive = pd.to_datetime(end_date, utc=True) + pd.Timedelta(days=1)
        filtered = filtered[filtered[timestamp_col] < end_exclusive]

    return filtered


def extract_date_from_filename(path: Path) -> str | None:
    match = DATE_RE.search(path.name)
    if not match:
        return None
    raw = match.group(1).replace("_", "").replace("-", "")
    return f"{raw[:4]}-{raw[4:6]}-{raw[6:8]}"


def write_partitioned(df: pd.DataFrame, ts_col: str, output_dir: Path, stem: str) -> int:
    written = 0
    day_values = df[ts_col].dt.strftime("%Y-%m-%d")
    for day, part in df.groupby(day_values):
        day_dir = output_dir / f"day={day}"
        ensure_dir(day_dir)
        out_file = day_dir / f"{stem}.parquet"
        part.to_parquet(out_file, index=False)
        written += len(part)
    return written


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).expanduser().resolve()
    work_dir = Path(args.work_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    source_roots, extracted_roots, skipped_archives = resolve_source_roots(
        input_path,
        work_dir,
        fail_on_invalid_archive=args.fail_on_invalid_archive,
    )
    if not source_roots:
        raise SystemExit(
            "No parquet sources found. Check input path and archive contents."
            + (f" Skipped invalid archives: {len(skipped_archives)}" if skipped_archives else "")
        )

    if args.extract_only:
        print(
            f"Extraction complete. Extracted roots: {len(extracted_roots)} at {work_dir}. "
            f"Skipped invalid archives: {len(skipped_archives)}"
        )
        return

    ensure_dir(output_dir)

    files: list[Path] = []
    seen: set[Path] = set()
    for root in source_roots:
        for parquet in discover_parquet_files(root):
            if parquet not in seen:
                seen.add(parquet)
                files.append(parquet)

    files = sorted(files)
    if args.max_files is not None:
        files = files[: args.max_files]

    if not files:
        raise SystemExit("No parquet files found")

    manifest: list[dict[str, object]] = []
    total_rows = 0

    for file_path in files:
        frame = pd.read_parquet(file_path, columns=args.columns)
        ts_col = detect_timestamp_column(frame, args.timestamp_col)
        normalized, ts_col = normalize_dataframe(frame, ts_col)
        filtered = apply_date_window(
            normalized,
            ts_col,
            start_date=args.start_date,
            end_date=args.end_date,
        )

        stem_day = extract_date_from_filename(file_path)
        stem = file_path.stem if stem_day is None else f"{file_path.stem}_{stem_day}"

        rows_written = write_partitioned(filtered, ts_col, output_dir, stem) if not filtered.empty else 0
        total_rows += rows_written

        manifest.append(
            {
                "file": str(file_path),
                "rows_in": int(len(frame)),
                "rows_out": int(rows_written),
                "timestamp_col": ts_col,
                "ts_min": str(filtered[ts_col].min()) if not filtered.empty else None,
                "ts_max": str(filtered[ts_col].max()) if not filtered.empty else None,
            }
        )

    summary = {
        "input": str(input_path),
        "source_roots": [str(p) for p in source_roots],
        "extracted_roots": [str(p) for p in extracted_roots],
        "skipped_archives": skipped_archives,
        "output_dir": str(output_dir),
        "files_processed": len(files),
        "rows_written_total": total_rows,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "manifest": manifest,
    }
    summary_path = output_dir / "_prep_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Preparation complete. Summary: {summary_path}")


if __name__ == "__main__":
    main()
