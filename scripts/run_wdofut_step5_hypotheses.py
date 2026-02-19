#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd


@dataclass
class Hypothesis:
    id: str
    name: str
    rationale: str
    expected_regime: str
    signal_fn: Callable[[pd.DataFrame], np.ndarray]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Step 5: generate and score 10 rule-based edge hypotheses."
    )
    parser.add_argument(
        "--input-parquet",
        default="./data/wdofut_prepared/wdofut_features_v1.parquet",
        help="Feature parquet path from Step 4.",
    )
    parser.add_argument(
        "--cost-per-trade",
        type=float,
        default=0.0,
        help="Flat cost per non-zero signal trade.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="How many hypotheses to keep as top candidates (default: 3).",
    )
    parser.add_argument(
        "--output-root",
        default="./experiments",
        help="Base experiments folder (default: ./experiments).",
    )
    parser.add_argument("--z-upper-quantile", type=float, default=0.95, help="Upper quantile for zret_20 extremes.")
    parser.add_argument("--z-lower-quantile", type=float, default=0.05, help="Lower quantile for zret_20 extremes.")
    parser.add_argument("--spread-upper-quantile", type=float, default=0.95, help="Upper quantile for spread_z_20 extremes.")
    parser.add_argument("--spread-lower-quantile", type=float, default=0.05, help="Lower quantile for spread_z_20 extremes.")
    parser.add_argument("--vol-regime-upper-quantile", type=float, default=0.85, help="Upper quantile for vol_regime_20_over_60 high-vol regime.")
    parser.add_argument("--vol-regime-lower-quantile", type=float, default=0.15, help="Lower quantile for vol_regime_20_over_60 low-vol regime.")
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


def evaluate(signal: np.ndarray, y: np.ndarray, cost_per_trade: float) -> dict[str, Any]:
    traded = signal != 0
    pnl = signal * y - traded.astype(float) * cost_per_trade
    gross_profit = pnl[pnl > 0].sum()
    gross_loss = -pnl[pnl < 0].sum()
    pf = float(gross_profit / gross_loss) if gross_loss > 0 else (float("inf") if gross_profit > 0 else 0.0)
    trade_count = int(traded.sum())
    hit_rate = float((pnl[traded] > 0).mean()) if trade_count else 0.0
    return {
        "rows": int(len(y)),
        "trades": trade_count,
        "net_pnl": float(pnl.sum()),
        "profit_factor": pf,
        "hit_rate": hit_rate,
        "avg_pnl_per_trade": float(pnl[traded].mean()) if trade_count else 0.0,
    }


def q(series: pd.Series, p: float) -> float:
    return float(series.quantile(p))


def build_hypotheses(
    df: pd.DataFrame,
    *,
    z_upper_q: float,
    z_lower_q: float,
    spread_upper_q: float,
    spread_lower_q: float,
    vol_upper_q: float,
    vol_lower_q: float,
) -> list[Hypothesis]:
    # Precompute thresholds on train-compatible full sample snapshot;
    # selection/ranking still happens on temporal val/test splits.
    z95 = q(df["zret_20"].dropna(), z_upper_q)
    z05 = q(df["zret_20"].dropna(), z_lower_q)
    s95 = q(df["spread_z_20"].dropna(), spread_upper_q)
    s05 = q(df["spread_z_20"].dropna(), spread_lower_q)
    vr85 = q(df["vol_regime_20_over_60"].dropna(), vol_upper_q)
    vr15 = q(df["vol_regime_20_over_60"].dropna(), vol_lower_q)

    def sign(x: pd.Series) -> np.ndarray:
        return np.sign(x.fillna(0.0)).to_numpy(dtype=float)

    hs: list[Hypothesis] = [
        Hypothesis(
            "H01",
            "Short after positive extreme z-score",
            "Micro mean-reversion after stretched short-term move.",
            "High intrabar displacement without sustained follow-through.",
            lambda d: np.where(d["zret_20"] >= z95, -1.0, 0.0),
        ),
        Hypothesis(
            "H02",
            "Long after negative extreme z-score",
            "Symmetric mean-reversion for downside stretch.",
            "Short-lived panic downticks.",
            lambda d: np.where(d["zret_20"] <= z05, 1.0, 0.0),
        ),
        Hypothesis(
            "H03",
            "Momentum on 20-step return in calm regime",
            "Short-horizon continuation under low vol regime.",
            "Low-to-moderate volatility periods.",
            lambda d: np.where(
                d["vol_regime_20_over_60"] <= vr15,
                np.sign(d["ret_sum_20"]).astype(float),
                0.0,
            ),
        ),
        Hypothesis(
            "H04",
            "Contrarian on 20-step return in high-vol regime",
            "Reversal bias when volatility regime is elevated.",
            "High-volatility bursts.",
            lambda d: np.where(
                d["vol_regime_20_over_60"] >= vr85,
                -np.sign(d["ret_sum_20"]).astype(float),
                0.0,
            ),
        ),
        Hypothesis(
            "H05",
            "Short when spread shock is extreme wide",
            "Liquidity stress often coincides with adverse short-term drift.",
            "Spread expansion events.",
            lambda d: np.where(d["spread_z_20"] >= s95, -1.0, 0.0),
        ),
        Hypothesis(
            "H06",
            "Long when spread is unusually compressed",
            "Tighter spread can favor continuation with lower friction.",
            "High-liquidity micro regime.",
            lambda d: np.where(d["spread_z_20"] <= s05, 1.0, 0.0),
        ),
        Hypothesis(
            "H07",
            "Momentum on ret_sum_10",
            "Simple continuation baseline at intermediate lookback.",
            "Directional short-term flow.",
            lambda d: sign(d["ret_sum_10"]),
        ),
        Hypothesis(
            "H08",
            "Contrarian on ret_sum_5",
            "Quick mean-reversion at very short lookback.",
            "Choppy microstructure periods.",
            lambda d: -sign(d["ret_sum_5"]),
        ),
        Hypothesis(
            "H09",
            "Trade only when spread_delta compresses + momentum confirms",
            "Spread compression plus directional move may indicate clean impulse.",
            "Compression-to-move transitions.",
            lambda d: np.where(
                d["spread_delta1"] < 0,
                np.sign(d["ret_lag1"]).astype(float),
                0.0,
            ),
        ),
        Hypothesis(
            "H10",
            "Volatility breakout continuation",
            "When vol_20 exceeds vol_60 and lag return aligns, follow move.",
            "Volatility expansion with directional impulse.",
            lambda d: np.where(
                (d["vol_20"] > d["vol_60"]) & (d["ret_lag1"] != 0),
                np.sign(d["ret_lag1"]).astype(float),
                0.0,
            ),
        ),
    ]
    return hs


