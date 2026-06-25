# Codebase Improvement Plan: RADA (Risk-Aware Decision Agent)

## Executive Summary

- **Current State**: Solid **alpha-stage** system with clean architecture, excellent interface abstractions, good async patterns, and extensive documentation. All core flows (ingest → calc → reason → risk-gate → persist → reflect) are wired end-to-end. However, many components remain **stub/toy implementations**, the dual-metrics system is confusing, and testing lacks real E2E coverage.
- **Key Strengths**: Clean `ABC` interface contracts, factory-driven dependency injection, append-only audit trail, human feedback queue, multi-provider LLM strategy, risk-gated decision pipeline, offline reflection path.
- **Top Gaps**:
  1. **Stub saturation** — MCTS, search, reflection auditor, risk optimizer, game theory, and policy updater are all stubs with no real intelligence
  2. **No real learning loop** — Reflection loop and policy updates are simulated; no actual RLHF or online learning
  3. **Dual metrics systems** — `observability/metrics.py` and `utils/metrics.py` overlap in responsibility
  4. **Testing lacks realism** — No live API server E2E tests, no performance/stress tests, mock-heavy unit tests
  5. **Security is bare-minimum** — Single API key, no RBAC, no rate limiting, no JWT
  6. **Operational maturity gaps** — No structured error taxonomy, no alerting rules, no SLI/SLO framework

---

## Level 1: Architecture & Design

### Observation 1: Dual Metrics System Creates Confusion
Two separate metrics registries exist: `rada/observability/metrics.py` (Prometheus registry with counters + histograms) and `rada/utils/metrics.py` (flat counters + gauges + OTel hooks). They track overlapping signals (`rada_decisions_total` vs `rada_decisions_processed_total`).

**Recommendation**: Consolidate into a single `ObservabilityProvider` interface with one Prometheus-backed implementation. The `utils/metrics.py` convenience functions should delegate to the single registry. **Effort**: Medium (1-2 days) — affects ~10 files. **Impact**: High — eliminates confusion and double-counting.

### Observation 2: OpenTelemetry is a No-Op Stub
tracer.py implements a `_NoOpTracer` that never exports spans. `RADA_OTEL_ENABLED=true` only prints to stdout.

**Recommendation**: Replace with a real OTel SDK integration that exports to a configurable OTLP endpoint (e.g., Jaeger, Grafana Tempo, or Azure Monitor). Add span attributes consistently across all spans. **Effort**: Medium (3-5 days). **Impact**: Medium — critical for production distributed tracing.

### Observation 3: Three Separate SQLite Databases
The system uses separate SQLite files for decisions (`rada.db`), audit events (`rada_audit.db`), and feedback (`rada_feedback.db`). Each has independent schema creation in `ensure_ready()` with no migration management.

**Recommendation**: Either consolidate into a single database with proper foreign keys, or keep separate DBs but introduce a lightweight migration framework (Alembic already in `dev` dependencies). Add `on delete cascade` semantics and unified connection pooling. **Effort**: Medium (2-3 days). **Impact**: Medium — simplifies operational management.

### Observation 4: `run_bootstrap_once()` Duplication
`run_bootstrap_once()` and `run_bootstrap_once_inmemory()` are nearly identical except the second hardcodes `"inmemory"`.

**Recommendation**: Remove the duplicated function and have callers pass `event_bus_mode="inmemory"` to the single `run_bootstrap_once()`. **Effort**: Low (30 min). **Impact**: Low — code hygiene.

---

## Level 2: Features & Scalability

### Feature Gap 1: Real Reflection/Learning Pipeline
The `ReflectionLoop` uses `StubAuditor` (always returns 0.85 faithfulness) and `ReflectionPolicyUpdater` (running mean of faithfulness scores only). No actual policy improvement or model fine-tuning occurs on the reflection path.

