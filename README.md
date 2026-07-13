# Stockbee Dashboard

A stock market dashboard implementing Pradeep Bonde's (**@PradeepBonde**, "Stockbee") swing-trading methodology: market-breadth timing via the Market Monitor, plus nightly scans for Momentum Bursts, Anticipation setups, and Episodic Pivots.

## Documentation

| Doc | Contents |
|---|---|
| [docs/METHODOLOGY.md](docs/METHODOLOGY.md) | The Stockbee trading method — Market Monitor breadth indicators, the three setups, scan formulas, risk rules |
| [docs/DASHBOARD.md](docs/DASHBOARD.md) | Dashboard specification — the five panels and what each computes/displays |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Tech stack, data pipeline design, database schema sketch |
| [docs/DATA.md](docs/DATA.md) | Data provider plan — Tiingo paid backfill, Polygon free tier for ongoing dailies, universe definition |
| [docs/ROADMAP.md](docs/ROADMAP.md) | What's next — charts, regime tuning, hosted deployment (Cloudflare investigation) |

## Key decisions (agreed 2026-07-12)

- **Stack:** Python data pipeline (nightly EOD pull → breadth calculations → scan results in SQLite) with a web frontend.
- **Data plan:** Start with a **paid Tiingo plan** to bulk-load full-market historical EOD data. Afterwards, evaluate switching daily updates to **Polygon.io free tier** to cut recurring cost.
- **Scope:** End-of-day system first. Intraday/pre-market Episodic Pivot scanning is a later phase.

## Status

Working end-to-end on the **full universe**: 7,263 active US common stocks, daily bars from 2023-01-03 (Tiingo paid plan, backfilled 2026-07-12). Pipeline: `pipeline/` (ingest, universe, compute); dashboard: `app/` (FastAPI + single-page frontend). Scan panels rank by quality and show the top 50.

**Nightly automation:** launchd job `com.stockbee.nightly` (plist in `~/Library/LaunchAgents/`) runs [scripts/nightly.sh](scripts/nightly.sh) weekdays at 7:30pm local (America/Cayman — after US close year-round): universe refresh → Massive.com grouped-daily ingest of last 14 days (~28 API calls; auto re-backfills split tickers from Tiingo) → `compute --days 10`. Takes ~10 minutes, mostly free-tier rate-limit pacing. Logs to `logs/nightly-YYYY-MM-DD.log`, 30-day retention. launchd runs missed jobs on wake if the Mac was asleep. Manage with:

```sh
launchctl kickstart gui/501/com.stockbee.nightly   # run now
launchctl bootout gui/501/com.stockbee.nightly     # disable
```

When moving to a hosted environment, reuse `scripts/nightly.sh` under cron/systemd and drop the plist.

```sh
uv run python -m pipeline.ingest --tickers AAPL,MSFT --start 2025-01-01   # fetch EOD data
uv run python -m pipeline.compute                                         # breadth + scans
uv run uvicorn app.main:app --port 8321                                   # dashboard
```

After upgrading Tiingo: `uv run python -m pipeline.universe` then `uv run python -m pipeline.ingest --universe --start 2023-01-01`.

Built: all three scans (momentum burst with quality metrics, anticipation DT/TI65/MDT, EOD episodic pivot), Market Monitor table, regime banner, dashboard panels for each.

Not yet built: see [docs/ROADMAP.md](docs/ROADMAP.md) — breadth charts, regime tuning, hosted deployment (Cloudflare), earnings-calendar join, intraday EP scanning.

## Caveats

The exact Market Monitor column definitions and some scan nuances live behind Stockbee's paid membership; public blog posts and community writeups (see sources in [docs/METHODOLOGY.md](docs/METHODOLOGY.md)) cover enough to build a faithful version, but third-party writeups sometimes garble details. If you join the membership, transcribe his posted TC2000 scan codes as ground truth and update the docs.
