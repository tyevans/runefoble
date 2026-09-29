#!/usr/bin/env bash
# Local CI Runner Simulation for Playwright BDD Quality Gate (TASK-0364)
# Governed by ADR-0010 and ADR-0014.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> [Local CI Runner] Simulating GitHub Actions e2e-playwright job..."

# Clean up any running dev server processes on exit
DEV_PID=""
cleanup() {
  if [[ -n "$DEV_PID" ]] && kill -0 "$DEV_PID" 2>/dev/null; then
    echo "==> [Local CI Runner] Stopping background development services (PID $DEV_PID)..."
    kill -TERM "$DEV_PID" 2>/dev/null || true
    wait "$DEV_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

# 1. Setup environment variables matching CI
export CI=true
export PLAYWRIGHT_BASE_URL="http://localhost:5173"
export SPICEDB_ENDPOINT="mock"
export RUNEFOBLE_SPICEDB_ENDPOINT="mock"
export AUTH_DEV_MODE="true"
export RUNEFOBLE_AUTH_DEV_MODE="true"
export REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
export RUNEFOBLE_REDIS_URL="${RUNEFOBLE_REDIS_URL:-redis://localhost:6379/0}"

# 2. Check if background services should be started or are already running
if curl -sf http://localhost:8000/api/v1/health >/dev/null 2>&1 && curl -sf http://localhost:5173 >/dev/null 2>&1; then
  echo "==> [Local CI Runner] Detected running services on :8000 and :5173. Reusing existing servers."
else
  echo "==> [Local CI Runner] Starting local services in background via dev_server.py..."
  python3 scripts/dev_server.py --timeout 60 &
  DEV_PID=$!

  echo "==> [Local CI Runner] Polling service readiness..."
  TIMEOUT=60
  START_TIME=$(date +%s)
  READY=false
  while [[ $(($(date +%s) - START_TIME)) -lt $TIMEOUT ]]; do
    if curl -sf http://localhost:8000/api/v1/health >/dev/null 2>&1 && curl -sf http://localhost:5173 >/dev/null 2>&1; then
      READY=true
      break
    fi
    sleep 2
  done

  if [[ "$READY" != "true" ]]; then
    echo "==> [Local CI Runner] Error: Services failed to become ready within ${TIMEOUT}s" >&2
    exit 1
  fi
  echo "==> [Local CI Runner] API Gateway and Vite Frontend are ready!"
fi

# 3. Execute Playwright BDD Suite in headless mode
echo "==> [Local CI Runner] Executing Playwright BDD test suite..."
make test-e2e ARGS="--reporter=github,html ${ARGS:-}"

echo "==> [Local CI Runner] Playwright BDD Quality Gate passed successfully!"
