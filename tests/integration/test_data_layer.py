from datetime import UTC, datetime

import pytest

from rada.core.decision_loop import DecisionLoop, HoldPolicy, NoOpReasoner, PassThroughRiskOptimizer
from rada.data.analytics import RollingPnLTracker
from rada.data.bus import InMemoryEventBus
from rada.data.quality import ingest_with_lineage
from rada.data.storage import InMemoryDecisionStore, SQLiteDecisionStore
from rada.schemas import MarketEvent


@pytest.mark.integration
@pytest.mark.asyncio
async def test_data_layer_bus_ingest_persist_analytics(tmp_path) -> None:
    """Bus ingest → persist → analytics read (SQLite stand-in for Timescale in CI)."""
    bus = InMemoryEventBus()
    store = SQLiteDecisionStore(f"sqlite:///{tmp_path / 'data_layer.db'}")
    loop = DecisionLoop(
        reasoner=NoOpReasoner(),
        policy=HoldPolicy(),
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=store,
    )
    tracker = RollingPnLTracker(window=5)

    raw = MarketEvent(
        symbol="BTCUSD",
        price=52000.0,
        volume=1.5,
        timestamp=datetime(2026, 5, 30, tzinfo=UTC),
    )
    event, lineage = await ingest_with_lineage(raw, source="integration-test")
    await bus.enqueue(event)

    dequeued = await bus.dequeue()
    decision = await loop.process_one(dequeued)
    restored = await store.get_decision(decision.decision_id)
    rolling = tracker.record(decision)

    assert lineage.checksum
    assert restored is not None
    assert restored.decision_id == decision.decision_id
    assert isinstance(rolling, float)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fake_ingest_through_inmemory_bus() -> None:
    from rada.data.ingestion import synthetic_market_events

    bus = InMemoryEventBus()
    store = InMemoryDecisionStore()
    loop = DecisionLoop(
        reasoner=NoOpReasoner(),
        policy=HoldPolicy(),
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=store,
    )

    count = 3
    async for event in synthetic_market_events(count=count, seed=99):
        validated, _ = await ingest_with_lineage(event, source="fake-ingest")
        await bus.enqueue(validated)

    decisions = []
    for _ in range(count):
        event = await bus.dequeue()
        decisions.append(await loop.process_one(event))

    assert len(decisions) == count
    assert all(d.decision_id for d in decisions)
