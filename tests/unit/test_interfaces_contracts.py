from __future__ import annotations

from datetime import UTC, datetime

import pytest

from rada.interfaces import (
    BaseAuditor,
    BaseDataStore,
    BasePolicy,
    BaseReasoner,
    BaseRiskOptimizer,
    BaseSearchEnv,
)
from rada.schemas import ActionDirection, Decision, DecisionTrace, MarketEvent, ProposedAction


class StubReasoner(BaseReasoner):
    async def reason(self, event: MarketEvent) -> DecisionTrace:
        return DecisionTrace(model_name="stub-reasoner", rationale=f"symbol={event.symbol}")


class StubPolicy(BasePolicy):
    async def propose(self, event: MarketEvent, trace: DecisionTrace) -> ProposedAction:
        _ = trace
        return ProposedAction(direction=ActionDirection.HOLD, size=0)


class StubRisk(BaseRiskOptimizer):
    async def optimize(self, action: ProposedAction, trace: DecisionTrace) -> ProposedAction:
        _ = trace
        return action.model_copy(update={"risk_adjusted_size": action.size, "cvar_impact": 0.0})


class StubAuditor(BaseAuditor):
    async def audit(self, decision: Decision) -> DecisionTrace:
        return decision.trace.model_copy(update={"faithfulness_score": 1.0})


class StubDataStore(BaseDataStore):
    def __init__(self) -> None:
        self.items: dict[str, Decision] = {}

    async def save_decision(self, decision: Decision) -> None:
        self.items[decision.decision_id] = decision

    async def get_decision(self, decision_id: str) -> Decision | None:
        return self.items.get(decision_id)


class StubSearchEnv(BaseSearchEnv):
    async def search(self, query: str, top_k: int = 5) -> list[dict[str, str]]:
        return [{"query": query, "rank": str(i)} for i in range(top_k)]


def _sample_event() -> MarketEvent:
    return MarketEvent(
        symbol="BTCUSD",
        price=64000,
        volume=2,
        timestamp=datetime.now(tz=UTC),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_interface_contracts_with_stubs() -> None:
    event = _sample_event()

    reasoner = StubReasoner()
    policy = StubPolicy()
    risk = StubRisk()
    auditor = StubAuditor()
    store = StubDataStore()
    search = StubSearchEnv()

    trace = await reasoner.reason(event)
    action = await policy.propose(event, trace)
    adjusted = await risk.optimize(action, trace)

    decision = Decision(
        market_event=event,
        proposed_action=adjusted,
        trace=trace,
    )

    audited_trace = await auditor.audit(decision)
    decision = decision.model_copy(update={"trace": audited_trace})

    await store.save_decision(decision)
    restored = await store.get_decision(decision.decision_id)
    hits = await search.search(query="shock", top_k=3)

    assert restored is not None
    assert restored.decision_id == decision.decision_id
    assert restored.trace.faithfulness_score == 1.0
    assert adjusted.risk_adjusted_size == 0
    assert len(hits) == 3
