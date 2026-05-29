from datetime import UTC, datetime

import pytest

from rada.core.decision_loop import DecisionLoop, HoldPolicy, NoOpReasoner, PassThroughRiskOptimizer
from rada.data.storage import InMemoryDecisionStore
from rada.schemas import ActionDirection, MarketEvent


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decision_loop_processes_one_event() -> None:
    store = InMemoryDecisionStore()
    loop = DecisionLoop(
        reasoner=NoOpReasoner(),
        policy=HoldPolicy(),
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=store,
    )

    event = MarketEvent(
        symbol="BTCUSD",
        price=63000.0,
        volume=1.2,
        timestamp=datetime.now(tz=UTC),
    )

    decision = await loop.process_one(event)
    restored = await store.get_decision(decision.decision_id)

    assert restored is not None
    assert restored.decision_id == decision.decision_id
    assert restored.proposed_action.direction == ActionDirection.HOLD
    assert restored.proposed_action.risk_adjusted_size == 0
