from datetime import UTC, datetime

import pytest

from rada.search.simulation import ShockScenario, generate_shock_scenario, iter_shock_events


@pytest.mark.unit
def test_known_shock_fixture_macro_liquidity_price() -> None:
    scenario = ShockScenario(
        name="macro-liquidity-shock",
        symbol="BTCUSD",
        base_price=50000.0,
        price_delta_pct=-6.0,
        causality_chain=["macro", "liquidity", "price"],
        steps=3,
        start_time=datetime(2026, 6, 1, tzinfo=UTC),
    )
    events = generate_shock_scenario(scenario)

    assert len(events) == 3
    assert events[0].price == pytest.approx(49000.0, rel=1e-4)
    assert events[-1].price < events[0].price
    assert all(event.symbol == "BTCUSD" for event in events)
    assert all(event.timestamp.tzinfo is not None for event in events)


@pytest.mark.unit
def test_iter_shock_events_replay_compatible() -> None:
    scenario = ShockScenario(
        name="replay-smoke",
        price_delta_pct=3.0,
        causality_chain=["supply", "demand"],
        steps=2,
    )
    replay = list(iter_shock_events(scenario))
    assert len(replay) == 2
    assert replay[1].price > replay[0].price
