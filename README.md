# RADA

Risk-Aware Decision Agent.

## Architecture Intent

RADA is an async, test-first decision pipeline for market-event ingestion and risk-aware action generation.
The initial architecture is split into:

- Schemas: strong typed domain contracts
- Interfaces: abstract boundaries for reasoner/risk/policy/auditor/storage/search
- Core loop: orchestrated event -> decision flow
- Data layer: event ingress, quality hooks, analytics, and decision persistence

## Non-Goals

- No live trading execution
- No broker account connectivity in MVP
- No unmanaged third-party adapter calls in the hot path
- **No sole dependence on GitHub Actions for production deploy** (see [docs/runbook.md](docs/runbook.md))

## Quickstart (Sprint 1 baseline)

1. Create a virtual environment and install dependencies from `pyproject.toml`.
2. Bring up local infra:

	- `make up`
	- or `docker compose up -d`

3. Optional data overlay (Kafka / ZeroMQ / Timescale):

	- `docker compose -f docker-compose.yml -f docker-compose.data.yml up -d`

4. Run checks locally:

	- `ruff check .`
	- `pytest`

5. Start API (health + metrics):

	- `uvicorn rada.main:app --reload`

## Current Scope

Foundation through R5 docs and R6/R7 data stubs:

- Python package under `src/rada/`
- Domain schemas, interfaces, and decision loop
- Pluggable event bus (`inmemory`, `redis`, `kafka`, `zeromq`)
- Ingest quality lineage and rolling P&L analytics stubs
- Causal market shock simulation for replay
- Operator runbook, monitoring docs, ADR log
- Sample GitHub Actions workflows (opt-in under `samples/github-actions/`)

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/runbook.md](docs/runbook.md) | Manual deploy, backup, rollback, incidents |
| [docs/monitoring.md](docs/monitoring.md) | Metrics, logs, alert thresholds, OTel hooks |
| [docs/decisions.md](docs/decisions.md) | Architecture decisions and R1–R5 parity checklist |
| [docs/search.md](docs/search.md) | Simulation -> vectorized search -> batched action flow |
| [samples/github-actions/README.md](samples/github-actions/README.md) | Copy-enable CI/lint workflows |

## Test Strategy

- Unit or mock-contract tests for each main implementation step.
- Integration checkpoint tests at sprint milestones (`tests/integration/`).
- During active buildout, prioritize static checks and targeted reviews before full-suite execution.

## Roadmap

| Milestone | Status | Highlights |
|-----------|--------|------------|
| R1 Foundation | Shipped | schemas, interfaces, compose stack |
| R2 Core loop | Shipped | `decision_loop`, storage adapters |
| R3 Ingest | Shipped | synthetic ingest, fake ingest tests |
| R4 Contracts | Shipped | interface contract tests |
| R5 Docs & samples | Shipped | runbook, monitoring, GH Actions samples |
| R6 Data & search | In progress | bus, analytics, quality, simulation |
| R7+ | Planned | vault-seed issues |

See [docs/decisions.md](docs/decisions.md) for ADRs and vault parity checklist.
