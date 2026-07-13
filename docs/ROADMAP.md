# Roadmap

## Near term

- ~~**Breadth time-series charts**~~ — done 2026-07-12: Breadth History section (SPY overlay, 4% up/down, 5d/10d ratios on log scale, 25%-quarter counts, T2108) with 3M/6M/1Y/All ranges, hand-rolled SVG, no deps. Known cosmetic quirk: first ~65 days of the "All" range show zero for the quarterly counts (rolling-window warm-up).
- ~~**Regime threshold tuning**~~ — done 2026-07-12. Rules extracted to `pipeline/regime.py`; `pipeline/backtest_regime.py` grid-searches thresholds against forward SPY returns. Tuned values (washout_t 25, strong_r5 1.1, defensive_r5 0.7, trend_days 3) raised the aggressive-vs-stand_aside fwd10 spread from 0.04pp to 0.40pp (65%+ win rate). Honest caveats: sample is 861 mostly-bull-market days with no true bear phase, so the "avoid crashes" half of the dial is under-tested — **re-run `backtest_regime --grid` after the data includes a real drawdown**. Dashboard shows a regime timeline band under the SPY chart.
- ~~**Earnings-calendar join for EPs**~~ — done 2026-07-12. Source: Nasdaq's public calendar API (`pipeline/providers/nasdaq.py`, no key; unofficial endpoint — if it breaks, Finnhub/FMP free tiers are the fallback). `pipeline/earnings.py` fetches into the `earnings` table (backfilled ±90 days; nightly refreshes −7/+30). EP scan flags earnings catalysts with EPS surprise %; anticipation scan shows days-to-next-earnings (red < 7 on the dashboard — avoid entries into a report).

## Hosted deployment (decided: wanted; platform under investigation)

Move off the local Mac to a hosted environment. **First choice: Cloudflare** (2026-07-12). Open questions to resolve before committing:

1. **Database — D1.** Cloudflare D1 is SQLite-based, so the schema and queries should port cleanly. Verify: ~5M-row `prices` table vs D1 size limits (10 GB/db as of 2026 — likely fine; DB is currently well under that), bulk-write throughput for nightly upserts, and query latency from the dashboard.
2. **Scheduling — Cron Triggers.** Cloudflare Workers support Cron Triggers (cron-syntax scheduled invocations), so "does CF have cron" = yes. The real constraint is what the trigger can run:
3. **The pipeline is the hard part, not the schedule.** `pipeline/` is Python + pandas; Workers are JS-first (Python Workers exist but pandas-heavy compute and 7k+ outbound API calls per run don't fit Worker CPU/time limits well). Options to evaluate:
   - Rewrite ingest+compute as a Worker in JS/TS with set-based SQL in D1 doing the breadth math (most Cloudflare-native; biggest rewrite).
   - Cloudflare **Containers** or a Durable-Object-orchestrated batch job running the existing Python pipeline (least rewrite; newer product, check pricing/limits).
   - Hybrid: keep the Python pipeline anywhere that runs cron (small VPS, GitHub Actions scheduled workflow), have it write to D1 via the HTTP API; host only the dashboard (static frontend + Worker API over D1) on Cloudflare. Pragmatic middle ground.
4. **Dashboard hosting** — FastAPI would be replaced by a Worker serving the API routes + static assets (Cloudflare Pages/Workers Sites); frontend is already a single static HTML file, so this part is easy.
5. **Secrets** — Tiingo key moves to Worker/environment secrets.

Fallback if Cloudflare doesn't fit: any small VPS (the whole stack is one process + SQLite + cron), or Fly.io/Railway which run the current code unchanged.

## Later

- Pre-market/intraday episodic-pivot scanning (needs intraday data source).
- Polygon.io free tier for daily updates (see [DATA.md](DATA.md)) — less relevant if the paid Tiingo plan stays.
- Survivorship-correct backtesting using the delisted tickers' retained history.
- Per-ticker chart view (click-through from scan panels).
