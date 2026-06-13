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
  <a href="https://github.com/artaasd95/RADA/stargazers"><img src="https://img.shields.io/github/stars/artaasd95/RADA?style=social" alt="GitHub stars" /></a>
</p>

<p align="center">
  <img src="assets/logo.png" alt="RADA Logo" width="120" />
</p>

# RADA

**RADA (Risk-Aware Decision Agent)** is a production-oriented decision intelligence service that converts market events into auditable, risk-gated actions.

It is built for systems where **traceability, safety constraints, and operator control** matter more than raw model output.

<p align="center">
  <strong>Ingest events. Enforce risk. Keep full auditability. Stay human-supervised.</strong>
</p>

<p align="center">
  <a href="#quickstart-in-60-seconds">Quickstart</a> •
  <a href="#feature-highlights">Features</a> •
  <a href="#dashboards">Dashboards</a> •
  <a href="#api-surface">API</a> •
  <a href="#documentation">Docs</a>
</p>

## Feature Highlights

- **Risk-gated decision engine:** calc verification and risk checks run before decisions are persisted.
- **Full audit timeline:** each decision can be replayed through `/audit/decision/{decision_id}` or exported with `/audit/export`.
- **Human review queue:** auto-flagged decisions can be approved/rejected through Streamlit and API workflows.
- **Production-ready operations:** Docker Compose stack, health checks, metrics endpoint, and deploy check script.
- **Model portability:** local Qwen by default, plus BYOK providers for OpenAI-compatible cloud or self-hosted inference.
- **Separated hot path and learning path:** reflection/export/training are asynchronous and do not block ingest.

## Why RADA?

RADA is for teams that need a decision system, not just a model call. It is optimized for traceability, operator review, and explicit risk control around every output.

It intentionally serves two roles:

- **Core library:** reusable Python components for loops, risk gates, reasoners, audit trails, and storage.
- **Standalone showcase:** a complete FastAPI service, dashboards, configs, and scripts that demonstrate how those components run end to end.

If you want to embed RADA into a larger platform, extend `src/rada/`. If you want a working reference stack, run this repository as-is and treat it as the showcase deployment.

## Why Teams Choose RADA

| Capability | RADA Advantage |
|---|---|
| **Decision safety** | Risk checks and policy gating run before persistence. |
| **Auditability** | Full decision lifecycle retrieval and NDJSON export. |
| **Operator oversight** | Human feedback queue with explicit approve/reject flow. |
| **Deployment flexibility** | Local dev, Compose production, optional monitoring overlays. |
| **Model strategy** | Mock-first reliability with optional BYOK providers. |

## Built For Teams That Need

- **Trust and governance:** explainable decisions and immutable audit events.
- **Operator control:** manual approval workflows for sensitive actions.
- **Reliable iteration:** run with deterministic mock reasoning, then swap providers when ready.
- **Data flywheel readiness:** export production decisions into reflection/training pipelines.

## High-Value Use Cases

- **Risk-aware decision automation pilots** where every output must be inspectable before trust is granted.
- **Human-supervised AI operations** that require queue-based review for flagged or low-confidence actions.
- **Model evaluation and improvement loops** that export real runtime traces for offline training/refinement.
- **Regulated or compliance-sensitive domains** where observability and audit trails are mandatory.

## Quickstart in 60 Seconds

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
ollama pull qwen2.5:0.5b
uvicorn rada.main:app --reload
```

Runtime default:

- local-first real reasoner via Ollama and `qwen2.5:0.5b`
- BYOK fallback via `configs/llm_cloud.yaml` when `OPENAI_API_KEY` is set
- mock reasoner only for tests and explicit mock mode

Then send one event:

```bash
curl -X POST "http://localhost:8000/ingest" \
  -H "Content-Type: application/json" \
  -d "{\"symbol\":\"BTCUSD\",\"price\":60000,\"volume\":1.0,\"timestamp\":\"2026-06-01T12:00:00Z\"}"
```

Then inspect the full chain:

```bash
curl "http://localhost:8000/audit/decision/<decision_id>"
```

Open API documentation:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## System Flow

```text
MarketEvent -> Calc verification -> Reasoner proposal -> Decision/risk gate
            -> Persist decision -> Audit event stream -> Human feedback
                                      |
                                      +-> Reflection/export/training (async/off-path)
```

## Repository Layout

```text
src/rada/              # Core runtime: FastAPI, loops, calc, storage, audit, feedback
apps/streamlit/        # Streamlit operator dashboard (review queue + metrics)
dashboard/             # React dashboard (Vite + React Query + Router)
scripts/               # Export, training, comparison, and ops CLIs
docs/                  # Architecture, runbooks, monitoring, models, training docs
configs/               # Runtime, monitoring, and model configuration files
tests/                 # Unit + integration coverage
```

## Quickstart (Local Development)

### 1) Install and run API

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate

pip install -e ".[dev]"
ollama pull qwen2.5:0.5b
uvicorn rada.main:app --reload
```

API starts on `http://localhost:8000`.

### 2) Smoke test ingest

```bash
curl -X POST "http://localhost:8000/ingest" \
  -H "Content-Type: application/json" \
  -d "{\"symbol\":\"BTCUSD\",\"price\":60000,\"volume\":1.0,\"timestamp\":\"2026-06-01T12:00:00Z\"}"
```

In development mode, API key auth is optional unless `RADA_API_KEY` is set.

### 3) Run tests and lint

```bash
pytest tests/unit -m "not gpu and not integration"
pytest tests/integration -m integration
ruff check .
```

