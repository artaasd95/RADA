# RADA

**Risk-Aware Decision Agent** — an async Python service that ingests normalized market events, reasons over them, applies risk constraints, and persists decisions. It is built for reviewability and testability, not live trading.

## What you are looking at

RADA is a decision pipeline, not a trading bot. The hot path is:

```text
MarketEvent → reasoner → policy → [optional search] → risk → Decision → store
```

Reflection (auditor feedback, policy checkpoints, batch export) runs **off** that path so latency stays predictable.

## Architecture at a glance

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Schemas | `src/rada/schemas.py` | Typed domain contracts |
| Interfaces | `src/rada/interfaces/` | Reasoner, policy, risk, auditor, storage, search |
| Core | `src/rada/core/` | `decision_loop`, `reflection_loop`, optional `search_loop` |
| Data | `src/rada/data/` | Bus, ingest, storage, pipeline, export cards |
| Search | `src/rada/search/` | Simulation, MCTS, CVaR selection, eval fixtures |
| Ops | `src/rada/utils/metrics.py`, `docs/` | Health, Prometheus stubs, runbooks |

See [docs/architecture-overview.md](docs/architecture-overview.md) for a reviewer-oriented walkthrough.

## Quickstart

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"

docker compose up -d
ruff check .
pytest

uvicorn rada.main:app --reload
```

- Health: `GET /health`
- Metrics: `GET /metrics`

Optional data stack: `docker compose -f docker-compose.yml -f docker-compose.data.yml up -d`

Optional monitoring overlay: `docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d`

## Configuration highlights

| Variable | Default | Purpose |
|----------|---------|---------|
| `RADA_DATA_STORE_MODE` | `sqlite` | `inmemory`, `sqlite`, `timescale` |
| `RADA_EVENT_BUS_MODE` | `inmemory` | Event bus backend |
| `RADA_SEARCH_ENABLED` | off | Enable search before risk gate |
| `RADA_OTEL_ENABLED` | off | Emit OTel hook events |

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/architecture-overview.md](docs/architecture-overview.md) | System design for reviewers |
| [docs/data-platform.md](docs/data-platform.md) | Usage vs export pipeline modes |
| [docs/search-algorithms.md](docs/search-algorithms.md) | Search layer + fixtures |
| [docs/monitoring.md](docs/monitoring.md) | Metrics, alerts, compose overlay |
| [docs/runbook.md](docs/runbook.md) | Deploy, rollback, incidents |
| [docs/decisions.md](docs/decisions.md) | ADR log |
| [docs/post-mvp-demo.md](docs/post-mvp-demo.md) | Data + search demo guide |

## Non-goals

- No live order execution or broker connectivity
- No third-party HTTP on the hot path (MVP)
- Production deploy does not depend solely on GitHub Actions ([runbook](docs/runbook.md))

## Roadmap

| Milestone | Status |
|-----------|--------|
| R1–R5 Foundation → docs | Shipped |
| S3 Reflection loop | Shipped (`reflection_loop.py`) |
| S6 Data platform | Shipped (pipeline, cards, export CLI) |
| S8–S9 Search + monitoring | Shipped (fixtures, feature-flag search) |
| S10+ Product MVP | Planned (vault tasks from S10-01) |

## License

MIT — see [LICENSE](LICENSE).
