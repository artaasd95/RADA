# Architecture decision log

Decisions reflected from the projects-management vault. Update when vault Decision-Log entries change.

## ADR-001: Async test-first pipeline

**Status:** Accepted (R1)

RADA uses async Python with Pydantic schemas, abstract interfaces, and pytest markers (`unit`, `integration`). The decision loop orchestrates reasoner → policy → risk → persist without live trading.

**Repo:** `src/rada/core/decision_loop.py`, `src/rada/interfaces/`

## ADR-002: SQLite fallback for local/CI persistence

**Status:** Accepted (R1–R2)

Postgres is the target store in compose; SQLite remains the deterministic fallback for bootstrap and CI without a live DB.

**Repo:** `src/rada/data/storage.py`, `docker-compose.yml`

## ADR-003: MVP — no active GitHub Actions on main

**Status:** Accepted (R5)

Production must not depend solely on GitHub Actions. Workflow templates live under `samples/github-actions/`; operators copy to `.github/workflows/` when opting in.

**Repo:** `samples/github-actions/`, [runbook.md](./runbook.md)

## ADR-004: Pluggable event bus (Redis / Kafka / ZeroMQ)

**Status:** Accepted (R6)

Ingest uses `src/rada/data/bus.py` so `decision_loop` and callers stay unchanged when switching backends. Optional services are documented in `docker-compose.data.yml`.

**Repo:** `src/rada/data/bus.py`, `docker-compose.data.yml`

## ADR-005: MVP monitoring stubs, S9 full observability

**Status:** Accepted (R5 → S9)

MVP exposes `/health`, `/metrics`, and in-process counters with optional OTel hook registration. Full tracing and OTLP export deferred to post-MVP S9.

**Repo:** `src/rada/utils/metrics.py`, [monitoring.md](./monitoring.md)

## ADR-006: Causal market simulation for replay

**Status:** Accepted (R6 / S7)

`src/rada/search/simulation.py` generates shock scenarios with explicit causality chains, outputting `MarketEvent` streams compatible with `decision_loop` replay.

**Repo:** `src/rada/search/simulation.py`

## ADR-007: Timescale warm tier over kdb+ hot tier (MVP)

**Status:** Accepted (spike S9-04)

MVP and export batches use SQL/Timescale. kdb+ evaluated for sub-ms tick hot tier; deferred until ingest SLOs require it.

**Repo:** `docs/spikes/kdb-vs-timescale.md`, `src/rada/data/timescale_store.py`

## ADR-008: Reflection and export off hot path

**Status:** Accepted (S3-03, S6-05–S6-08)

`ReflectionLoop` and `export_batch` never block `DecisionLoop.process_one`. Usage/export pipelines configured via YAML.

**Repo:** `src/rada/core/reflection_loop.py`, `src/rada/data/export_batch.py`, `configs/data/`

## ADR-009: Optional search before risk gate

**Status:** Accepted (S8–S9)

`SearchLoop` is feature-flagged (`RADA_SEARCH_ENABLED`, default off). Wired into `DecisionLoop` between policy and risk.

**Repo:** `src/rada/core/search_loop.py`, `src/rada/search/risk_selection.py`

## Roadmap parity checklist (R1–R5)

| Milestone | Theme | Shipped artifacts (repo) |
|-----------|-------|---------------------------|
| R1 | Foundation | `src/rada/`, schemas, interfaces, unit tests, `docker-compose.yml` |
| R2 | Core loop | `decision_loop.py`, storage adapters, integration boot test |
| R3 | Ingest | `ingestion.py`, fake ingest integration test |
| R4 | Interfaces & contracts | `interfaces/*`, contract unit tests |
| R5 | Docs & samples | `docs/runbook.md`, `docs/monitoring.md`, `docs/decisions.md`, `samples/github-actions/` |

Verify periodically: no broken links in this table, README roadmap, and doc cross-references.
