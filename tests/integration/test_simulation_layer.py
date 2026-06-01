from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from rada.search.game_theory import batch_nash_spread_search_stub
from rada.search.simulation import ShockScenario, generate_shock_scenario
from rada.search.uncertainty import attach_interval_to_action
from rada.search.vectorized_env import VectorizedSearchEnv


@pytest.mark.integration
@pytest.mark.asyncio
async def test_market_simulation_to_vectorized_env_to_action_batch() -> None:
    scenario = ShockScenario(
        name="sim-layer-smoke",
        symbol="BTCUSD",
        base_price=50000.0,
        price_delta_pct=-4.0,
        causality_chain=["macro", "liquidity", "spread"],
        steps=4,
        start_time=datetime(2026, 6, 1, tzinfo=UTC),
    )
    events = generate_shock_scenario(scenario)

    env = VectorizedSearchEnv(max_concurrency=32)
    queries = [f"{event.symbol} shock price={event.price}" for event in events]
    batched_hits = await env.search_batch(queries, top_k=3)

    actions = batch_nash_spread_search_stub(events=events, batched_hits=batched_hits, top_k=3)
    bounded_actions = [attach_interval_to_action(action, confidence=0.9) for action in actions]

    assert len(batched_hits) == len(events)
    assert len(bounded_actions) == len(events)
    assert all("equilibrium_action" in action for action in bounded_actions)
    assert all("uncertainty" in action for action in bounded_actions)

    # Dashboard payload compatibility check.
    json.dumps({"scenario": scenario.name, "actions": bounded_actions})
