"""Nightly compute: breadth (Market Monitor) + scans from the prices table.

All % moves use adjusted prices so splits don't register as fake moves.

Scans (written to scan_results):
  momentum_burst  — close >= 1.04x prior close, volume > prior day
  anticipation    — momentum stock in a quiet phase (Double Trouble / TI65 / MDT)
  episodic_pivot  — EOD big move on 2x+ average volume (catalyst check is manual)

Usage:
  uv run python -m pipeline.compute            # full recompute
  uv run python -m pipeline.compute --days 10  # only most recent N days
"""

import argparse
import json

import pandas as pd

from . import db

MIN_VOLUME = 100_000  # Stockbee-style liquidity floor for scan hits

# index/ETF series stored in prices for charting but excluded from breadth/scans
BENCHMARKS = ("SPY",)


def load_prices(conn) -> pd.DataFrame:
    df = pd.read_sql(
        f"""SELECT ticker, date, high, low, close, volume,
                   adj_open, adj_high, adj_low, adj_close
            FROM prices
            WHERE ticker NOT IN ({','.join('?' * len(BENCHMARKS))})""",
        conn,
        params=BENCHMARKS,
    )
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    g = df.groupby("ticker", sort=False)

    df["prev_close"] = g["adj_close"].shift(1)
    df["prev_volume"] = g["volume"].shift(1)
    df["pct"] = df["adj_close"] / df["prev_close"] - 1
    df["gap"] = df["adj_open"] / df["prev_close"] - 1

    df["close_65_ago"] = g["adj_close"].shift(65)
    df["close_34_ago"] = g["adj_close"].shift(34)
    df["sma40"] = g["adj_close"].transform(lambda s: s.rolling(40).mean())
    df["sma10"] = g["adj_close"].transform(lambda s: s.rolling(10).mean())

    # anticipation-scan ingredients
    df["avgc7"] = g["adj_close"].transform(lambda s: s.rolling(7).mean())
    df["avgc65"] = g["adj_close"].transform(lambda s: s.rolling(65).mean())
    df["avgc126"] = g["adj_close"].transform(lambda s: s.rolling(126).mean())
    df["minl252"] = g["adj_low"].transform(lambda s: s.rolling(252, min_periods=126).min())
    df["minv3"] = g["volume"].transform(lambda s: s.rolling(3).min())
    df["vol_avg50"] = g["volume"].transform(lambda s: s.rolling(50).mean())

    # range contraction: 5d avg daily range vs 20d avg (lower = quieter)
    rng_pct = (df["adj_high"] - df["adj_low"]) / df["adj_close"]
    df["rng5_over_rng20"] = (
        rng_pct.groupby(df["ticker"]).transform(lambda s: s.rolling(5).mean())
        / rng_pct.groupby(df["ticker"]).transform(lambda s: s.rolling(20).mean())
    )

    # consecutive up-days *before* today
    up = df["pct"] > 0
    block = (~up.fillna(False)).groupby(df["ticker"]).cumsum()
    consec_incl = up.fillna(False).groupby([df["ticker"], block]).cumsum()
    df["consec_up_prior"] = consec_incl.groupby(df["ticker"]).shift(1).fillna(0).astype(int)

    # trading days since the previous 4% up move (proxy for consolidation length)
    pos = g.cumcount()
    burst_pos = pos.where(df["pct"] >= 0.04)
    prior_burst_pos = burst_pos.groupby(df["ticker"]).ffill().groupby(df["ticker"]).shift(1)
    df["days_since_burst"] = pos - prior_burst_pos

    return df


def _recent_dates(df: pd.DataFrame, days: int | None) -> set | None:
    if not days:
        return None
    return set(sorted(df["date"].unique())[-days:])


def _upsert_scan(conn, scan: str, rows: list[tuple]) -> int:
    conn.executemany(
        """INSERT INTO scan_results (date, scan, ticker, metrics) VALUES (?, ?, ?, ?)
           ON CONFLICT(date, scan, ticker) DO UPDATE SET metrics=excluded.metrics""",
        [(d, scan, t, json.dumps(m)) for d, t, m in rows],
    )
    conn.commit()
    return len(rows)


def _f(v, nd=3):
    return None if pd.isna(v) else round(float(v), nd)


