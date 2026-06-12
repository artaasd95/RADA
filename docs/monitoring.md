# Monitoring and alerting (MVP)

Observability hooks for RADA align with post-MVP **S9 production monitoring** intent. MVP ships stubs and documented thresholds; full OpenTelemetry export is opt-in.

## Metrics endpoints

| Endpoint | Format | Purpose |
|----------|--------|---------|
| `GET /health` | JSON | Liveness (`{"status":"ok"}`) |
| `GET /metrics` | Prometheus text | Legacy (`utils/metrics.py`) + observability (`observability/metrics.py`) |
| `GET /metrics/json` | JSON | Debug snapshot of both metric facades |

### Legacy metrics (`src/rada/utils/metrics.py`)

| Metric | Type | Description |
|--------|------|-------------|
| `rada_decisions_processed_total` | counter | Decisions completed by `DecisionLoop` |
| `rada_events_ingested_total` | counter | Events passing ingest/quality |
| `rada_ingest_quality_rejected_total` | counter | Events rejected by quality hooks |
| `rada_rolling_pnl_stub` | gauge | Latest rolling P&L stub from analytics |
| `rada_reflection_processed_total` | counter | Decisions processed by reflection loop |
| `rada_reflection_mean_faithfulness` | gauge | Rolling mean faithfulness from audits |
| `rada_search_invocations_total` | counter | Search loop invocations when enabled |

### Observability metrics (`src/rada/observability/metrics.py`)

| Metric | Type | Description |
|--------|------|-------------|
| `rada_decisions_total` | counter | Decisions completed (decision loop) |
| `rada_risk_gate_rejections_total` | counter | Risk gate rejections |
| `rada_loop_errors_total` | counter | Background loop errors |
| `rada_audit_queue_drops_total` | counter | Audit events dropped when queue is full |
| `rada_reflection_queue_drops_total` | counter | Reflection decisions dropped when queue is full |

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

## Docker monitoring overlay

```bash
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

- Prometheus UI: http://localhost:9090
- Grafana UI: http://localhost:3000 (admin/admin)

Scrape config: `configs/monitoring/prometheus.yml` (targets host app on port 8000).

## Alert hooks

```python
from rada.utils.metrics import emit_alert, register_alert_hook

def pagerduty_bridge(name: str, payload: dict) -> None:
    ...

register_alert_hook(pagerduty_bridge)
emit_alert("ingest_quality_spike", severity="critical", rate_per_min=25)
```

## Related

- [runbook.md](./runbook.md) — incident response
- [decisions.md](./decisions.md) — ADR-005 monitoring stance
