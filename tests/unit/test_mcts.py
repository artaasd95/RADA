from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from rada.interfaces import BaseRiskOptimizer
from rada.schemas import ActionDirection, DecisionTrace, MarketEvent, ProposedAction
from rada.search.mcts import MCTSConfig, MCTSPlanner, run_mcts_benchmark_fixture


class CountingRiskOptimizer(BaseRiskOptimizer):
    def __init__(self) -> None:
        self.calls = 0

    async def optimize(self, action: ProposedAction, trace: DecisionTrace) -> ProposedAction:
        _ = trace
        self.calls += 1
        return action.model_copy(update={"risk_adjusted_size": action.size, "cvar_impact": 0.0})


def _sample_event() -> MarketEvent:
    return MarketEvent(
        symbol="BTCUSD",
        price=50000.0,
        volume=1.5,
        timestamp=datetime(2026, 6, 1, tzinfo=UTC),
    )


def _sample_trace() -> DecisionTrace:
    return DecisionTrace(
        model_name="test-mcts",
        rationale="unit test",
        warnings=[],
        assumptions=["deterministic fixture"],
        faithfulness_score=1.0,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mcts_plan_returns_json_serializable_payload() -> None:
    planner = MCTSPlanner(
        risk_optimizer=CountingRiskOptimizer(),
        config=MCTSConfig(iterations=12, rollout_depth=2),
    )

    result = await planner.plan(_sample_event(), _sample_trace())

    assert result["algorithm"] == "mcts-hybrid-stub"
    assert result["policy_source"] == "trinity-stub"
    assert result["best_action"]["direction"] in {
        ActionDirection.BUY.value,
        ActionDirection.SELL.value,
        ActionDirection.HOLD.value,
    }
    json.dumps(result)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mcts_consults_risk_optimizer_during_search() -> None:
    risk_optimizer = CountingRiskOptimizer()
    planner = MCTSPlanner(
        risk_optimizer=risk_optimizer,
        config=MCTSConfig(iterations=9, rollout_depth=2),
    )

    await planner.plan(_sample_event(), _sample_trace())

    # At least expansion + rollout calls per iteration, plus final best-action pass.
    assert risk_optimizer.calls >= (9 * 2) + 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mcts_benchmark_completes_within_budget() -> None:
    planner = MCTSPlanner(
        risk_optimizer=CountingRiskOptimizer(),
        config=MCTSConfig(iterations=32, rollout_depth=3),
    )

    summary = await run_mcts_benchmark_fixture(
        planner,
        event=_sample_event(),
        trace=_sample_trace(),
        budget_seconds=60.0,
    )

    assert summary["timing"]["within_budget"] is True
    assert float(summary["timing"]["budget_seconds"]) == pytest.approx(60.0)
