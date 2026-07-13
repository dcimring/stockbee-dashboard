"""Maintain the symbols table: US common stocks on NYSE/NASDAQ/AMEX.

A symbol is active only if Tiingo has data for it within the last ~30 days;
delisted tickers keep their history but are excluded from ingest and scans.
"""

from datetime import date, timedelta

from dotenv import load_dotenv

from . import db
from .providers import tiingo

load_dotenv()

EXCHANGES = {"NYSE", "NASDAQ", "AMEX", "NYSE ARCA", "NYSE MKT"}


def refresh_universe(conn) -> int:
    df = tiingo.fetch_supported_tickers()
    df = df[
        (df["assetType"] == "Stock")
        & (df["exchange"].isin(EXCHANGES))
        & (df["priceCurrency"] == "USD")
        & df["endDate"].notna()
    ]
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    rows = [
        (
            r.ticker.upper(),
            None,
            r.exchange,
            "Stock",
            1 if str(r.endDate)[:10] >= cutoff else 0,
            r.startDate,
            r.endDate,
        )
        for r in df.itertuples()
        if isinstance(r.ticker, str) and r.ticker.isalpha()
    ]
    conn.executemany(
        """INSERT INTO symbols (ticker, name, exchange, type, active, first_seen, last_seen)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(ticker) DO UPDATE SET
             exchange=excluded.exchange, active=excluded.active,
             last_seen=excluded.last_seen""",
        rows,
    )
    conn.commit()
    return len(rows)


if __name__ == "__main__":
    conn = db.connect()
    n = refresh_universe(conn)
    print(f"universe refreshed: {n} symbols")
