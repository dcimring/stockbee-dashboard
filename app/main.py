"""Stockbee dashboard — FastAPI backend over the pipeline's SQLite DB."""

import json
import sqlite3
from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from pipeline import regime as regime_rules
from pipeline.db import DB_PATH

app = FastAPI(title="Stockbee Dashboard")

INDEX = Path(__file__).parent / "static" / "index.html"


def q(sql: str, *params) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params)]
    finally:
        conn.close()


def _breadth_df(days: int) -> pd.DataFrame:
    rows = q(
        "SELECT date, ratio5, t2108 FROM breadth_daily ORDER BY date DESC LIMIT ?",
        days,
    )
    return pd.DataFrame(rows[::-1])  # chronological


@app.get("/", response_class=HTMLResponse)
def index():
    return INDEX.read_text()


@app.get("/api/breadth")
def breadth(days: int = 30):
    return q(
        "SELECT * FROM breadth_daily ORDER BY date DESC LIMIT ?", days
    )


@app.get("/api/benchmark")
def benchmark(ticker: str = "SPY", days: int = 250):
    return q(
        "SELECT date, adj_close AS close FROM prices "
        "WHERE ticker=? ORDER BY date DESC LIMIT ?",
        ticker, days,
    )


@app.get("/api/regime")
def regime():
    df = _breadth_df(10)
    if len(df) < 4:
        return {"regime": "unknown", "rationale": "not enough breadth history", "date": None}
    reg = regime_rules.classify(df).iloc[-1]
    last = df.iloc[-1].to_dict()
    return {
        "regime": reg,
        "rationale": regime_rules.rationale(last, reg),
        "date": last["date"],
    }


@app.get("/api/regime_history")
def regime_history(days: int = 250):
    df = _breadth_df(days + regime_rules.DEFAULTS["trend_days"])
    if df.empty:
        return []
    df["regime"] = regime_rules.classify(df)
    return df.tail(days)[["date", "regime"]].to_dict("records")


# per-scan quality ranking (SQLite json_extract over the metrics blob)
SCAN_ORDER = {
    "momentum_burst": (
        "json_extract(metrics, '$.close_near_high') DESC, "
        "json_extract(metrics, '$.pct') DESC"
    ),
    "anticipation": "json_extract(metrics, '$.contraction') ASC",
    "episodic_pivot": (
        "json_extract(metrics, '$.rel_volume') DESC, "
        "json_extract(metrics, '$.pct') DESC"
    ),
}


@app.get("/api/scans/{scan}")
def scans(scan: str, days: int = 5, limit: int = 50):
    dates = [
        r["date"]
        for r in q(
            "SELECT DISTINCT date FROM scan_results WHERE scan=? ORDER BY date DESC LIMIT ?",
            scan, days,
        )
    ]
    if not dates:
        return {"total": 0, "rows": []}
    placeholders = ",".join("?" * len(dates))
    total = q(
        f"SELECT count(*) AS n FROM scan_results WHERE scan=? AND date IN ({placeholders})",
        scan, *dates,
    )[0]["n"]
    order = SCAN_ORDER.get(scan, "sr.ticker")
    rows = q(
        f"SELECT sr.date, sr.ticker, sr.metrics, sy.exchange FROM scan_results sr "
        f"LEFT JOIN symbols sy ON sy.ticker = sr.ticker "
        f"WHERE sr.scan=? AND sr.date IN ({placeholders}) "
        f"ORDER BY sr.date DESC, {order} LIMIT ?",
        scan, *dates, limit,
    )
    for r in rows:
        r["metrics"] = json.loads(r["metrics"])
    return {"total": total, "rows": rows}