def compute_breadth(conn, df: pd.DataFrame, days: int | None = None) -> int:
    d = df.dropna(subset=["pct"])
    by_date = d.groupby("date")
    out = pd.DataFrame(
        {
            "up4": by_date.apply(lambda x: int((x["pct"] >= 0.04).sum()), include_groups=False),
            "down4": by_date.apply(lambda x: int((x["pct"] <= -0.04).sum()), include_groups=False),
            "universe_count": by_date.size(),
        }
    )
    out["ratio5"] = out["up4"].rolling(5).sum() / out["down4"].rolling(5).sum()
    out["ratio10"] = out["up4"].rolling(10).sum() / out["down4"].rolling(10).sum()

    q = df.dropna(subset=["close_65_ago"])
    qr = q["adj_close"] / q["close_65_ago"] - 1
    out["up25q"] = q[qr >= 0.25].groupby("date").size()
    out["down25q"] = q[qr <= -0.25].groupby("date").size()

    m = df.dropna(subset=["close_34_ago"])
    mr = m["adj_close"] / m["close_34_ago"] - 1
    out["up13_34"] = m[mr >= 0.13].groupby("date").size()
    out["down13_34"] = m[mr <= -0.13].groupby("date").size()

    t = df.dropna(subset=["sma40"])
    out["t2108"] = (
        t[t["adj_close"] > t["sma40"]].groupby("date").size() / t.groupby("date").size() * 100
    )

    out = out.fillna(0).reset_index()
    # drop phantom sessions (market holidays where a stray ticker has a row)
    out = out[out["universe_count"] >= 0.5 * out["universe_count"].median()]
    if days:
        out = out.tail(days)
    rows = [
        (
            r.date, int(r.up4), int(r.down4),
            float(r.ratio5), float(r.ratio10),
            int(r.up25q), int(r.down25q),
            int(r.up13_34), int(r.down13_34),
            float(r.t2108), int(r.universe_count),
        )
        for r in out.itertuples()
    ]
    conn.executemany(
        """INSERT INTO breadth_daily
           (date, up4, down4, ratio5, ratio10, up25q, down25q, up13_34, down13_34, t2108, universe_count)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(date) DO UPDATE SET
             up4=excluded.up4, down4=excluded.down4, ratio5=excluded.ratio5,
             ratio10=excluded.ratio10, up25q=excluded.up25q, down25q=excluded.down25q,
             up13_34=excluded.up13_34, down13_34=excluded.down13_34,
             t2108=excluded.t2108, universe_count=excluded.universe_count""",
        rows,
    )
    conn.commit()
    return len(rows)


def scan_momentum_burst(conn, df: pd.DataFrame, days: int | None = None) -> int:
    """close >= 1.04 * prior close AND volume > prior day, with quality metrics."""
    hits = df[
        (df["pct"] >= 0.04)
        & (df["volume"] > df["prev_volume"])
        & (df["volume"] >= MIN_VOLUME)
        & (df["adj_close"] >= 1)
    ].copy()
    keep = _recent_dates(df, days)
    if keep:
        hits = hits[hits["date"].isin(keep)]
    rng = hits["high"] - hits["low"]
    hits["cnh"] = (hits["close"] - hits["low"]) / rng.where(rng > 0)
    rows = [
        (
            r.date, r.ticker,
            {
                "pct": _f(r.pct, 4),
                "volume": int(r.volume),
                "close_near_high": _f(r.cnh),
                "consec_up_prior": int(r.consec_up_prior),
                "days_since_burst": None if pd.isna(r.days_since_burst) else int(r.days_since_burst),
                "ext_sma10": _f(r.adj_close / r.sma10 - 1) if pd.notna(r.sma10) else None,
            },
        )
        for r in hits.itertuples()
    ]
    return _upsert_scan(conn, "momentum_burst", rows)


def _next_earnings(earn: pd.DataFrame):
    """Map (ticker, date) -> calendar days until the next earnings report."""
    if earn.empty:
        return lambda ticker, day: None
    by_ticker: dict[str, list[str]] = {}
    for r in earn.itertuples():
        by_ticker.setdefault(r.ticker, []).append(r.date)
    for v in by_ticker.values():
        v.sort()

    def lookup(ticker: str, day: str):
        from datetime import date

        for d in by_ticker.get(ticker, ()):
            if d >= day:
                return (date.fromisoformat(d) - date.fromisoformat(day)).days
        return None

    return lookup


