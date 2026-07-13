# Data Plan

## Requirement

The Market Monitor needs **daily OHLCV for the entire US common-stock universe** (~6,000+ active tickers) to count 4% movers, quarterly 25% movers, and compute T2108. Single-ticker free APIs can't do this; we need bulk/grouped EOD endpoints.

## Phase 1 — Tiingo (paid plan): bulk backfill + initial daily updates

Decision (2026-07-12): start with a paid Tiingo plan.

- **Backfill:** pull full history (2+ years minimum, more is better) for all active US common stocks via the EOD endpoint. Tiingo provides both raw and split/dividend-adjusted closes (`adjClose`) — store both.
- **Universe:** Tiingo's supported-tickers list, filtered to `assetType = Stock`, US exchanges (NYSE, NASDAQ, AMEX), excluding ETFs/funds/warrants/preferreds/units.
- **Daily updates:** same endpoint, latest date only, after market close (pipeline run ~6pm ET or later to let vendors finalize).
- API key lives in environment variable `TIINGO_API_KEY` (never committed).

## Phase 2 — Massive.com (formerly Polygon.io) free tier for ongoing dailies

Implemented 2026-07-12 in `pipeline/providers/polygon.py` + `pipeline/ingest_daily.py`. Polygon.io rebranded to **Massive.com** in October 2025; base URL is `https://api.massive.com` (legacy `api.polygon.io` still works). Key in `POLYGON_API_KEY`.

- **Endpoint:** `/v2/aggs/grouped/locale/us/market/stocks/{date}` — the whole market's daily bars in a single call. Nightly update = 2 calls per trading day (raw + split-adjusted), so a 14-day corrections window is ~28 calls.
- **Free tier:** 5 requests/minute, end-of-day data. The ingest self-paces at 13s/call, so a nightly run takes ~7 minutes of mostly waiting. Data timing is not critical for this project (confirmed by Daniel).
- **Split/dividend handling:** grouped `adjusted=true` is split-adjusted only, not dividend-adjusted (Tiingo's adjClose is both). `ingest_daily` detects splits via `/v3/reference/splits` and re-backfills affected tickers' full history from Tiingo, which also refreshes their dividend adjustment. Residual caveat: for dividend payers, adjusted closes drift slightly at each ex-div date until the next Tiingo re-backfill of that ticker — the drift per event is well under the 4% scan threshold, acceptable noise.
- Tiingo remains the source for full-history backfills and new-symbol history; the symbols directory (free zip download) also stays on Tiingo.

Keep the paid Tiingo plan until a few weeks of Massive-based nightlies prove clean, then downgrade Tiingo to free (it's still needed for split re-backfills, which are rare enough for free-tier limits).

## Data-quality rules

- **Split adjustment:** compute % moves on adjusted prices so splits don't register as fake 4%/25% moves. On new split events, recompute affected rolling windows.
- **Survivorship:** keep delisted tickers' history in the DB (don't delete); breadth counts on past dates must reflect the universe as it was.
- **Late corrections:** vendors occasionally restate a day; re-ingest the last 5 trading days each night (cheap) to pick up corrections.
- **Sanity checks per run:** universe count within expected band, no day with zero 4% movers, T2108 in [0, 100]; alert/log on violations rather than silently writing bad breadth rows.

## Cost snapshot (verify current pricing before purchase)

- **Tiingo Power/paid:** ~$10–30/mo class, generous request limits, full-history EOD + adjusted data.
- **Polygon free:** $0, 5 req/min, delayed data — likely sufficient for a once-nightly EOD grouped pull, pending verification.