**Recommendation**: Implement a real auditor (faithfulness scoring via LLM-as-judge or embedding similarity) and connect the reflection loop to the existing `UnslothTrainer` for periodic LoRA fine-tuning. This closes the data flywheel gap. **Reference**: [HuggingFace TRL's DPO trainer](https://github.com/huggingface/trl) for RLHF patterns. **Effort**: High (2-4 weeks). **Impact**: Transformative — turns RADA into a true learning system.

### Feature Gap 2: Toy MCTS With No Real Simulation
`MCTSPlanner` runs 64 deterministic iterations with no stochastic simulation, no UCB exploration, and no environment model. The `TrinityPolicyStub` proposes only 3 fixed candidates.

**Recommendation**: Implement proper UCB1 selection, a lightweight simulation environment (could use the existing `VectorizedEnv` stub base), and configurable iteration budgets. Add a `WarmStartMCTS` variant that seeds from the reasoner's proposal. **Effort**: Medium (1-2 weeks). **Impact**: High — unlocks meaningful search-based decision improvement.

### Feature Gap 3: No Streaming LLM Support
All LLM adapters use blocking `complete()` calls. No streaming for real-time UX or progressive reasoning.

**Recommendation**: Add a `stream_complete()` method to `BaseLLMBackend` and `LLMProvider` interfaces. Implement SSE-based streaming in the FastAPI `/ingest` endpoint for progressive decision trace delivery. **Effort**: Medium (3-5 days). **Impact**: Medium — improves UX for dashboards.

### Feature Gap 4: Limited Calculation Engine
Only 3 calc functions: CVaR, position sizing, drawdown. No Greeks, no portfolio correlation, no volatility regime detection.

**Recommendation**: Extend `calc/engine.py` with: (1) volatility regime classifier (low/medium/high), (2) simple moving average crossover signal, (3) RSI-based overbought/oversold signal, (4) portfolio-level correlation tracker. Each new function follows the existing `CalcResult` contract. **Effort**: Low-Medium (3-5 days). **Impact**: Medium — enriches decision context.

### Feature Gap 5: No Rate Limiting or Request Throttling
The `/ingest` endpoint has no rate limiting. A burst of events could overwhelm the pipeline.

**Recommendation**: Add FastAPI middleware for token-bucket rate limiting (per IP or per API key). Use Redis-backed storage for distributed rate limiting. **Effort**: Low (1 day). **Impact**: High — prevents cascading failures.

### Feature Gap 6: Dashboard Lacks Real-Time Updates
The React dashboard polls every 8 seconds for pending feedback. No WebSocket support.

**Recommendation**: Add a WebSocket endpoint (`/ws/events`) for streaming decision updates, metrics, and feedback queue changes. Update the React dashboard to use `EventSource` or native WebSocket. **Effort**: Medium (3-5 days). **Impact**: Medium — improves operator experience.

---

## Level 3: Code-Level & Integration Improvements

### Improvement 1: Structured Error Handling
The codebase uses broad `except Exception` in several critical paths (`_complete_with_fallback`, `_consumer` in reflections, `AuditWriter._consumer`). Errors are logged but not categorized.

**Recommendation**: Define a `RADAError` base exception hierarchy:
- `ProviderError` (LLM connection/timeout/runtime)
- `StoreError` (DB connection/constraint violations)
- `PolicyViolationError` (risk gate breaches)
- `CalcError` (insufficient data / numerical instability)

Chain-specific catch blocks in all async consumers. **Effort**: Medium (2-3 days). **Impact**: High — enables structured alerting and debugging.

### Improvement 2: Configuration Schema Validation
`RuntimeSettings` is a dataclass with raw env var reads. `LLMConfig` and `PolicyProfile` use Pydantic. Mix of validation approaches.

**Recommendation**: Convert `RuntimeSettings` to a Pydantic `BaseSettings` model for env var validation, type coercion, and `.env` file support. Unify all config models under a single configs schema hierarchy. **Effort**: Low (1 day). **Impact**: Medium — catches misconfiguration at startup.

### Improvement 3: Missing Async Connection Pooling for SQLite
`SQLiteDecisionStore`, `AuditStore`, and `FeedbackStore` each open/close a new connection on every operation via `sqlite3.connect()` inside `asyncio.to_thread()`.

**Recommendation**: Use `aiosqlite` for native async SQLite with connection pooling/reuse. This avoids the thread-pool overhead per query. **Effort**: Low (1-2 days). **Impact**: Medium — improves throughput under load.

### Improvement 4: CI/CD Pipeline Enhancement
Only a Makefile target for `test` exists. No visible CI config (despite the badge referencing ci.yml).

**Recommendation**: Ensure the CI pipeline runs:
- `ruff check` linting
- `pytest tests/unit -m "not gpu and not integration"`
- `pytest tests/integration -m integration` (with mock LLM)
- Container build & smoke test
- Security scan (bandit, safety)

Add GitHub Actions workflow with matrix testing for Python 3.11 and 3.12. **Effort**: Low (1 day). **Impact**: High — catches regressions before merge.

### Improvement 5: API Response Standardization
Some endpoints return `dict`, some use Pydantic models. Error responses are not standardized.

**Recommendation**: Create a standard `APIResponse[T]` envelope: `{"status": "ok"|"error", "data": T, "error": {...}}`. Use FastAPI exception handlers to standardize all 4xx/5xx responses. **Effort**: Low (1 day). **Impact**: Medium — improves API consistency.

### Improvement 6: Missing Cache Layer for Model Resolution
`resolve_model_path()` downloads from HuggingFace every time if not cached. No TTL or invalidation.

**Recommendation**: Add a weak-TTL in-memory cache for resolved model paths. Consider a `ModelCacheManager` that periodically checks disk usage and purges unused models. **Effort**: Low (1 day). **Impact**: Low-Medium — speeds up cold starts.

### Improvement 7: Inconsistent Audit Writer Fallback in `_lifespan`
In main.py, the `_lifespan` function creates `audit_writer` and passes it to `build_decision_loop()`. However, `_get_store()` in `audit/api.py` falls back to creating a new `AuditStore()` if `request.app.state.audit_store` is None. This pattern allows silent misconfiguration.

**Recommendation**: Use `@property`-based dependency injection on `request.app` with `raise` on missing state. Or use FastAPI's `Depends()` with a proper provider function. **Effort**: Low (few hours). **Impact**: Low — defensive programming.

---

## Comparable Projects

| Project | Why Similar | What RADA Could Learn |
|---|---|---|
| **[OpenBB Terminal](https://github.com/OpenBB-finance/OpenBBTerminal)** | Open-source investment research platform with decision support | Rich calc library (100+ indicators), plugin-based data providers, community-contributed policies |
| **[Kelp](https://github.com/Kelp-X-Platform/kelp)** | Risk-aware market making agent with audit trails | Production-grade MCTS implementation, real-time position management, risk engine with VaR/CVaR |
| **[Hummingbot](https://github.com/hummingbot/hummingbot)** | Open-source market making framework with strategy scripts | Strategy-as-code pattern, backtesting framework, paper trading mode |
| **[LangGraph](https://github.com/langchain-ai/langgraph)** | Agent orchestration with human-in-the-loop | Graph-based state machine for decision pipelines, conditional branching, checkpoint/rollback |
| **[ZenML](https://github.com/zenml-io/zenml)** | ML pipeline orchestration with metadata tracking | Pipeline artifact tracking, experiment comparison, model registry integration |

---

## Gap Analysis: Current → Production-Ready

| Dimension | Current State | Target State | Path to Close |
|---|---|---|---|
| **Learning Loop** | Stub auditor, no fine-tuning | Automated reflection → LoRA fine-tuning → policy update | Connect `ReflectionLoop` → `UnslothTrainer` → policy checkpoint |
| **Search Quality** | 64-iteration deterministic MCTS | Configurable MCTS with UCB1 + stochastic simulation | Full MCTS implementation with proper exploration/exploitation |
| **Error Management** | Broad `except Exception` | Structured error hierarchy + alerting | `RADAError` base classes + centralized error handler |
| **Testing Depth** | 33 unit + 22 integration (mock-heavy) | E2E tests + stress tests + property-based tests | Add `test_e2e_api.py`, `test_performance_load.py`, Hypothesis tests |
| **Security** | Single API key | RBAC + JWT + rate limiting + per-tenant isolation | JWT middleware, token-bucket rate limiter, tenant store |
| **Observability** | Dual metrics, no real OTel | Unified Prometheus + real OTLP export + dashboards | Consolidate metrics, real OTel SDK, Grafana dashboards |
| **Data Platform** | SQLite in production (prod.yml) | TimescaleDB for hot path + S3/Parquet for cold | Production deploy should default to TimescaleDB |
| **Frontend** | Basic React dashboard with polling | WebSocket real-time + auth UI + advanced filtering | Add WS endpoint, auth flows, richer data visualization |

---

## Priority Roadmap (Phased)

### Phase 1 — Quick Wins (1-2 weeks, high impact per effort)
1. **Fix dual metrics** — Consolidate into one registry [1-2 days]
2. **Structured error hierarchy** — Define `RADAError` + chained handlers [2-3 days]
3. **Rate limiting middleware** — Token-bucket on `/ingest` [1 day]
4. **CI/CD pipeline** — Full GitHub Actions workflow [1 day]
5. **API response standardization** — Unified response envelope [1 day]
6. **Remove `run_bootstrap_once` duplication** [30 min]
7. **Convert `RuntimeSettings` to Pydantic** [1 day]

### Phase 2 — Mid-Term (1-2 months, significant impact)
8. **Real MCTS implementation** — UCB1 + simulation environment [1-2 weeks]
9. **Extend calc engine** — Add 4-5 new financial indicators [3-5 days]
10. **Async SQLite via `aiosqlite`** — Connection pooling [1-2 days]
11. **Real OTel SDK integration** — Export to OTLP endpoint [3-5 days]
12. **Streaming LLM support** — SSE endpoint for progressive traces [3-5 days]
13. **WebSocket dashboard support** — Real-time dashboard updates [3-5 days]
14. **Database migration management** — Alembic for all stores [2-3 days]

### Phase 3 — Long-Term (3+ months, transformative)
15. **Real reflection + learning loop** — Connect auditor → trainer → policy [2-4 weeks]
16. **RBAC + JWT authentication** — Multi-tenant security [1-2 weeks]
17. **E2E + load testing suite** — Full CI integration [1-2 weeks]
18. **TimescaleDB production default** — Hot path performance [1 week]
19. **Advanced dashboard** — Real-time charts, WebSocket, decision replay [2-3 weeks]
20. **Plugin system for calc functions** — Community-extensible indicators [2-3 weeks]