"""Nasdaq public earnings-calendar API (no key required).

Unofficial but stable endpoint used by nasdaq.com itself; requires
browser-like headers. Returns actual EPS, consensus forecast, surprise %,
and report timing (pre-market / after-hours) when supplied.
"""

import re

import pandas as pd
import requests

URL = "https://api.nasdaq.com/api/calendar/earnings"
SCREENER_URL = "https://api.nasdaq.com/api/screener/stocks"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    "Accept": "application/json",
}

TIME_MAP = {
    "time-pre-market": "bmo",
    "time-after-hours": "amc",
    "time-not-supplied": None,
}


def _money(s: str | None) -> float | None:
    """Parse '$2.20' / '($0.81)' / '' to float."""
    if not s:
        return None
    neg = "(" in s
    m = re.search(r"[\d.]+", s.replace(",", ""))
    if not m:
        return None
    v = float(m.group())
    return -v if neg else v


def fetch_screener() -> pd.DataFrame:
    """Whole-market classifications in one call: sector, industry, country,
    IPO year. ~90% of liquid names carry an industry; blanks stay None."""
    resp = requests.get(
        SCREENER_URL, params={"limit": 0, "download": "true"},
        headers=HEADERS, timeout=60,
    )
    resp.raise_for_status()
    rows = (resp.json().get("data") or {}).get("rows") or []
    return pd.DataFrame(
        {
            "ticker": r["symbol"].strip().upper(),
            "sector": r.get("sector") or None,
            "industry": r.get("industry") or None,
            "country": r.get("country") or None,
            "ipo_year": int(r["ipoyear"]) if r.get("ipoyear") else None,
        }
        for r in rows
        if r.get("symbol")
    )


def fetch_earnings(day: str) -> pd.DataFrame:
    """Earnings reported on one date (YYYY-MM-DD). Empty frame if none."""
    resp = requests.get(URL, params={"date": day}, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    rows = (resp.json().get("data") or {}).get("rows") or []
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(
        {
            "ticker": r["symbol"].upper(),
            "date": day,
            "time": TIME_MAP.get(r.get("time"), None),
            "eps_actual": _money(r.get("eps")),
            "eps_forecast": _money(r.get("epsForecast")),
            "surprise_pct": float(r["surprise"]) if r.get("surprise") not in (None, "", "N/A") else None,
        }
        for r in rows
        if r.get("symbol")
    )
