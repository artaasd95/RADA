"""Main FastAPI entrypoint for RADA."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from fastapi import FastAPI

from rada.core.decision_loop import DecisionLoop, HoldPolicy, NoOpReasoner, PassThroughRiskOptimizer
from rada.data.ingestion import synthetic_market_events
from rada.data.storage import InMemoryDecisionStore, SQLiteDecisionStore
from rada.schemas import Decision, MarketEvent


@dataclass(slots=True)
class RuntimeSettings:
    event_bus_mode: str = os.getenv("RADA_EVENT_BUS_MODE", "inmemory")
    sqlite_url: str = os.getenv("RADA_SQLITE_URL", "sqlite:///./rada.db")


class InMemoryEventBus:
    def __init__(self) -> None:
        self._queue: asyncio.Queue[MarketEvent] = asyncio.Queue()

    async def enqueue(self, event: MarketEvent) -> None:
        await self._queue.put(event)

    async def dequeue(self) -> MarketEvent:
        return await self._queue.get()


class RedisEventBus:
    """Minimal Redis event bus wrapper used only when explicitly enabled."""

    def __init__(self, redis_url: str) -> None:
        import redis.asyncio as redis

        self._channel = "rada:events"
        self._client = redis.from_url(redis_url)

    async def enqueue(self, event: MarketEvent) -> None:
        await self._client.rpush(self._channel, event.model_dump_json())

    async def dequeue(self) -> MarketEvent:
        _, payload = await self._client.blpop(self._channel)
        return MarketEvent.model_validate_json(payload)


async def _build_event_bus(settings: RuntimeSettings) -> InMemoryEventBus | RedisEventBus:
    if settings.event_bus_mode.lower() == "redis":
        redis_url = os.getenv("RADA_REDIS_URL", "redis://localhost:6379/0")
        try:
            return RedisEventBus(redis_url)
        except Exception:
            return InMemoryEventBus()
    return InMemoryEventBus()


async def run_bootstrap_once(event_count: int = 1, settings: RuntimeSettings | None = None) -> Decision:
    settings = settings or RuntimeSettings()

    event_bus = await _build_event_bus(settings)
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
    return await loop.process_one(first_event)


async def run_bootstrap_once_inmemory(event_count: int = 1) -> Decision:
    event_bus = InMemoryEventBus()
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
    return await loop.process_one(first_event)


app = FastAPI(title="RADA", version="0.1.0")


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Liveness probe for local/dev stack health checks."""
    return {"status": "ok"}


@app.post("/bootstrap-demo", tags=["demo"])
async def bootstrap_demo() -> dict[str, str]:
    decision = await run_bootstrap_once(event_count=1)
    return {"decision_id": decision.decision_id}
