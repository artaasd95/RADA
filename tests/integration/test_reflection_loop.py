from __future__ import annotations

from datetime import UTC, datetime

import pytest

from rada.core.decision_loop import DecisionLoop, HoldPolicy, NoOpReasoner, PassThroughRiskOptimizer
from rada.core.reflection_loop import ReflectionLoop
from rada.data.storage import InMemoryDecisionStore
from rada.schemas import MarketEvent


@pytest.mark.integration
@pytest.mark.asyncio
async def test_n_decisions_produce_audit_scores_and_policy_checkpoint() -> None:
    store = InMemoryDecisionStore()
    loop = DecisionLoop(
        reasoner=NoOpReasoner(),
        policy=HoldPolicy(),
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=store,
    )
    reflection = ReflectionLoop()

    n = 5
    for index in range(n):
        event = MarketEvent(
            symbol="BTCUSD",
            price=60000.0 + index,
            volume=1.0,
            timestamp=datetime(2026, 6, 1, 12, index, tzinfo=UTC),
        )
        decision = await loop.process_one(event)
        reflection.enqueue(decision)

    processed = await reflection.drain_all()
    assert processed == n
    assert len(reflection.audit_scores) == n
    assert all(0.0 <= score <= 1.0 for score in reflection.audit_scores)

    checkpoint = reflection.policy_checkpoint
    assert checkpoint.audit_count == n
    assert checkpoint.version == n
    assert checkpoint.mean_faithfulness > 0.0
