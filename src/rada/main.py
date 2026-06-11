"""Main FastAPI entrypoint for RADA."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI, Request, Response

from rada.audit.api import router as audit_router
from rada.audit.store import AuditStore
from rada.audit.writer import AuditWriter
from rada.adapters.scenario_reasoner import ScenarioReasoner
from rada.core.decision_loop import (
    DecisionLoop,
    HoldPolicy,
    NoOpReasoner,
    PassThroughRiskOptimizer,
)
from rada.feedback.auto_flag import build_flag_feedback, should_auto_flag
from rada.core.reasoner_loop import ReasonerLoop
from rada.core.reflection_loop import ReflectionLoop
from rada.data.bus import build_event_bus
from rada.data.ingestion import synthetic_market_events
from rada.data.storage import InMemoryDecisionStore, SQLiteDecisionStore
from rada.data.timescale_store import TimescaleDecisionStore
from rada.feedback.api import router as feedback_router
from rada.feedback.store import FeedbackStore
from rada.interfaces import BaseDataStore
from rada.observability.metrics import get_metrics
from rada.schemas import Decision, MarketEvent
from rada.utils.metrics import (
    get_metrics_snapshot,
    record_decision_processed,
    render_prometheus_text,
)


@dataclass(slots=True)
class RuntimeSettings:
    event_bus_mode: str = os.getenv("RADA_EVENT_BUS_MODE", "inmemory")
    data_store_mode: str = os.getenv("RADA_DATA_STORE_MODE", "sqlite")
    database_url: str = os.getenv("RADA_DATABASE_URL", "postgresql://rada:rada@localhost:5432/rada")
    sqlite_url: str = os.getenv("RADA_SQLITE_URL", "sqlite:///./rada.db")
    audit_db_path: str = os.getenv("RADA_AUDIT_DB_PATH", "./rada_audit.db")
    feedback_db_path: str = os.getenv("RADA_FEEDBACK_DB_PATH", "./rada_feedback.db")
    reasoner_mode: str = os.getenv("RADA_REASONER_MODE", "mock")
    llm_config_path: str = os.getenv("RADA_LLM_CONFIG_PATH", "configs/llm_mock.yaml")


def build_data_store(settings: RuntimeSettings) -> BaseDataStore:
    mode = settings.data_store_mode.lower().strip()

    if mode == "inmemory":
        return InMemoryDecisionStore()
    if mode == "sqlite":
        return SQLiteDecisionStore(settings.sqlite_url)
    if mode == "timescale":
        return TimescaleDecisionStore(settings.database_url)

    raise ValueError(f"Unsupported RADA_DATA_STORE_MODE={settings.data_store_mode!r}")


def build_reasoner(settings: RuntimeSettings):
    mode = settings.reasoner_mode.lower().strip()
    if mode in {"mock", "scenario"}:
        return ScenarioReasoner()
    return NoOpReasoner()


def build_llm_provider(settings: RuntimeSettings):
    """Optional BYOK LLM provider for runtime inference (mock default)."""
    from pathlib import Path

    from rada.llm_integration.factory import create_llm_provider

    path = Path(settings.llm_config_path)
    if not path.exists():
        path = Path("configs/llm_mock.yaml")
    return create_llm_provider(path)


def build_decision_loop(
    store: BaseDataStore,
    audit_writer: AuditWriter | None = None,
    settings: RuntimeSettings | None = None,
) -> DecisionLoop:
    settings = settings or RuntimeSettings()
    reasoner = build_reasoner(settings)
    return DecisionLoop(
        reasoner=reasoner,
        policy=HoldPolicy(),
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=store,
        reasoner_loop=ReasonerLoop(reasoner),
        audit_writer=audit_writer,
    )


async def run_bootstrap_once(
    event_count: int = 1,
    settings: RuntimeSettings | None = None,
) -> Decision:
    settings = settings or RuntimeSettings()

    event_bus = await build_event_bus(settings.event_bus_mode)
    store = build_data_store(settings)

    loop = build_decision_loop(store)

    async for event in synthetic_market_events(count=event_count):
        await event_bus.enqueue(event)

    first_event = await event_bus.dequeue()
    decision = await loop.process_one(first_event)
    record_decision_processed()
    return decision


async def run_bootstrap_once_inmemory(event_count: int = 1) -> Decision:
    event_bus = await build_event_bus("inmemory")
    store = InMemoryDecisionStore()

    loop = build_decision_loop(store)

    async for event in synthetic_market_events(count=event_count):
        await event_bus.enqueue(event)

    first_event = await event_bus.dequeue()
    decision = await loop.process_one(first_event)
    record_decision_processed()
    return decision


@asynccontextmanager
async def _lifespan(app: FastAPI):
    settings = RuntimeSettings()
    store = build_data_store(settings)
    if hasattr(store, "ensure_ready"):
        await store.ensure_ready()  # type: ignore[attr-defined]

    audit_store = AuditStore(db_path=settings.audit_db_path)
    await audit_store.ensure_ready()
    audit_writer = AuditWriter(store=audit_store)
    audit_writer.start()

    feedback_store = FeedbackStore(db_path=settings.feedback_db_path)
    await feedback_store.ensure_ready()

    reflection = ReflectionLoop(data_store=store)
    reflection.start()

    app.state.reflection_loop = reflection
    app.state.data_store = store
    app.state.audit_store = audit_store
    app.state.audit_writer = audit_writer
    app.state.feedback_store = feedback_store
    app.state.decision_loop = build_decision_loop(store, audit_writer, settings)
    app.state.llm_provider = build_llm_provider(settings)

    yield

    await reflection.stop()
    await audit_writer.stop()
    close = getattr(store, "close", None)
    if close is not None:
        await close()


app = FastAPI(title="RADA", version="1.0.0", lifespan=_lifespan)
app.include_router(audit_router)
app.include_router(feedback_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness probe for local/dev stack health checks."""
    return {"status": "ok"}


