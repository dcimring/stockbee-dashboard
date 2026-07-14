"""Daily update via Massive.com grouped bars: whole market, ~2 calls per day.

For each recent trading day, fetch raw + split-adjusted grouped bars, join,
and upsert rows for tickers in the active universe. Then detect splits in the
window and re-backfill those tickers' full history from Tiingo (fixing both
split and dividend adjustment across history).

Usage:
  uv run python -m pipeline.ingest_daily --days 14
"""

import argparse
import time
from datetime import date, timedelta

from dotenv import load_dotenv

from . import db
from .ingest import UPSERT, ingest_ticker
from .providers import polygon

load_dotenv()


def ingest_day(conn, day: str, active: set[str]) -> int:
    raw = polygon.grouped_daily(day, adjusted=False)
    if raw.empty:
        return 0  # holiday/weekend
    time.sleep(polygon.RATE_SLEEP)
    adj = polygon.grouped_daily(day, adjusted=True)
    merged = raw.merge(adj, on=["ticker", "date"], suffixes=("", "_adj"))
    merged = merged[merged["ticker"].isin(active)]
    rows = [
        (
            r.ticker, r.date, r.open, r.high, r.low, r.close, int(r.volume),
            r.open_adj, r.high_adj, r.low_adj, r.close_adj,
        )
        for r in merged.itertuples()
    ]
    conn.executemany(UPSERT, rows)
    conn.commit()
    return len(rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14, help="calendar days back")
    args = ap.parse_args()

    conn = db.connect()
    active = {r[0] for r in conn.execute("SELECT ticker FROM symbols WHERE active=1")}
    start = date.today() - timedelta(days=args.days)

    total = 0
    skipped = 0
    day = start
    while day <= date.today():
        if day.weekday() < 5:
            try:
                n = ingest_day(conn, day.isoformat(), active)
                print(f"{day}: {n} rows")
                total += n
            except Exception as e:
                # A recent day the free tier hasn't released yet returns 403;
                # the 14-day lookback backfills it on a later run. Never let one
                # day abort the whole ingest (and the compute step that follows).
                print(f"{day}: SKIPPED ({e})")
                skipped += 1
            time.sleep(polygon.RATE_SLEEP)
        day += timedelta(days=1)
    print(f"grouped ingest done: {total} rows, {skipped} day(s) skipped")

    try:
        split_tickers = [t for t in polygon.splits_since(start.isoformat()) if t in active]
        if split_tickers:
            print(f"splits detected, re-backfilling from Tiingo: {split_tickers}")
            for t in split_tickers:
                n = ingest_ticker(conn, t, "2023-01-01")
                print(f"  {t}: {n} rows")
    except Exception as e:
        print(f"split re-backfill SKIPPED ({e})")


if __name__ == "__main__":
    main()
