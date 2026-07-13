"""SQLite connection and schema."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "stockbee.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS symbols (
  ticker TEXT PRIMARY KEY,
  name TEXT,
  exchange TEXT,
  type TEXT,
  active INTEGER DEFAULT 1,
  first_seen DATE,
  last_seen DATE,
  sector TEXT,
  industry TEXT,
  country TEXT,
  ipo_year INTEGER
);

CREATE TABLE IF NOT EXISTS prices (
  ticker TEXT,
  date DATE,
  open REAL, high REAL, low REAL, close REAL,
  volume INTEGER,
  adj_open REAL, adj_high REAL, adj_low REAL, adj_close REAL,
  PRIMARY KEY (ticker, date)
);
CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date);

CREATE TABLE IF NOT EXISTS breadth_daily (
  date DATE PRIMARY KEY,
  up4 INTEGER, down4 INTEGER,
  ratio5 REAL, ratio10 REAL,
  up25q INTEGER, down25q INTEGER,
  up13_34 INTEGER, down13_34 INTEGER,
  t2108 REAL,
  universe_count INTEGER
);

CREATE TABLE IF NOT EXISTS earnings (
  ticker TEXT,
  date DATE,               -- report date
  time TEXT,               -- 'bmo' | 'amc' | NULL (not supplied)
  eps_actual REAL,
  eps_forecast REAL,
  surprise_pct REAL,
  PRIMARY KEY (ticker, date)
);
CREATE INDEX IF NOT EXISTS idx_earnings_date ON earnings(date);

CREATE TABLE IF NOT EXISTS scan_results (
  date DATE,
  scan TEXT,
  ticker TEXT,
  metrics TEXT,
  PRIMARY KEY (date, scan, ticker)
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.executescript(SCHEMA)
    # migrations for databases created before these columns existed
    cols = {r[1] for r in conn.execute("PRAGMA table_info(symbols)")}
    for col, typ in (
        ("sector", "TEXT"), ("industry", "TEXT"),
        ("country", "TEXT"), ("ipo_year", "INTEGER"),
    ):
        if col not in cols:
            conn.execute(f"ALTER TABLE symbols ADD COLUMN {col} {typ}")
    return conn
