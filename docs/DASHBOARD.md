# Dashboard Specification

Five panels, all driven by the nightly EOD pipeline. End-of-day system first; intraday features are a later phase.

## 1. Market Monitor table

The daily breadth grid, one row per trading day (newest on top), color-coded against Stockbee's thresholds.

**Columns:** 4% breakouts, 4% breakdowns, 5-day ratio, 10-day ratio, 25%-in-quarter up, 25%-in-quarter down, 13%-in-34-days up/down, T2108 (% above 40-day MA).

**Color rules (initial):**
- 5d/10d ratio: red > 2.0 (overbought caution), green < 0.5 (contrarian buy zone)
- 25%-quarter up count: green when < 300 (washed out)
- T2108: green < 20, red > 80

**Plus:** a time-series chart of each column so breadth thrusts and divergences vs. the S&P 500 are visible at a glance.

## 2. Momentum Burst scanner

Nightly scan results: `close ≥ 1.04 × prior close AND volume > prior volume` (and the $-breakout variant).

Each hit is annotated with automated quality-filter columns so the ritual checks are pre-computed:
- Close-near-high % (`(close - low) / (high - low)`)
- Days of consolidation before the breakout (3–20 wanted)
- Consecutive up-days before the breakout (0–2 wanted)
- Extension from 10-day MA
- Breakout count in the current trend (young trend preferred)

Sortable/filterable table with mini sparkline charts; click-through to a full candlestick chart.

## 3. Anticipation watchlist

The three anticipation scans (Double Trouble, TI65 1% Mover, MDT — see [METHODOLOGY.md](METHODOLOGY.md)) surfacing momentum stocks in quiet contraction, ranked by range contraction (e.g. NR7 count, ATR percentile). These are tomorrow's momentum-burst candidates.

## 4. Episodic Pivot screen

EOD version first: yesterday's 10%+ gappers on 2x+ average volume, with neglect metrics (distance from 52-week high, months since last big move, average volume percentile) and 9M+ share volume flags. Joined with an earnings calendar when available. Pre-market/intraday scanning is phase 2.

## 5. Regime dial

A single "how aggressive should I be" indicator derived from Market Monitor readings:

| Regime | Example conditions (to be tuned) |
|---|---|
| **Aggressive** | 5d ratio rising through 1.0+ off a low reading; T2108 recovering from < 20 |
| **Normal** | Ratios 1.0–2.0, T2108 mid-range |
| **Defensive** | Ratios rolling over, breadth divergence vs. index highs |
| **Stand aside** | Breakdowns dominating; 5d ratio < 1 and falling with T2108 > 40 |

Shown as a banner across the top of every page, since sizing-with-breadth is the core of the method.
