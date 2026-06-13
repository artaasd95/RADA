from __future__ import annotations

import pytest

from rada.core.decision_loop import DecisionLoop, NoOpReasoner, PassThroughRiskOptimizer
from rada.data.storage import InMemoryDecisionStore
from rada.policies import ToolAwarePolicy
from rada.schemas import MarketEvent


@pytest.mark.integration
@pytest.mark.asyncio
async def test_decision_loop_with_tool_aware_policy_emits_tool_calls() -> None:
    loop = DecisionLoop(
        reasoner=NoOpReasoner(),
        policy=ToolAwarePolicy(max_size=5.0, max_cvar=0.1),
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=InMemoryDecisionStore(),
    )
    event = MarketEvent.model_validate(
        {
            "symbol": "BTCUSD",
            "price": 58000.0,
            "volume": 2.0,
            "timestamp": "2026-01-01T00:00:00Z",
        }
    )

    decision = await loop.process_one(event)

    assert decision.proposed_action is not None
    assert len(decision.trace.tool_calls) >= 4
    assert any(call["name"] == "risk_calculator" for call in decision.trace.tool_calls)
