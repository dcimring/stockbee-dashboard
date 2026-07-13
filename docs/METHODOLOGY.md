# The Stockbee Methodology

Pradeep Bonde (@PradeepBonde on X, known as **Stockbee**) is a veteran swing trader who has run [stockbee.blogspot.com](https://stockbee.blogspot.com) and a members-only community for ~20 years. He mentored several well-known momentum traders (including Kristjan Kullamägi) and was featured in *The Stocktwits Edge* for his Trend Intensity breakout setup.

His approach is deliberately **process-based**: a small number of mechanical scans run daily, filtered by market breadth, with tight risk rules. Market breadth determines *how aggressively* to act on setup signals.

---

## 1. Market Monitor (market-timing layer)

A daily breadth table built from counting stocks making significant moves across the whole US common-stock universe. This is the heart of the system.

### Indicators

| Indicator | Definition | Interpretation |
|---|---|---|
| **4% breakouts (daily)** | Count of stocks closing up ≥ 4% on the day, on volume | Primary daily buying-pressure reading |
| **4% breakdowns (daily)** | Count of stocks closing down ≥ 4% on the day | Primary daily selling-pressure reading |
| **5-day ratio** | Sum of last 5 days' 4% breakouts ÷ sum of last 5 days' 4% breakdowns | < 0.5 = extreme bearishness (contrarian **bullish**); > 2.0 = strength |
| **10-day ratio** | Same, over 10 days | Same thresholds, slower signal |
| **25% up in a quarter** | Count of stocks up ≥ 25% over 65 trading days | Below ~200–300 = washed-out market, good time to buy |
| **25% down in a quarter** | Count of stocks down ≥ 25% over 65 trading days | Complements the above |
| **13% up/down in 34 days** | Medium-term counterpart of the quarterly counts | Trend confirmation |
| **T2108** | % of stocks above their 40-day simple moving average | < 20 = bottoming zone; > 80 = overbought, pullback likely |

### Interpretation rules

- **Extremely bearish breadth is bullish** — signals the start of a bounce or bottom.
- **Short-term extremely bullish breadth precedes pullbacks.**
- Look at the **total picture**, not individual indicators in isolation.
- Watch for **breadth thrusts** (sudden expansion in 4% breakouts off a low) and **divergences** (price making highs while breadth deteriorates).

---

## 2. Momentum Bursts (bread-and-butter trade)

Stocks move in short bursts of 3–5 days gaining 8–20%+. The edge is entering on **day one** of range expansion, not chasing.

### Scan

```
close >= 1.04 * prior_close
AND volume > prior_day_volume
```

A companion **$-breakout** variant uses a dollar move instead of a percentage for higher-priced stocks (e.g. "up $5+ or 8%+ in 5 days" family of scans).

### Qualitative filters (his daily ritual checks)

- Stock closes **near or at its high** on the breakout day.
- **3–20 days of consolidation** immediately prior.
- **Not up 3+ consecutive days** before the breakout.
- Young trend preferred (first or second breakout in a trend, not the fifth).
- Low-volume, orderly pullback/base before the move.

### Trade management

- Enter on the first day of the burst.
- Exit within **3–5 days**, or immediately if loss exceeds ~8%.

---

## 3. Anticipation Setups

Instead of chasing breakouts, find stocks *about* to break out: established momentum currently in a quiet, contracted phase.

### Scans (TC2000-style, from community writeups)

| Name | Formula | Plus |
|---|---|---|
| **Double Trouble** | `c / minl252 >= 1.8 AND minv3.1 >= 100000` | today's move within ±1% |
| **TI65 1% Mover** | `avgc7 / avgc65 > 1.05 AND minv3.1 > 100000` | today's move within ±1% |
| **MDT** | `c / avgc126 > 1.19 AND minv3.1 > 100000` | today's move within ±1% |

(`minl252` = 252-day low; `avgc7/avgc65` is his **Trend Intensity 65** ratio; `minv3.1` = minimum volume over last 3 days.)

### Setup criteria

- Series of **narrow-range days**; low volume and volatility.
- Orderly pullback or flat base, no consecutive big up days.
- Enter on the day the range expands (i.e. when it becomes a momentum burst).

---

## 4. Episodic Pivots (the big-money trade)

A **catalyst** forces the market to re-rate a stock: earnings blowout, guidance raise, FDA approval, major contract, M&A. These can run 20–50%+ over weeks, unlike the 3–5 day bursts.

### Signature

- **10%+ gap** (or 4%+ move at minimum) on **2x+ average volume**.
- Ideally a **neglected** name — limited analyst/media coverage, hasn't moved in months.
- **"9 million share EPs"**: one-day volume of 9M+ shares marks massive institutional interest.

### Example scan forms (from community writeups)

```
(c/c1 > 1.04 OR c/c1 < 0.96) AND v > 3 * avg50_volume AND c >= 3 AND v >= 300000
(100 * (c - c1) / c1) >= 20 AND v > 10000 AND c >= 5      -- big % gainers
(c - c1) >= 5 AND v > 10000 AND c >= 5                     -- big $ gainers
```

### Catalyst checklist

Earnings acceleration, new contracts, product launches, sector momentum, biotech approvals, insider buying > $1M, first-time institutional recognition.

---

## 5. Risk & sizing rules

- Very small risk per trade (he has described **~0.25% of account risk** per trade).
- **Zero leverage.**
- Cut momentum-burst losers fast (time stop of 3–5 days; hard stop ~8%).
- **Scale aggressiveness with breadth**: size up when Market Monitor is healthy, stand aside when it deteriorates.

---

## Sources

- [Stockbee: Market Monitor (MM)](https://stockbee.blogspot.com/p/mm.html)
- [Stockbee: How to use market breadth to avoid market crashes](https://stockbee.blogspot.com/2011/08/how-to-use-market-breadth-to-avoid.html)
- [Systems, Setups & Process of Swing Trading from @stockbee (Substack)](https://tikamalma.substack.com/p/systems-setups-and-process-of-swing)
- [TraderLion podcast: Pradeep Bonde on Episodic Pivots](https://traderlion.com/podcast/pradeep-bonde-episodic-pivots/)
- [Trends and Breakouts: Stockbee's process-based approach](https://trendsandbreakouts.com/stockbee)
- [Deepvue: Pradeep Bonde's screens](https://deepvue.com/screener/pradeep-bonde-screens/)
- [The Trend Intensity Breakout Setup — The Stocktwits Edge (Wiley)](https://onlinelibrary.wiley.com/doi/10.1002/9781119202516.ch26)

> **Accuracy note:** exact Market Monitor columns and scan nuances live behind the paid Stockbee membership. Treat third-party formulas above as best-effort reconstructions; verify against his posted TC2000 codes if/when a membership is available.
