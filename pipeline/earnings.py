"""Fetch earnings calendar into the earnings table.

Usage:
  uv run python -m pipeline.earnings --back 7 --forward 30    # nightly
  uv run python -m pipeline.earnings --back 90 --forward 90   # backfill
"""

import argparse
import time
from datetime import date, timedelta

from dotenv import load_dotenv

from . import db
from .providers import nasdaq

load_dotenv()

UPSERT = """
INSERT INTO earnings (ticker, date, time, eps_actual, eps_forecast, surprise_pct)
VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(ticker, date) DO UPDATE SET
  time=excluded.time, eps_actual=excluded.eps_actual,
  eps_forecast=excluded.eps_forecast, surprise_pct=excluded.surprise_pct
"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--back", type=int, default=7)
    ap.add_argument("--forward", type=int, default=30)
    args = ap.parse_args()

    conn = db.connect()
    day = date.today() - timedelta(days=args.back)
    end = date.today() + timedelta(days=args.forward)
    total = 0
    while day <= end:
        if day.weekday() < 5:
            try:
                df = nasdaq.fetch_earnings(day.isoformat())
            except Exception as e:
                print(f"{day}: ERROR {e}")
                day += timedelta(days=1)
                continue
            if not df.empty:
                conn.executemany(UPSERT, df.itertuples(index=False))
                conn.commit()
                total += len(df)
            print(f"{day}: {len(df)} reports")
            time.sleep(0.5)
        day += timedelta(days=1)
    print(f"done: {total} earnings rows")


if __name__ == "__main__":
    main()
