"""Regime classification from Market Monitor breadth.

Buckets: aggressive / normal / defensive / stand_aside.
Two ways in to 'aggressive': washed-out breadth turning up (contrarian
bounce) or healthy breadth with rising ratios (trend participation).

Thresholds are tuned against forward SPY returns — see backtest_regime.py.
"""

import pandas as pd
import numpy as np

# Tuned 2026-07-12 against forward SPY returns over 861 days of breadth
# history (see backtest_regime.py): spread aggressive-vs-stand_aside fwd10
# improved from 0.04pp (old values) to 0.40pp; trend_days=3 and washout_t=25
# were the consistent winners across the grid. Re-tune after the dataset
# includes a real bear phase.
DEFAULTS = {
    "washout_r5": 0.5,   # 5d ratio below this = washed out (contrarian bullish)
    "washout_t": 25,     # T2108 below this = washed out
    "strong_r5": 1.1,    # 5d ratio at/above this = breakouts lead
    "defensive_r5": 0.7, # between this and strong = deteriorating
    "overbought_t": 80,  # T2108 above this = froth, cap aggressiveness
    "trend_days": 3,     # ratio5 rising = above its value this many days ago
}

REGIMES = ["aggressive", "normal", "defensive", "stand_aside"]


def classify(df: pd.DataFrame, **overrides) -> pd.Series:
    """Vectorized regime per row. df: chronological breadth_daily frame
    with ratio5, t2108 columns."""
    p = {**DEFAULTS, **overrides}
    r5 = df["ratio5"]
    t = df["t2108"]
    rising = r5 > r5.shift(p["trend_days"])

    washout_turn = ((r5 < p["washout_r5"]) | (t < p["washout_t"])) & rising
    healthy = (r5 >= p["strong_r5"]) & rising & (t <= p["overbought_t"])
    positive = r5 >= p["strong_r5"]
    fading = r5 >= p["defensive_r5"]

    return pd.Series(
        np.select(
            [washout_turn, healthy, positive, fading],
            ["aggressive", "aggressive", "normal", "defensive"],
            default="stand_aside",
        ),
        index=df.index,
    )


def rationale(row: dict, regime: str) -> str:
    r5, t = row["ratio5"], row["t2108"]
    if regime == "aggressive":
        if r5 < DEFAULTS["washout_r5"] or t < DEFAULTS["washout_t"]:
            return "washed-out breadth turning up — contrarian buy zone"
        return "healthy breadth, ratios rising"
    if regime == "normal":
        return "breakouts leading but momentum flat"
    if regime == "defensive":
        return "breakdowns gaining on breakouts"
    return "breakdowns dominating"