def main() -> int:
    args = parse_args()
    in_path = Path(args.input_parquet).expanduser().resolve()
    if not in_path.exists():
        raise SystemExit(f"Input parquet not found: {in_path}")

    df = pd.read_parquet(in_path)
    required = {"timestamp", "y_tb", "ret_lag1", "ret_sum_5", "ret_sum_10", "ret_sum_20", "vol_20", "vol_60", "zret_20", "spread_z_20", "spread_delta1", "vol_regime_20_over_60"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp", "y_tb"]).sort_values("timestamp").reset_index(drop=True)
    splits = split_temporal(df)
    hypotheses = build_hypotheses(
        df,
        z_upper_q=args.z_upper_quantile,
        z_lower_q=args.z_lower_quantile,
        spread_upper_q=args.spread_upper_quantile,
        spread_lower_q=args.spread_lower_quantile,
        vol_upper_q=args.vol_regime_upper_quantile,
        vol_lower_q=args.vol_regime_lower_quantile,
    )

    scored: list[dict[str, Any]] = []
    for h in hypotheses:
        item: dict[str, Any] = {
            "id": h.id,
            "name": h.name,
            "rationale": h.rationale,
            "expected_regime": h.expected_regime,
            "metrics": {},
        }
        for sname, sdf in splits.items():
            sig = h.signal_fn(sdf)
            y = sdf["y_tb"].to_numpy(dtype=float)
            item["metrics"][sname] = evaluate(sig, y, args.cost_per_trade)
        # ranking objective focused on validation robustness
        val = item["metrics"]["val"]
        item["rank_score"] = float(val["net_pnl"] * (val["profit_factor"] if np.isfinite(val["profit_factor"]) else 1.0))
        scored.append(item)

    scored.sort(key=lambda x: x["rank_score"], reverse=True)
    top = scored[: args.top_k]

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    exp_dir = Path(args.output_root).expanduser().resolve() / f"{ts}_step5_hypotheses"
    exp_dir.mkdir(parents=True, exist_ok=True)

    full_path = exp_dir / "hypotheses_full.json"
    top_path = exp_dir / "candidates_top3.json"
    md_path = exp_dir / "hypotheses.md"

    payload = {
        "input_parquet": str(in_path),
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
        "hypotheses": scored,
    }
    full_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    top_path.write_text(json.dumps(top, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Step 5 Hypotheses",
        "",
        f"- Input: `{in_path}`",
        f"- Cost per trade: `{args.cost_per_trade}`",
        f"- Thresholds: z=({args.z_lower_quantile:.2f},{args.z_upper_quantile:.2f}), spread=({args.spread_lower_quantile:.2f},{args.spread_upper_quantile:.2f}), vol_regime=({args.vol_regime_lower_quantile:.2f},{args.vol_regime_upper_quantile:.2f})",
        f"- Top-K selected: `{args.top_k}`",
        "",
        "## Top Candidates",
        "",
    ]
    for i, h in enumerate(top, start=1):
        lines.extend(
            [
                f"### {i}. {h['id']} — {h['name']}",
                f"- Rationale: {h['rationale']}",
                f"- Expected regime: {h['expected_regime']}",
                f"- Validation net_pnl: {h['metrics']['val']['net_pnl']}",
                f"- Validation profit_factor: {h['metrics']['val']['profit_factor']}",
                f"- Validation hit_rate: {h['metrics']['val']['hit_rate']}",
                f"- Test net_pnl: {h['metrics']['test']['net_pnl']}",
                f"- Test profit_factor: {h['metrics']['test']['profit_factor']}",
                f"- Test hit_rate: {h['metrics']['test']['hit_rate']}",
                "",
            ]
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")

    result = {
        "experiment_dir": str(exp_dir),
        "full_hypotheses_json": str(full_path),
        "top_candidates_json": str(top_path),
        "summary_markdown": str(md_path),
        "top_candidates": [{"id": h["id"], "name": h["name"]} for h in top],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