@app.get("/metrics", tags=["system"])
async def metrics() -> Response:
    """Prometheus-style metrics snapshot."""
    obs_body = get_metrics().render_prometheus()
    legacy_body = render_prometheus_text()
    return Response(content=obs_body + legacy_body, media_type="text/plain; version=0.0.4")


@app.get("/metrics/json", tags=["system"])
async def metrics_json() -> dict[str, object]:
    """JSON metrics snapshot for debugging."""
    return {"legacy": get_metrics_snapshot(), "observability": get_metrics().snapshot()}


@app.post("/ingest", tags=["demo"])
async def ingest_event(event: MarketEvent, request: Request) -> dict[str, str]:
    """Ingest one market event through the decision pipeline."""
    loop: DecisionLoop = request.app.state.decision_loop
    reflection: ReflectionLoop = request.app.state.reflection_loop
    feedback_store: FeedbackStore = request.app.state.feedback_store
    audit_writer: AuditWriter = request.app.state.audit_writer

    decision = await loop.process_one(event)
    reflection.enqueue(decision)

    flag, reason = should_auto_flag(decision)
    if flag:
        await feedback_store.submit(build_flag_feedback(decision, reason))
        from rada.audit.schemas import AuditEventType

        audit_writer.emit(
            AuditEventType.HUMAN_FEEDBACK,
            decision_id=decision.decision_id,
            payload_after={"auto_flag": True, "reason": reason},
        )

    record_decision_processed()
    return {
        "decision_id": decision.decision_id,
        "direction": decision.proposed_action.direction.value,
        "flagged": flag,
    }


@app.post("/bootstrap-demo", tags=["demo"])
async def bootstrap_demo() -> dict[str, str]:
    decision = await run_bootstrap_once(event_count=1)
    return {"decision_id": decision.decision_id}