def scan_anticipation(conn, df: pd.DataFrame, days: int | None = None) -> int:
    """Momentum stock in a quiet phase: today ±1%, liquid, and at least one of
    Double Trouble (c/minl252 >= 1.8), TI65 (avgc7/avgc65 > 1.05),
    MDT (c/avgc126 > 1.19)."""
    next_earn = _next_earnings(load_earnings(conn))
    d = df[
        (df["pct"].abs() <= 0.01)
        & (df["minv3"] >= MIN_VOLUME)
        & (df["adj_close"] >= 1)
    ].copy()
    keep = _recent_dates(df, days)
    if keep:
        d = d[d["date"].isin(keep)]

    d["dt"] = d["adj_close"] / d["minl252"] >= 1.8
    d["ti65"] = d["avgc7"] / d["avgc65"] > 1.05
    d["mdt"] = d["adj_close"] / d["avgc126"] > 1.19
    d = d[d[["dt", "ti65", "mdt"]].any(axis=1)]

    rows = [
        (
            r.date, r.ticker,
            {
                "variants": [v for v, ok in (("DT", r.dt), ("TI65", r.ti65), ("MDT", r.mdt)) if ok],
                "ti65_ratio": _f(r.avgc7 / r.avgc65) if pd.notna(r.avgc65) else None,
                "contraction": _f(r.rng5_over_rng20),
                "days_since_burst": None if pd.isna(r.days_since_burst) else int(r.days_since_burst),
                "consec_up_prior": int(r.consec_up_prior),
                "days_to_earnings": next_earn(r.ticker, r.date),
            },
        )
        for r in d.itertuples()
    ]
    return _upsert_scan(conn, "anticipation", rows)


def load_earnings(conn) -> pd.DataFrame:
    return pd.read_sql(
        "SELECT ticker, date, time, surprise_pct FROM earnings", conn
    )


def _earnings_catalyst(earn: pd.DataFrame):
    """Map (ticker, ep_date) -> earnings row if the company reported on the
    EP day (pre-market/unspecified) or within the prior 3 calendar days
    (after-hours / weekend gap)."""
    if earn.empty:
        return lambda ticker, day: None
    by_ticker: dict[str, list[tuple[str, str | None, float | None]]] = {}
    for r in earn.itertuples():
        by_ticker.setdefault(r.ticker, []).append((r.date, r.time, r.surprise_pct))

    def lookup(ticker: str, day: str):
        from datetime import date, timedelta

        lo = (date.fromisoformat(day) - timedelta(days=3)).isoformat()
        for d, t, s in by_ticker.get(ticker, ()):
            if d == day and t != "amc":
                return {"earnings_date": d, "surprise_pct": s}
            if lo <= d < day:
                return {"earnings_date": d, "surprise_pct": s}
        return None

    return lookup


def scan_episodic_pivot(conn, df: pd.DataFrame, days: int | None = None) -> int:
    """EOD EP: 8%+ move on 2x+ 50-day average volume, $3+ stock.
    Earnings catalysts auto-flagged from the earnings table; other
    catalysts (contracts, FDA, M&A) remain a manual check."""
    catalyst = _earnings_catalyst(load_earnings(conn))
    hits = df[
        (df["pct"] >= 0.08)
        & (df["volume"] >= 2 * df["vol_avg50"])
        & (df["volume"] >= 300_000)
        & (df["adj_close"] >= 3)
    ].copy()
    keep = _recent_dates(df, days)
    if keep:
        hits = hits[hits["date"].isin(keep)]
    rows = []
    for r in hits.itertuples():
        earn = catalyst(r.ticker, r.date)
        rows.append(
            (
                r.date, r.ticker,
                {
                    "pct": _f(r.pct, 4),
                    "gap": _f(r.gap, 4),
                    "rel_volume": _f(r.volume / r.vol_avg50, 1),
                    "volume": int(r.volume),
                    "nine_million": bool(r.volume >= 9_000_000),
                    "dollar_volume_m": _f(r.volume * r.close / 1e6, 1),
                    "earnings": earn is not None,
                    "surprise_pct": earn["surprise_pct"] if earn else None,
                },
            )
        )
    return _upsert_scan(conn, "episodic_pivot", rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, help="only recompute the most recent N days")
    args = ap.parse_args()

    conn = db.connect()
    df = load_prices(conn)
    if df.empty:
        print("no prices in DB — run ingest first")
        return
    nb = compute_breadth(conn, df, args.days)
    nmb = scan_momentum_burst(conn, df, args.days)
    na = scan_anticipation(conn, df, args.days)
    nep = scan_episodic_pivot(conn, df, args.days)
    print(
        f"breadth rows: {nb}, momentum bursts: {nmb}, "
        f"anticipation: {na}, episodic pivots: {nep}"
    )


if __name__ == "__main__":
    main()
