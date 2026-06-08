from __future__ import annotations

from datetime import UTC, datetime

import pytest

from rada.core.decision_loop import DecisionLoop, HoldPolicy, NoOpReasoner, PassThroughRiskOptimizer
from rada.data.storage import InMemoryDecisionStore
from rada.schemas import MarketEvent


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inmemory_list_decisions_since_and_limit() -> None:
    store = InMemoryDecisionStore()
    loop = DecisionLoop(
        reasoner=NoOpReasoner(),
        policy=HoldPolicy(),
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=store,
    )
    for day in (1, 2, 3):
        await loop.process_one(
            MarketEvent(
                symbol="ETH",
                price=100.0 + day,
                volume=1.0,
                timestamp=datetime(2026, 6, day, tzinfo=UTC),
            )
        )

    all_decisions = await store.list_decisions()
    assert len(all_decisions) == 3

    limited = await store.list_decisions(limit=2)
    assert len(limited) == 2

    since = await store.list_decisions(since=datetime(2026, 6, 2, tzinfo=UTC))
    assert len(since) == 2
