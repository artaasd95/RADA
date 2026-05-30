"""Main FastAPI entrypoint for RADA."""

from __future__ import annotations

import os
from dataclasses import dataclass

from fastapi import FastAPI, Response

from rada.core.decision_loop import DecisionLoop, HoldPolicy, NoOpReasoner, PassThroughRiskOptimizer
from rada.data.bus import build_event_bus
from rada.data.ingestion import synthetic_market_events
from rada.data.storage import InMemoryDecisionStore, SQLiteDecisionStore
from rada.schemas import Decision
from rada.utils.metrics import get_metrics_snapshot, record_decision_processed, render_prometheus_text


@dataclass(slots=True)
class RuntimeSettings:
    event_bus_mode: str = os.getenv("RADA_EVENT_BUS_MODE", "inmemory")
    sqlite_url: str = os.getenv("RADA_SQLITE_URL", "sqlite:///./rada.db")


async def run_bootstrap_once(event_count: int = 1, settings: RuntimeSettings | None = None) -> Decision:
    settings = settings or RuntimeSettings()

    event_bus = await build_event_bus(settings.event_bus_mode)
    store = SQLiteDecisionStore(settings.sqlite_url)

    loop = DecisionLoop(
        reasoner=NoOpReasoner(),
        policy=HoldPolicy(),
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=store,
    )

    async for event in synthetic_market_events(count=event_count):
        await event_bus.enqueue(event)

    first_event = await event_bus.dequeue()
    decision = await loop.process_one(first_event)
    record_decision_processed()
    return decision


async def run_bootstrap_once_inmemory(event_count: int = 1) -> Decision:
    event_bus = await build_event_bus("inmemory")
    store = InMemoryDecisionStore()

    loop = DecisionLoop(
        reasoner=NoOpReasoner(),
        policy=HoldPolicy(),
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=store,
    )

    async for event in synthetic_market_events(count=event_count):
        await event_bus.enqueue(event)

    first_event = await event_bus.dequeue()
    decision = await loop.process_one(first_event)
    record_decision_processed()
    return decision


app = FastAPI(title="RADA", version="0.1.0")


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness probe for local/dev stack health checks."""
    return {"status": "ok"}


@app.get("/metrics", tags=["system"])
async def metrics() -> Response:
    """Prometheus-style metrics snapshot."""
    return Response(content=render_prometheus_text(), media_type="text/plain; version=0.0.4")


@app.get("/metrics/json", tags=["system"])
async def metrics_json() -> dict[str, int | float]:
    """JSON metrics snapshot for debugging."""
    return get_metrics_snapshot()


@app.post("/bootstrap-demo", tags=["demo"])
async def bootstrap_demo() -> dict[str, str]:
    decision = await run_bootstrap_once(event_count=1)
    return {"decision_id": decision.decision_id}
