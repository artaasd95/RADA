# Monitoring and alerting (MVP)

Observability hooks for RADA align with post-MVP **S9 production monitoring** intent. MVP ships stubs and documented thresholds; full OpenTelemetry export is opt-in.

## Metrics endpoints

| Endpoint | Format | Purpose |
|----------|--------|---------|
| `GET /health` | JSON | Liveness (`{"status":"ok"}`) |
| `GET /metrics` | Prometheus text | Counters/gauges from `src/rada/utils/metrics.py` |

### Exposed metrics (MVP)

| Metric | Type | Description |
|--------|------|-------------|
| `rada_decisions_processed_total` | counter | Decisions completed by `DecisionLoop` |
| `rada_events_ingested_total` | counter | Events passing ingest/quality |
| `rada_ingest_quality_rejected_total` | counter | Events rejected by quality hooks |
| `rada_rolling_pnl_stub` | gauge | Latest rolling P&L stub from analytics |

## Log structure

Logs should be structured JSON in production (plain text acceptable in dev).

Recommended fields:

```json
{
  "timestamp": "2026-05-30T12:00:00Z",
  "level": "INFO",
  "service": "rada",
  "env": "prod",
  "message": "decision persisted",
  "decision_id": "uuid",
  "symbol": "BTCUSD",
  "event_bus_mode": "redis"
}
```

Set `RADA_LOG_LEVEL` (`DEBUG`, `INFO`, `WARNING`, `ERROR`). See `.env.example`.

## Alert thresholds (recommended starting points)

| Signal | Warning | Critical | Action |
|--------|---------|----------|--------|
| `/health` non-200 | 1 min | 3 min | Restart app; see [runbook.md](./runbook.md) |
| `rada_ingest_quality_rejected_total` rate | > 5/min | > 20/min | Inspect ingest source; check clock skew |
| Postgres connections | > 80% pool | exhausted | Scale pool; restart app |
| Redis memory | > 70% | > 90% | Restart Redis; drain queue |
| Decision latency p95 | > 2s | > 5s | Profile reasoner/risk; reduce load |

Wire alerts to your operator channel (PagerDuty, email, etc.) — not GitHub Actions.

## OpenTelemetry hooks

MVP provides registration stubs only:

```python
from rada.utils.metrics import register_otel_hook

def export_span(event: str, attributes: dict) -> None:
    ...  # post-MVP: OTel tracer/meter export

register_otel_hook(export_span)
```

Enable with `RADA_OTEL_ENABLED=true`. Without hooks registered, events are no-ops beyond in-process counters.

Post-MVP S9 will add:

- Distributed traces across ingest → decision → persist
- OTLP export to collector
- SLO dashboards for decision latency and ingest lag

## Related

- [runbook.md](./runbook.md) — incident response
- [decisions.md](./decisions.md) — ADR-005 monitoring stance
