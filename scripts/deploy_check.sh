#!/usr/bin/env bash
set -euo pipefail

RADA_HOST="${RADA_HOST:-localhost}"
RADA_PORT="${RADA_PORT:-8000}"
BASE_URL="http://${RADA_HOST}:${RADA_PORT}"

echo "==> RADA deploy check (${BASE_URL})"

required_vars=(RADA_DATA_STORE_MODE)
for var in "${required_vars[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "WARN: ${var} not set (using app defaults)"
  else
    echo "OK: ${var}=${!var}"
  fi
done

echo "==> Port reachability"
if command -v nc >/dev/null 2>&1; then
  nc -z "${RADA_HOST}" "${RADA_PORT}"
  echo "OK: port ${RADA_PORT} open"
fi

echo "==> Health"
curl -fsS "${BASE_URL}/health" | grep -q '"status":"ok"'
echo "OK: /health"

echo "==> Metrics"
curl -fsS "${BASE_URL}/metrics" | grep -q rada_decisions_total
echo "OK: /metrics"

echo "==> Ingest smoke"
curl -fsS -X POST "${BASE_URL}/ingest" \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSD","price":60000,"volume":1.0,"timestamp":"2026-06-01T12:00:00Z"}' \
  | grep -q decision_id
echo "OK: /ingest"

echo "Deploy check passed."
