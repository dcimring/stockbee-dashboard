"""Ingest daily OHLCV into the prices table (idempotent upserts).

Usage:
  uv run python -m pipeline.ingest --tickers AAPL,MSFT --start 2024-01-01
  uv run python -m pipeline.ingest --universe --start 2024-01-01   # paid plan
"""

import argparse
import sys
import time

from dotenv import load_dotenv

from . import db
from .providers import tiingo

load_dotenv()

UPSERT = """
INSERT INTO prices (ticker, date, open, high, low, close, volume,
                    adj_open, adj_high, adj_low, adj_close)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(ticker, date) DO UPDATE SET
  open=excluded.open, high=excluded.high, low=excluded.low,
  close=excluded.close, volume=excluded.volume,
  adj_open=excluded.adj_open, adj_high=excluded.adj_high,
  adj_low=excluded.adj_low, adj_close=excluded.adj_close
"""


def ingest_ticker(conn, ticker: str, start: str, end: str | None = None) -> int:
    df = tiingo.fetch_daily(ticker, start, end)
    if df.empty:
        return 0
    conn.executemany(UPSERT, df.itertuples(index=False))
    conn.commit()
    return len(df)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", help="comma-separated list")
    ap.add_argument("--universe", action="store_true", help="all symbols in DB")
    ap.add_argument("--start", required=True)
    ap.add_argument("--end")
    ap.add_argument("--sleep", type=float, default=0.1, help="seconds between requests")
    args = ap.parse_args()

    conn = db.connect()
    if args.universe:
        tickers = [r[0] for r in conn.execute("SELECT ticker FROM symbols WHERE active=1")]
    elif args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    else:
        ap.error("need --tickers or --universe")

    total = 0
    for i, t in enumerate(tickers, 1):
        try:
            n = ingest_ticker(conn, t, args.start, args.end)
        except Exception as e:  # keep going; report at end
            print(f"{t}: ERROR {e}", file=sys.stderr)
            continue
        total += n
        print(f"[{i}/{len(tickers)}] {t}: {n} rows")
        time.sleep(args.sleep)
    print(f"done: {total} rows upserted")


if __name__ == "__main__":
    main()
