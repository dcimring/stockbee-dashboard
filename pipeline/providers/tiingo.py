"""Tiingo EOD data provider.

Free plan limits (as of 2026): ~50 req/hour, 1000 req/day, 500 unique
symbols/month — fine for testing with a small ticker list; the full-universe
backfill needs the paid plan.
"""

import io
import os
import zipfile

import pandas as pd
import requests

BASE = "https://api.tiingo.com"
SUPPORTED_TICKERS_URL = (
    "https://apimedia.tiingo.com/docs/tiingo/daily/supported_tickers.zip"
)


def _token() -> str:
    token = os.environ.get("TIINGO_API_KEY")
    if not token:
        raise RuntimeError("TIINGO_API_KEY not set (put it in .env)")
    return token


def fetch_supported_tickers() -> pd.DataFrame:
    """Full Tiingo symbol directory (no API-call cost; static zip)."""
    resp = requests.get(SUPPORTED_TICKERS_URL, timeout=60)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        with zf.open(zf.namelist()[0]) as f:
            return pd.read_csv(f)


def fetch_daily(ticker: str, start_date: str, end_date: str | None = None) -> pd.DataFrame:
    """Daily OHLCV (raw + adjusted) for one ticker. Empty frame if no data."""
    params = {"startDate": start_date, "token": _token(), "format": "json"}
    if end_date:
        params["endDate"] = end_date
    resp = requests.get(
        f"{BASE}/tiingo/daily/{ticker}/prices", params=params, timeout=30
    )
    if resp.status_code == 404:
        return pd.DataFrame()
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["date"]).dt.date.astype(str)
    df["ticker"] = ticker.upper()
    return df[
        [
            "ticker", "date", "open", "high", "low", "close", "volume",
            "adjOpen", "adjHigh", "adjLow", "adjClose",
        ]
    ].rename(
        columns={
            "adjOpen": "adj_open",
            "adjHigh": "adj_high",
            "adjLow": "adj_low",
            "adjClose": "adj_close",
        }
    )
