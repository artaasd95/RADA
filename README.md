<p align="center">
  <img src="assets/banner.png" alt="RADA — Risk-Aware Decision Agent" width="100%" />
</p>

<p align="center">
  <a href="https://github.com/artaasd95/RADA/actions/workflows/ci.yml"><img src="https://github.com/artaasd95/RADA/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white" alt="Python 3.11+" /></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.111+-009688?logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker" /></a>
  <a href="https://github.com/artaasd95/RADA"><img src="https://img.shields.io/badge/version-1.0.0-blue" alt="Version 1.0.0" /></a>
  <a href="https://github.com/artaasd95/RADA/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue?logo=apache&logoColor=white" alt="License: Apache 2.0" /></a>
  <a href="https://github.com/artaasd95/RADA"><img src="https://img.shields.io/github/stars/artaasd95/RADA?style=social" alt="GitHub stars" /></a>
</p>

# RADA

Async Python service: ingest market events → verified calc → reasoner proposals → risk-gated decision → audit trail → human review → optional BYOK LLM inference.

## Quickstart (production)

```bash
cp env.example.prod .env
docker compose -f docker-compose.prod.yml up -d --build
./scripts/deploy_check.sh
```

Ingest a shock-compatible event:

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSD","price":60000,"volume":1.0,"timestamp":"2026-06-01T12:00:00Z"}'
```

Streamlit review queue:

```bash
pip install -e ".[dev,ui]"
streamlit run apps/streamlit/dashboard.py
```

## Quickstart (local dev)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
pytest
uvicorn rada.main:app --reload
```

Optional overlays:

```bash
docker compose -f docker-compose.yml -f docker-compose.data.yml up -d
docker compose -f docker-compose.prod.yml -f docker-compose.observability.yml up -d
```

## Pipeline

```text
MarketEvent → calc → reasoner_loop → decision_loop → persist → audit
                      (async, no trades)   (risk gate)
```

Reflection and batch export run **off** the hot path.

## Key commands

| Command | Purpose |
|---------|---------|
| `POST /ingest` | Process one `MarketEvent` |
| `GET /health` | Liveness |
| `GET /metrics` | Prometheus metrics |
| `GET /audit/decision/{id}` | Full audit chain |
| `python scripts/export_reflection.py --from-db` | Batch export from action DB |
| `python scripts/export_reflection.py --synthetic-count 5` | Smoke export |
| `python examples/search_demo.py` | Shock fixture demo |

Mock adapters are the default (`NoOpReasoner`, `ScenarioReasoner`); no external LLM required.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `RADA_DATA_STORE_MODE` | `sqlite` | `inmemory`, `sqlite`, `timescale` |
| `RADA_REASONER_MODE` | `mock` | Mock reasoner in prod compose |
| `RADA_OTEL_ENABLED` | off | Console OTel spans |
| `RADA_API_URL` | `http://localhost:8000` | Streamlit → API |

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/architecture.md](docs/architecture.md) | System design |
| [docs/calc.md](docs/calc.md) | Numerical verification contract |
| [docs/data-platform.md](docs/data-platform.md) | Usage vs export pipelines |
| [docs/runbook-production.md](docs/runbook-production.md) | Deploy, rollback, incidents |
| [docs/post-mvp-demo.md](docs/post-mvp-demo.md) | Data + search demos |

## Milestone

| Milestone | Status |
|-----------|--------|
| R1–R5 Foundation | Shipped |
| v1.0 R-PROD (RADA-01..22) | Shipped |

## License

Apache License 2.0 — see [LICENSE](LICENSE).
