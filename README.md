# RADA

Risk-Aware Decision Agent.

## Architecture Intent

RADA is an async, test-first decision pipeline for market-event ingestion and risk-aware action generation.
The initial architecture is split into:

- Schemas: strong typed domain contracts
- Interfaces: abstract boundaries for reasoner/risk/policy/auditor/storage/search
- Core loop: orchestrated event -> decision flow
- Data layer: event ingress and decision persistence

## Non-Goals

- No live trading execution
- No broker account connectivity in MVP
- No unmanaged third-party adapter calls in the hot path

## Quickstart (Sprint 1 baseline)

1. Create a virtual environment and install dependencies from `pyproject.toml`.
2. Bring up local infra:

	- `make up`
	- or `docker compose up -d`

3. Run checks locally:

	- `ruff check .`
	- `pytest`

## Current Scope

This repository currently contains Sprint 1 foundation assets:

- Python package scaffold under `src/rada/`
- Domain schemas and interface contracts
- Unit/mock tests for schema and interface contracts
- Local Redis/Postgres compose stack

## Test Strategy

- Add unit or mock-contract tests for each main implementation step.
- Add integration checkpoint tests at the end of each sprint milestone.
- During active buildout, prioritize static checks and targeted reviews before full-suite execution.

## Roadmap

Main loop implementation, ingest pipeline, persistence, and sprint-end integration tests are tracked in the vault-seed issue list.
