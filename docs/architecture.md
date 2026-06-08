# Architecture

See also [architecture-overview.md](./architecture-overview.md).

## Hot path

```text
MarketEvent → ingest → calc → reasoner_loop → decision_loop (select + risk gate) → persist
```

- **Reasoner loop** (`src/rada/core/reasoner_loop.py`) — async proposals only; never executes trades.
- **Decision loop** (`src/rada/core/decision_loop.py`) — selects under live CVaR gate, persists `Decision`.
- **Calc** (`src/rada/calc/`) — verified numbers in `DecisionTrace.verified_context`.

## Off hot path

```text
reflection_loop → auditor → outcome stub → export JSONL → policy checkpoint
```

## Audit & feedback

- Append-only `audit_events` — `GET /audit/decision/{id}`, `GET /audit/export`
- Human feedback — `POST /feedback/submit`, `GET /feedback/pending`

## Observability

- OTel spans when `RADA_OTEL_ENABLED=true`
- Prometheus metrics at `GET /metrics`
- Overlay: `docker compose -f docker-compose.prod.yml -f docker-compose.observability.yml`

## Production

- `docker-compose.prod.yml` — RADA + Postgres + Redis, mock reasoner default
- [runbook-production.md](./runbook-production.md)
