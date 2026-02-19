#!/usr/bin/env python3
"""
Read-only validator for snapshot Parquet datasets.

Policy: this script NEVER rewrites Parquet. It only scans and reports.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


CRITICAL_PHYSICAL_PATHS: Tuple[str, ...] = (
    "state.flow.vol.rel",
    "state.flow.window.delta",
    "derived.effort_vs_result",
    "derived.absorption_signal",
    "state.price.last",
    "feed.VWAP",
)


def _get_path(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _is_finite_number(x: Any) -> bool:
    if not _is_number(x):
        return False
    return math.isfinite(float(x))


def _parse_iso(ts: Any) -> bool:
    if ts is None:
        return False
    if isinstance(ts, datetime):
        return True
    if hasattr(ts, "isoformat"):
        try:
            ts = ts.isoformat()
        except Exception:
            return False
    if not isinstance(ts, str) or not ts:
        return False
    try:
        datetime.fromisoformat(ts)
        return True
    except ValueError:
        return False


@dataclass
class Issue:
    code: str
    path: Optional[str] = None


def _iter_json_paths(obj: Any, prefix: str = "") -> Iterable[Tuple[str, str]]:
    if obj is None:
        yield (prefix or "$", "null")
        return
    if isinstance(obj, bool):
        yield (prefix or "$", "bool")
        return
    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        yield (prefix or "$", "number")
        return
    if isinstance(obj, str):
        yield (prefix or "$", "str")
        return
    if isinstance(obj, dict):
        yield (prefix or "$", "dict")
        for k, v in obj.items():
            key = k if isinstance(k, str) else f"<non-str-key:{type(k).__name__}>"
            child = f"{prefix}.{key}" if prefix else key
            yield from _iter_json_paths(v, child)
        return
    if isinstance(obj, list):
        yield (prefix or "$", "list")
        for i, v in enumerate(obj):
            child = f"{prefix}[{i}]" if prefix else f"[{i}]"
            yield from _iter_json_paths(v, child)
        return
    yield (prefix or "$", f"other:{type(obj).__name__}")


def _json_shape_signature(obj: Any) -> Dict[str, str]:
    # Normalize list indices so shape checks don't fail on varying list lengths.
    signature: Dict[str, str] = {}
    for path, kind in _iter_json_paths(obj):
        normalized_path = re.sub(r"\[\d+\]", "[]", path)
        signature[normalized_path] = kind
    return signature


def _validate_json_like(obj: Any, *, prefix: str, strict_floats: bool) -> List[Issue]:
    issues: List[Issue] = []

    for path, kind in _iter_json_paths(obj, prefix=prefix):
        if kind.startswith("other:"):
            issues.append(Issue("INVALID_JSON_TYPE", path))
            continue
        if kind == "dict":
            cur = _get_path({"_": obj}, f"_.{path}" if path else "_")
            if isinstance(cur, dict):
                for k in cur.keys():
                    if not isinstance(k, str):
                        issues.append(Issue("NON_STRING_JSON_KEY", path))
                        break

    if strict_floats:
        stack: List[Tuple[str, Any]] = [(prefix, obj)]
        while stack:
            p, cur = stack.pop()
            if cur is None or isinstance(cur, (str, bool)):
                continue
            if isinstance(cur, (int, float)) and not isinstance(cur, bool):
                if not _is_finite_number(cur):
                    issues.append(Issue("NON_FINITE_NUMBER", p))
                continue
            if isinstance(cur, dict):
                for k, v in cur.items():
                    key = k if isinstance(k, str) else f"<non-str-key:{type(k).__name__}>"
                    child = f"{p}.{key}" if p else key
                    stack.append((child, v))
                continue
            if isinstance(cur, list):
                for i, v in enumerate(cur):
                    child = f"{p}[{i}]" if p else f"[{i}]"
                    stack.append((child, v))
                continue

    return issues


def _validate_row(
    row: Dict[str, Any],
    *,
    full_json: bool,
    strict_floats: bool,
    baseline_shape: Optional[Dict[str, str]],
) -> Tuple[List[Issue], Optional[Dict[str, str]]]:
    issues: List[Issue] = []

    if not _is_number(row.get("ts")):
        issues.append(Issue("INVALID_TS_COLUMN", "ts"))

    if not _parse_iso(row.get("timestamp")):
        issues.append(Issue("INVALID_TIMESTAMP_ISO", "timestamp"))

    if not isinstance(row.get("ticker"), str) or not row.get("ticker"):
        issues.append(Issue("INVALID_TICKER", "ticker"))

    for top in ("feed", "state", "derived"):
        if row.get(top) is None:
            issues.append(Issue("MISSING_TOPLEVEL", top))
        elif not isinstance(row.get(top), dict):
            issues.append(Issue("INVALID_TOPLEVEL_TYPE", top))

    state = row.get("state") if isinstance(row.get("state"), dict) else None
    feed = row.get("feed") if isinstance(row.get("feed"), dict) else None
    derived = row.get("derived") if isinstance(row.get("derived"), dict) else None
    snapshot_like = {"state": state, "feed": feed, "derived": derived}

    for p in CRITICAL_PHYSICAL_PATHS:
        val = _get_path(snapshot_like, p)
        if val is None:
            issues.append(Issue("MISSING_CRITICAL_PATH", p))
        elif not _is_number(val):
            issues.append(Issue("INVALID_CRITICAL_TYPE", p))

    if full_json:
        for top in ("feed", "state", "derived"):
            obj = row.get(top)
            issues.extend(_validate_json_like(obj, prefix=top, strict_floats=strict_floats))

    next_baseline = baseline_shape
    if full_json and baseline_shape is not None:
        current_shape = _json_shape_signature(snapshot_like)
        if current_shape != baseline_shape:
            issues.append(Issue("JSON_SHAPE_MISMATCH", "snapshot_like"))
    elif full_json and baseline_shape is None:
        next_baseline = _json_shape_signature(snapshot_like)

    return issues, next_baseline


def _iter_parquet_files(base: Path, ticker: Optional[str], date: Optional[str]) -> List[Path]:
    root = base
    if ticker:
        root = root / f"ticker={ticker}"
    if date:
        root = root / f"date={date}"

    if not root.exists():
        raise SystemExit(f"Parquet path not found: {root}")

    files = sorted(root.rglob("*.parquet"))
    if not files:
        raise SystemExit(f"No parquet files under: {root}")
    return files


def _scan_rows(
    files: List[Path],
    *,
    limit: Optional[int],
    batch_size: int,
) -> Iterable[Dict[str, Any]]:
    try:
        import pyarrow.dataset as ds  # type: ignore
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Missing dependency: pyarrow. Install requirements and re-run, e.g. "
            "`pip install -r requirements.txt`."
        ) from exc

    dataset = ds.dataset(files, format="parquet")
    scanner = dataset.scanner(batch_size=batch_size)

    yielded = 0
    for batch in scanner.to_batches():
        for row in batch.to_pylist():
            yield row
            yielded += 1
            if limit is not None and yielded >= limit:
                return


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    # Handles pandas.Timestamp, datetime, numpy scalars, pyarrow scalars, etc.
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate snapshot parquet dataset structure (read-only)."
    )
    parser.add_argument(
        "--parquet-base",
        default="data/raw/ticker=WDOFUT_F_0",
        help="Dataset base dir (default: dataset_wdofut).",
    )
    parser.add_argument("--ticker", help="Ticker partition, e.g. WDOFUT_F_0.")
    parser.add_argument("--date", help="Date partition YYYY-MM-DD.")
    parser.add_argument("--limit", type=int, help="Max rows to scan (default: all).")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=2048,
        help="Arrow scan batch size (default: 2048).",
    )
    parser.add_argument(
        "--max-sample-issues",
        type=int,
        default=20,
        help="Max issue samples to print (default: 20).",
    )
    parser.add_argument(
        "--full-json",
        action="store_true",
        help="Also validate that feed/state/derived are fully JSON-like and optionally check shape drift.",
    )
    parser.add_argument(
        "--strict-floats",
        action="store_true",
        help="When --full-json is enabled, also flag NaN/Inf numbers inside feed/state/derived.",
    )
    parser.add_argument(
        "--enforce-shape",
        action="store_true",
        help="When --full-json is enabled, compute baseline JSON shape from the first row and flag any drift.",
    )
    parser.add_argument(
        "--show-examples",
        action="store_true",
        help="Print usage examples and exit.",
    )
    args = parser.parse_args()

    if args.show_examples:
        print(
            "python3 scripts/parquet_remount_validate.py "
            "--parquet-base dataset_wdofut --ticker WDOFUT_F_0 --date 2026-01-06 --limit 1000"
        )
        print(
            "python3 scripts/parquet_remount_validate.py "
            "--parquet-base dataset_wdofut --ticker WDOFUT_F_0 --date 2026-01-06 "
            "--full-json --strict-floats --enforce-shape"
        )
        return 0

    base = Path(args.parquet_base)
    files = _iter_parquet_files(base, args.ticker, args.date)

    totals: Dict[str, int] = {}
    sampled: List[Dict[str, Any]] = []
    rows = 0
    baseline_shape: Optional[Dict[str, str]] = None

    for row in _scan_rows(files, limit=args.limit, batch_size=args.batch_size):
        rows += 1
        issues, baseline_shape = _validate_row(
            row,
            full_json=bool(args.full_json),
            strict_floats=bool(args.strict_floats),
            baseline_shape=baseline_shape if args.enforce_shape else None,
        )

        if not issues:
            continue

        for issue in issues:
            key = f"{issue.code}:{issue.path}" if issue.path else issue.code
            totals[key] = totals.get(key, 0) + 1

        if len(sampled) < args.max_sample_issues:
            sampled.append(
                {
                    "ts": _json_safe(row.get("ts")),
                    "timestamp": _json_safe(row.get("timestamp")),
                    "ticker": _json_safe(row.get("ticker")),
                    "issues": [{"code": i.code, "path": i.path} for i in issues],
                }
            )

    report = {
        "parquet_base": str(base),
        "ticker": args.ticker,
        "date": args.date,
        "rows_scanned": rows,
        "issue_counts": dict(sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))),
        "issue_samples": sampled,
        "critical_physical_paths": list(CRITICAL_PHYSICAL_PATHS),
        "full_json": bool(args.full_json),
        "strict_floats": bool(args.strict_floats),
        "enforce_shape": bool(args.enforce_shape),
    }

    print(json.dumps(_json_safe(report), ensure_ascii=False, indent=2))

    return 1 if totals else 0


if __name__ == "__main__":
    raise SystemExit(main())
