# Architecture

## Stack

- **Language:** Python 3.12+
- **Storage:** SQLite (single file, zero ops; revisit DuckDB/Postgres only if it becomes a bottleneck)
- **Pipeline:** nightly job — EOD data pull → breadth calculations → scan runs → results written to SQLite
- **Frontend:** web app reading from SQLite. Start with **FastAPI + a lightweight JS frontend** (or Streamlit for the very first iteration if we want panels on screen fastest); charting via Plotly or lightweight-charts.
- **Scheduling:** cron/launchd on the local machine to start; portable to a small VPS later.

## Data flow

```
Tiingo (bulk backfill, paid)        Polygon free tier (later, daily grouped bars)
        \                                   /
         └──────────► ingest.py ◄──────────┘
                          │  upsert daily OHLCV
                          ▼
                     SQLite: prices
                          │
                    compute.py  (nightly, after close)
                          │  breadth counts, T2108, scan hits, quality metrics
                          ▼
        SQLite: breadth_daily, scan_results, regime
                          │
                          ▼
                  FastAPI backend ──► web dashboard (5 panels)
```

## Schema sketch

```sql
-- universe of tradable US common stocks (excludes ETFs, funds, warrants)
CREATE TABLE symbols (
  ticker TEXT PRIMARY KEY,
  name TEXT,
  exchange TEXT,
  type TEXT,            -- common stock filter
  active INTEGER,
  first_seen DATE,
  last_seen DATE
);

CREATE TABLE prices (
  ticker TEXT,
  date DATE,
  open REAL, high REAL, low REAL, close REAL,
  volume INTEGER,
  adj_close REAL,        -- keep both raw and adjusted; breadth uses split-adjusted
  PRIMARY KEY (ticker, date)
);

CREATE TABLE breadth_daily (
  date DATE PRIMARY KEY,
  up4 INTEGER, down4 INTEGER,
  ratio5 REAL, ratio10 REAL,
  up25q INTEGER, down25q INTEGER,      -- 65 trading days
  up13_34 INTEGER, down13_34 INTEGER,  -- 34 trading days
  t2108 REAL,                          -- % above 40-day SMA
  universe_count INTEGER
);

CREATE TABLE scan_results (
  date DATE,
  scan TEXT,             -- 'momentum_burst' | 'dollar_breakout' | 'anticipation_*' | 'ep'
  ticker TEXT,
  metrics JSON,          -- close-near-high %, consolidation days, gap %, rel volume, ...
  PRIMARY KEY (date, scan, ticker)
);

CREATE TABLE regime (
  date DATE PRIMARY KEY,
  regime TEXT,           -- aggressive | normal | defensive | stand_aside
  rationale JSON
);
```

## Design notes

- **Universe filtering matters.** Stockbee's counts are over US common stocks only — exclude ETFs, closed-end funds, warrants, units, preferreds. Also apply a minimum-volume floor (e.g. 100k shares) consistent with his scans, and record `universe_count` daily so ratios are comparable over time.
- **Corporate actions:** use split-adjusted prices for % moves; a 2:1 split must not register as a 50% breakdown. Tiingo's `adjClose` handles this; recompute affected history on new split events.
- **Idempotent ingest:** upserts keyed on (ticker, date) so re-running a day is safe; makes the Tiingo→Polygon switch a swap of the fetch layer only.
- **Backfill depth:** 2+ years minimum so 65-day windows, T2108, and the historical Market Monitor chart are populated from day one; more history is cheap and enables validating thresholds against known market bottoms/tops.
- **Compute is trivial at this scale** (~6,000 tickers × daily bars): pandas over SQLite is plenty; no need for anything heavier.

## Repo layout (planned)

```
stockbee/
  docs/                  # this documentation
  pipeline/
    ingest.py            # provider-agnostic fetch → prices table
    providers/
      tiingo.py
      polygon.py
    compute.py           # breadth, scans, regime
    universe.py          # symbol list maintenance & filtering
  app/
    main.py              # FastAPI
    static/ templates/
  data/
    stockbee.db          # SQLite (gitignored)
  pyproject.toml
```
