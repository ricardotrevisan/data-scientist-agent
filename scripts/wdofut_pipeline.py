#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    print(f"\n$ {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def discover_archives(raw_dir: Path) -> list[Path]:
    archives: set[Path] = set()
    for pattern in ("*.tar.zst", "*.tzst", "*.tar", "*.zst"):
        archives.update(raw_dir.rglob(pattern))
    return sorted(p for p in archives if p.is_file())


def has_parquet(root: Path) -> bool:
    return any(root.rglob("*.parquet"))


def precheck_archives(raw_dir: Path, min_bytes: int) -> tuple[list[Path], list[Path]]:
    archives = discover_archives(raw_dir)
    if not archives:
        print(f"No archives found under: {raw_dir}")
        return [], []

    print(f"Found {len(archives)} archive(s) under {raw_dir}")
    bad: list[Path] = []
    good: list[Path] = []
    for archive in archives:
        size = archive.stat().st_size
        print(f"- {archive} ({size} bytes)")
        if size < min_bytes:
            bad.append(archive)
        else:
            good.append(archive)

    if bad:
        print("\nArchive precheck warning. These files are too small and will likely be skipped:")
        for path in bad:
            print(f"  - {path} ({path.stat().st_size} bytes)")
    return good, bad


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="End-to-end WDOFUT raw archive -> prepared parquet -> validation pipeline."
    )
    parser.add_argument("--raw-dir", default="./data/raw", help="Raw archive directory")
    parser.add_argument(
        "--work-dir",
        default="./data/raw_extracted",
        help="Extraction working directory",
    )
    parser.add_argument(
        "--output-dir",
        default="./data/wdofut_prepared",
        help="Prepared parquet output directory",
    )
    parser.add_argument("--start-date", default=None, help="Filter start date YYYY-MM-DD")
    parser.add_argument("--end-date", default=None, help="Filter end date YYYY-MM-DD")
    parser.add_argument("--max-files", type=int, default=None, help="Optional file cap")
    parser.add_argument(
        "--timestamp-col",
        default=None,
        help="Timestamp column override for prep script",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10000,
        help="Validator max rows scan (default: 10000)",
    )
    parser.add_argument(
        "--min-archive-bytes",
        type=int,
        default=128,
        help="Minimum archive size for sanity precheck",
    )
    parser.add_argument(
        "--skip-validate",
        action="store_true",
        help="Skip parquet validation step",
    )
    parser.add_argument(
        "--fail-on-invalid-archive",
        action="store_true",
        help="Fail pipeline when any invalid archive is found",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_dir = Path(args.raw_dir).expanduser().resolve()
    work_dir = Path(args.work_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()

    python = sys.executable

    print("Step 1/4: archive precheck")
    good_archives, bad_archives = precheck_archives(raw_dir, args.min_archive_bytes)
    if args.fail_on_invalid_archive and bad_archives:
        raise SystemExit(2)

    print("\nStep 2/4: extract archives")
    if good_archives:
        run(
            [
                python,
                "scripts/prepare_wdofut.py",
                "--input",
                str(raw_dir),
                "--work-dir",
                str(work_dir),
                "--extract-only",
            ]
        )
    else:
        print("No usable archives found for extraction. Proceeding with existing work-dir parquet if present.")
        if not has_parquet(work_dir):
            raise SystemExit(
                "No usable archives in raw-dir and no parquet found in work-dir. "
                "Provide valid raw archives first."
            )

    print("\nStep 3/4: prepare parquet window")
    prep_cmd = [
        python,
        "scripts/prepare_wdofut.py",
        "--input",
        str(work_dir),
        "--output-dir",
        str(output_dir),
    ]
    if args.start_date:
        prep_cmd.extend(["--start-date", args.start_date])
    if args.end_date:
        prep_cmd.extend(["--end-date", args.end_date])
    if args.max_files is not None:
        prep_cmd.extend(["--max-files", str(args.max_files)])
    if args.timestamp_col:
        prep_cmd.extend(["--timestamp-col", args.timestamp_col])
    run(prep_cmd)

    if not args.skip_validate:
        print("\nStep 4/4: validate prepared parquet")
        run(
            [
                python,
                "scripts/parquet_remount_validate.py",
                "--parquet-base",
                str(output_dir),
                "--limit",
                str(args.limit),
                "--full-json",
                "--strict-floats",
            ]
        )

    print("\nPipeline completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
