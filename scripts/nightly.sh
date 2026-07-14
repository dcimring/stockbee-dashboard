#!/bin/zsh
# Nightly Stockbee pipeline: refresh universe, re-ingest recent days
# (picks up new data + vendor corrections), recompute breadth & scans.
# Invoked by launchd (com.stockbee.nightly) on weekday evenings.

set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

PROJECT="/Users/danielcimring/antigravity/stockbee"
LOG_DIR="$PROJECT/logs"
mkdir -p "$LOG_DIR"
LOG="$LOG_DIR/nightly-$(date +%Y-%m-%d).log"

# Run a pipeline step but never let its failure abort the run — a flaky fetch
# must not skip the compute step and silently leave the dashboard stale.
step() {
  echo "--- $1 ---"
  shift
  if ! "$@"; then
    echo "STEP FAILED (exit $?): $*"
  fi
}

{
  echo "=== nightly run started $(date) ==="
  cd "$PROJECT" || exit 1

  step "universe refresh" uv run python -m pipeline.universe

  # Massive.com grouped bars: ~2 calls per trading day + split re-backfills
  # via Tiingo. 14 calendar days covers late vendor corrections and days the
  # free tier hadn't released yet on the previous run.
  step "grouped daily ingest (Massive)" uv run python -m pipeline.ingest_daily --days 14

  step "benchmark (SPY)" uv run python -m pipeline.ingest --tickers SPY --start "$(date -v-14d +%Y-%m-%d)"

  step "earnings calendar" uv run python -m pipeline.earnings --back 7 --forward 30

  # Always runs, even if a fetch above failed — recomputes from whatever landed.
  step "compute (last 10 days)" uv run python -m pipeline.compute --days 10

  echo "=== nightly run finished $(date) ==="
} >> "$LOG" 2>&1

# keep 30 days of logs
find "$LOG_DIR" -name 'nightly-*.log' -mtime +30 -delete
