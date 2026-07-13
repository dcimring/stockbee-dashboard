"""Backtest regime rules against forward SPY returns.

For each historical day, classify the regime from breadth and measure SPY's
return over the next 5/10/20 trading days. A good regime dial shows
monotonic separation: aggressive > normal > defensive > stand_aside.

Usage:
  uv run python -m pipeline.backtest_regime            # evaluate defaults
  uv run python -m pipeline.backtest_regime --grid     # small threshold grid
"""

import argparse
import itertools

import pandas as pd

from . import db, regime


def load(conn) -> pd.DataFrame:
    b = pd.read_sql("SELECT * FROM breadth_daily ORDER BY date", conn)
    spy = pd.read_sql(
        "SELECT date, adj_close FROM prices WHERE ticker='SPY' ORDER BY date", conn
    )
    df = b.merge(spy, on="date", how="inner")
    for n in (5, 10, 20):
        df[f"fwd{n}"] = df["adj_close"].shift(-n) / df["adj_close"] - 1
    return df


def evaluate(df: pd.DataFrame, **params) -> pd.DataFrame:
    reg = regime.classify(df, **params)
    out = df.assign(regime=reg).dropna(subset=["fwd20"])
    g = out.groupby("regime")
    stats = pd.DataFrame(
        {
            "days": g.size(),
            "pct_of_time": (g.size() / len(out) * 100).round(1),
            "fwd5_mean": (g["fwd5"].mean() * 100).round(2),
            "fwd10_mean": (g["fwd10"].mean() * 100).round(2),
            "fwd20_mean": (g["fwd20"].mean() * 100).round(2),
            "fwd10_win%": (g["fwd10"].apply(lambda s: (s > 0).mean()) * 100).round(1),
        }
    )
    return stats.reindex(regime.REGIMES)


def spread(stats: pd.DataFrame) -> float:
    """Separation score: aggressive minus stand_aside forward 10d return."""
    try:
        return stats.loc["aggressive", "fwd10_mean"] - stats.loc["stand_aside", "fwd10_mean"]
    except KeyError:
        return float("nan")


GRID = {
    "washout_r5": [0.4, 0.5, 0.6],
    "washout_t": [20, 25],
    "strong_r5": [1.0, 1.1],
    "defensive_r5": [0.7, 0.8],
    "trend_days": [1, 3, 5],
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", action="store_true")
    args = ap.parse_args()

    conn = db.connect()
    df = load(conn)
    print(f"days with breadth + SPY + forward returns: {len(df.dropna(subset=['fwd20']))}\n")

    print("=== current defaults ===")
    base = evaluate(df)
    print(base.to_string(), f"\nspread (aggr - stand, fwd10): {spread(base):.2f}pp\n")

    if not args.grid:
        return

    rows = []
    keys = list(GRID)
    for combo in itertools.product(*GRID.values()):
        params = dict(zip(keys, combo))
        stats = evaluate(df, **params)
        counts = stats["days"].fillna(0)
        # require every bucket to occur at least 5% of the time (no degenerate rules)
        if counts.min() < 0.05 * counts.sum():
            continue
        rows.append({**params, "spread": spread(stats),
                     "aggr_fwd10": stats.loc["aggressive", "fwd10_mean"],
                     "stand_fwd10": stats.loc["stand_aside", "fwd10_mean"]})
    res = pd.DataFrame(rows).sort_values("spread", ascending=False)
    print("=== top 10 by spread (all buckets >= 5% of days) ===")
    print(res.head(10).to_string(index=False))
    print("\n=== bottom 3 ===")
    print(res.tail(3).to_string(index=False))


if __name__ == "__main__":
    main()
