# Observability

RADA exposes OpenTelemetry-style tracing, Prometheus metrics, and structured logging via `src/rada/observability/`.

## Metrics

- `GET /metrics` — Prometheus text format
- `GET /metrics/json` — debug snapshot

Key counters: decisions processed, risk-gate rejections, loop errors.

## Docker overlay

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.observability.yml up -d
```

Alert rules: P95 latency > 500ms, error rate > 1%, risk-gate spike (see compose overlay).
