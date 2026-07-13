"""Massive.com (formerly Polygon.io) EOD data provider.

Free plan: 5 requests/minute, end-of-day data only — fine for the nightly
grouped-daily pull (1-2 calls per trading day).

The grouped endpoint returns the whole US stock market's daily bars in one
call. adjusted=true is split-adjusted only (not dividend-adjusted); splits
are detected via the reference endpoint and affected tickers re-backfilled
from Tiingo, which also refreshes dividend adjustment for those names.
"""

import os
import time

import pandas as pd
import requests

BASE = "https://api.massive.com"
RATE_SLEEP = 13  # seconds between calls: free plan allows 5/min


def _token() -> str:
    token = os.environ.get("POLYGON_API_KEY")
    if not token:
        raise RuntimeError("POLYGON_API_KEY not set (put it in .env)")
    return token


def _get(path: str, params: dict) -> dict:
    params = {**params, "apiKey": _token()}
    for attempt in range(5):
        resp = requests.get(f"{BASE}{path}", params=params, timeout=60)
        if resp.status_code == 429:
            time.sleep(60)
            continue
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"rate-limited too long on {path}")


def grouped_daily(day: str, adjusted: bool) -> pd.DataFrame:
    """Daily OHLCV for every US stock on one date (YYYY-MM-DD).
    Empty frame on holidays/weekends."""
    data = _get(
        f"/v2/aggs/grouped/locale/us/market/stocks/{day}",
        {"adjusted": str(adjusted).lower()},
    )
    results = data.get("results") or []
    if not results:
        return pd.DataFrame()
    df = pd.DataFrame(results)[["T", "o", "h", "l", "c", "v"]]
    df.columns = ["ticker", "open", "high", "low", "close", "volume"]
    df["date"] = day
    return df


def splits_since(day: str) -> list[str]:
    """Tickers with a split executing on/after `day` (paginated)."""
    tickers: set[str] = set()
    data = _get(
        "/v3/reference/splits",
        {"execution_date.gte": day, "limit": 1000},
    )
    while True:
        tickers.update(r["ticker"] for r in data.get("results", []))
        next_url = data.get("next_url")
        if not next_url:
            break
        time.sleep(RATE_SLEEP)
        data = requests.get(
            next_url, params={"apiKey": _token()}, timeout=60
        ).json()
    return sorted(tickers)
