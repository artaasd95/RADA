# RADA

**Risk-Aware Decision Agent** — async Python service: ingest market events → verified calc → reasoner proposals → risk-gated decision → audit trail → human review.

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

MIT — see [LICENSE](LICENSE).
