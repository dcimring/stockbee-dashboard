# Stockbee Dashboard

A stock market dashboard implementing Pradeep Bonde's (**@PradeepBonde**, "Stockbee") swing-trading methodology: market-breadth timing via the Market Monitor, plus nightly full-universe scans for Momentum Bursts, Anticipation setups, and Episodic Pivots.

**What it does, nightly and automatically:**

- Ingests EOD bars for ~7,200 active US common stocks (2 API calls via Massive.com grouped aggregates)
- Computes the **Market Monitor**: 4% breakout/breakdown counts, 5d/10d ratios, 25%-in-quarter counts, 13%-in-34-days counts, T2108
- Classifies the market **regime** (aggressive / normal / defensive / stand aside) with thresholds backtested against forward SPY returns
- Runs three scans with quality metrics: **momentum bursts** (4% + volume, close-near-high, consolidation length), **anticipation** (DT / TI65 / MDT variants, range contraction, days to earnings), **episodic pivots** (8%+ on 2x volume, earnings-catalyst auto-flagging with EPS surprise)
- Serves it all on a local web dashboard with breadth history charts and a regime timeline

## Stack

Python 3.12+ · SQLite · pandas · FastAPI · uv. Frontend is a single dependency-free HTML file (hand-rolled SVG charts). ~2,500 lines total.

**Data sources:** [Tiingo](https://tiingo.com) (historical backfill, split re-backfills — paid plan needed for the initial full-universe backfill only), [Massive.com](https://massive.com) free tier (nightly grouped-daily bars), Nasdaq public earnings calendar (no key).

## Setup

```sh
uv sync
cp .env.example .env          # add your TIINGO_API_KEY and POLYGON_API_KEY

# one-time backfill (needs Tiingo paid plan; ~35 min)
uv run python -m pipeline.universe
uv run python -m pipeline.ingest --universe --start 2023-01-01
uv run python -m pipeline.ingest --tickers SPY --start 2023-01-01
uv run python -m pipeline.earnings --back 90 --forward 90
uv run python -m pipeline.compute

# dashboard
uv run uvicorn app.main:app --port 8321
```

**Daily updates** (~10 min, free-tier friendly): [scripts/nightly.sh](scripts/nightly.sh) — universe refresh → Massive grouped ingest (last 14 days, auto split re-backfills) → SPY → earnings calendar → recompute. Runs via launchd (macOS) Tue–Sat 07:00 local; each step is resilient so one failed fetch never skips the recompute. The Massive free tier only authorizes a completed session after the midnight-ET rollover, so a morning run lands the prior trading day — the dashboard reflects the most recent close, not intraday. Run it manually anytime; it's idempotent.

## Documentation

| Doc | Contents |
|---|---|
| [docs/METHODOLOGY.md](docs/METHODOLOGY.md) | The Stockbee trading method — Market Monitor indicators, the three setups, scan formulas, risk rules, sources |
| [docs/DASHBOARD.md](docs/DASHBOARD.md) | Dashboard specification — the five panels and what each computes |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Data flow, schema, design notes (universe filtering, split handling, idempotent ingest) |
| [docs/DATA.md](docs/DATA.md) | Data provider plan and data-quality rules |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Done / next — including hosted-deployment (Cloudflare) investigation |

## Accuracy caveats

The exact Market Monitor column definitions and some scan nuances live behind Stockbee's paid membership; this implementation reconstructs them from his public blog posts and community writeups (sourced in the methodology doc). Regime thresholds were tuned on 2023–2026 data — mostly a bull market — and should be re-tuned once the dataset includes a real bear phase.

## Disclaimer

Educational/personal tooling, not investment advice. Trading involves substantial risk. Verify all data independently before making any financial decision.
