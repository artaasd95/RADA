from __future__ import annotations

import pytest

from rada.core.decision_loop import DecisionLoop, HoldPolicy, PassThroughRiskOptimizer
from rada.core.reasoner_loop import ReasonerLoop
from rada.adapters.scenario_reasoner import ScenarioReasoner
from rada.data.storage import InMemoryDecisionStore
from rada.search.simulation import ShockScenario, generate_shock_scenario


@pytest.mark.integration
@pytest.mark.asyncio
async def test_shock_fixture_produces_calc_trace() -> None:
    scenario = ShockScenario(
        name="macro-liquidity-shock",
        symbol="BTCUSD",
        base_price=60000.0,
        price_delta_pct=-8.0,
        causality_chain=["macro", "liquidity", "price"],
        steps=3,
    )
    events = generate_shock_scenario(scenario)
    reasoner = ScenarioReasoner(scenario)
    loop = DecisionLoop(
        reasoner=reasoner,
        policy=HoldPolicy(),
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=InMemoryDecisionStore(),
        reasoner_loop=ReasonerLoop(reasoner),
    )
    decision = await loop.process_one(events[-1])
    assert len(decision.trace.calc_results) >= 3
    assert "cvar" in decision.trace.verified_context
