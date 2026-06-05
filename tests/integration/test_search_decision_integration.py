from __future__ import annotations

from datetime import UTC, datetime

import pytest

from rada.core.decision_loop import DecisionLoop, HoldPolicy, NoOpReasoner, PassThroughRiskOptimizer
from rada.core.search_loop import SearchLoop
from rada.data.storage import InMemoryDecisionStore
from rada.schemas import ActionDirection, MarketEvent


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decision_loop_without_search_stays_hold() -> None:
    store = InMemoryDecisionStore()
    risk = PassThroughRiskOptimizer()
    loop = DecisionLoop(
        reasoner=NoOpReasoner(),
        policy=HoldPolicy(),
        risk_optimizer=risk,
        data_store=store,
        search_loop=SearchLoop(risk_optimizer=risk, enabled=False),
    )
    event = MarketEvent(
        symbol="BTCUSD",
        price=50000.0,
        volume=2.0,
        timestamp=datetime(2026, 6, 1, tzinfo=UTC),
    )
    decision = await loop.process_one(event)
    assert decision.proposed_action.direction == ActionDirection.HOLD


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decision_loop_with_search_enabled_may_change_action() -> None:
    store = InMemoryDecisionStore()
    risk = PassThroughRiskOptimizer()
    loop = DecisionLoop(
        reasoner=NoOpReasoner(),
        policy=HoldPolicy(),
        risk_optimizer=risk,
        data_store=store,
        search_loop=SearchLoop(risk_optimizer=risk, enabled=True),
    )
    event = MarketEvent(
        symbol="BTCUSD",
        price=50000.0,
        volume=10.0,
        timestamp=datetime(2026, 6, 1, tzinfo=UTC),
    )
    decision = await loop.process_one(event)
    assert decision.proposed_action.direction in {
        ActionDirection.BUY,
        ActionDirection.SELL,
        ActionDirection.HOLD,
    }
