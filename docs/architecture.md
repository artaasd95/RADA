# Architecture

See also [architecture-overview.md](./architecture-overview.md).

## Core Library vs. Showcase

RADA is deliberately split between a reusable library surface and a runnable showcase stack.

- **Core library:** `src/rada/` contains the loops, schemas, audit layer, policies, storage abstractions, and reasoner integrations.
- **Showcase stack:** the FastAPI app, dashboards, configs, scripts, and Docker assets demonstrate a complete standalone deployment.

That split lets teams either extend the library directly or use the repository as a reference system.

## Hot path

```text
MarketEvent → ingest → calc → reasoner_loop → decision_loop (select + risk gate) → persist
```

- **Reasoner loop** (`src/rada/core/reasoner_loop.py`) — async proposals only; never executes trades.
- **Decision loop** (`src/rada/core/decision_loop.py`) — selects under live CVaR gate, persists `Decision`.
- **Calc** (`src/rada/calc/`) — verified numbers in `DecisionTrace.verified_context`.

## Reasoner runtime

- Default runtime mode: real local reasoner via Ollama and `qwen2.5:0.5b`
- BYOK fallback: LiteLLM with OpenAI-compatible credentials from environment variables
- Test and CI mode: mock scenario reasoner for deterministic validation

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

- `docker-compose.prod.yml` — RADA + Postgres + Redis, local-first real reasoner default
- [runbook-production.md](./runbook-production.md)