## Quickstart (Production via Docker Compose)

```bash
cp env.example.prod .env
docker compose -f docker-compose.prod.yml up -d --build
./scripts/deploy_check.sh
```

Production stack includes:

- `rada` FastAPI service
- `postgres` and `redis`
- `rada-dashboard` (React UI, served on `http://localhost:5173`)

Optional observability overlay:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.observability.yml up -d
```

## Dashboards

RADA includes two operator interfaces:

- **React dashboard:** system overview, decisions, review queue, and audit pages.
- **Streamlit dashboard:** lightweight review queue and in-process metrics inspection.

### React dashboard

```bash
cd dashboard
npm install
npm run dev
```

Set `VITE_API_URL` to point at the API if needed.

### Streamlit review dashboard

```bash
pip install -e ".[ui]"
streamlit run apps/streamlit/dashboard.py
```

Set `RADA_API_URL` (and `RADA_API_KEY` if auth is enabled).

## UI Improvement Plan

The current UI is intentionally lightweight and does not require auth. The next iteration should focus on operator experience rather than identity plumbing.

1. Add a richer decision detail page that combines rationale, audit events, verified context, and review status.
2. Improve review queue filtering by symbol, confidence, risk state, and age.
3. Add trend charts for ingest volume, auto-flag rate, risk-gate rejections, and review backlog.
4. Make the audit timeline easier to scan with grouped event cards and delta-oriented visual cues.
5. Upgrade the React dashboard visual language so it reads like an operations console, not a scaffold.
6. Keep both dashboards auth-free for trusted internal environments until there is a separate access-control requirement.

## Visual Preview

RADA ships branding assets in `assets/`:

- `assets/banner.png` (repository banner)
- `assets/logo.png` (project logo)

These are ready for GitHub social previews, release notes, and docs pages.

## API Surface

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness |
| `GET /metrics` | Prometheus-style metrics |
| `GET /metrics/json` | JSON debug snapshot of metrics |
| `POST /ingest` | Process a single `MarketEvent` through the decision pipeline |
| `POST /bootstrap-demo` | One-shot bootstrap/demo decision |
| `GET /audit/decision/{decision_id}` | Full audit chain for one decision |
| `GET /audit/export` | NDJSON export over a time range |
| `POST /feedback/submit` | Submit human decision feedback |
| `GET /feedback/pending` | List pending/flagged feedback |

`/ingest`, `/audit/*`, and `/feedback/*` use API key dependency checks. In production, `RADA_API_KEY` is required.

## Configuration Highlights

| Variable | Default | Description |
|---|---|---|
| `RADA_ENV` | `dev` | Environment mode (`production` enables strict API key requirement). |
| `RADA_DATA_STORE_MODE` | `sqlite` | `inmemory`, `sqlite`, or `timescale`. |
| `RADA_SQLITE_URL` | `sqlite:///./rada.db` | SQLite DSN for local/dev. |
| `RADA_DATABASE_URL` | _empty_ | Required when `RADA_DATA_STORE_MODE=timescale`. |
| `RADA_EVENT_BUS_MODE` | `inmemory` | Event bus strategy (`inmemory`/`redis` by deployment). |
| `RADA_REASONER_MODE` | `real` | Runtime reasoner mode (`real`, `mock`, `scenario`, `noop`). |
| `RADA_API_KEY` | _empty_ | API key for protected endpoints. |
| `RADA_LLM_CONFIG_PATH` | `configs/llm_ollama.yaml` | Primary runtime LLM config path. |
| `RADA_OTEL_ENABLED` | `false` | Enables optional observability hooks. |
| `RADA_API_URL` | `http://localhost:8000` | Streamlit API target. |

See `.env.example` and `env.example.prod` for full templates.

## Data Export and Training Workflows

RADA keeps training workflows off the online decision path while preserving data lineage.

Export reflection data (off hot path):

```bash
python scripts/export_reflection.py --from-db --output-dir ./tmp/export
```

Synthetic export smoke test:

```bash
python scripts/export_reflection.py --synthetic-count 5
```

Run search fixture demo:

```bash
python examples/search_demo.py
```

Train adapters (stub backend for CI/smoke):

```bash
python scripts/reflection_train.py --backend stub --model-id qwen3-0.6b --data benchmarks/training/toy_feedback.jsonl
```

Pre/post training comparison:

```bash
python scripts/compare_pre_post_train.py --model-id qwen3-0.6b --fixtures benchmarks/training/toy_feedback.jsonl
```

## Project Maturity

- **Current release:** `v1.0.0`
- **Core status:** production-oriented decision path, audit APIs, feedback APIs, and dashboards are in place.
- **Testing:** extensive `tests/unit` and `tests/integration` coverage with CI checks.

## Documentation

- [Why RADA?](docs/why-rada.md)
- [Documentation index](docs/index.md)
- [Architecture overview](docs/architecture-overview.md)
- [Production runbook](docs/runbook-production.md)
- [Monitoring](docs/monitoring.md)
- [LLM integration (BYOK)](docs/llm-integration.md)
- [Training](docs/training.md)
- [Data platform](docs/data-platform.md)

## Contributing

Contributions are welcome. Start with:

- [Contributing guide](CONTRIBUTING.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)

For impactful contributions, prioritize:

- better risk policies and reasoner strategies,
- richer operator UX in dashboards,
- stronger benchmark/evaluation suites,
- production observability enhancements.

## License

Apache License 2.0. See [LICENSE](LICENSE).
