from __future__ import annotations

from datetime import UTC, datetime

import pytest

from rada.adapters.scenario_reasoner import ScenarioReasoner
from rada.core.decision_loop import DecisionLoop, PassThroughRiskOptimizer
from rada.core.reasoner_loop import ReasonerLoop
from rada.data.storage import InMemoryDecisionStore
from rada.policies.registry import RiskGatedPolicy, load_profile
from rada.schemas import MarketEvent
from rada.search.simulation import ShockScenario, generate_shock_scenario


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reasoner_proposes_decision_loop_selects_under_gate() -> None:
    scenario = ShockScenario(
        name="macro-liquidity-shock",
        symbol="BTCUSD",
        base_price=60000.0,
        price_delta_pct=-8.0,
        causality_chain=["macro", "liquidity", "price"],
        steps=3,
    )
    events = generate_shock_scenario(scenario)
    from rada.core.decision_loop import HoldPolicy

    reasoner = ScenarioReasoner(scenario)
    profile = load_profile("balanced")
    gated = RiskGatedPolicy(HoldPolicy(), profile)

    store = InMemoryDecisionStore()
    loop = DecisionLoop(
        reasoner=reasoner,
        policy=gated,
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=store,
        reasoner_loop=ReasonerLoop(reasoner),
        cvar_limit=profile.cvar_max,
    )

    decision = await loop.process_one(events[-1])
    assert decision.decision_id
    assert decision.trace.model_name == "scenario-reasoner-mock"
