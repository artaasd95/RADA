from datetime import UTC, datetime

import pytest

from rada.schemas import ActionDirection, Decision, DecisionTrace, MarketEvent, ProposedAction


@pytest.mark.unit
def test_market_event_json_roundtrip() -> None:
    event = MarketEvent(
        symbol="BTCUSD",
        price=65000.5,
        volume=12.1,
        timestamp=datetime.now(tz=UTC),
    )

    restored = MarketEvent.model_validate_json(event.model_dump_json())
    assert restored == event


@pytest.mark.unit
def test_decision_trace_json_roundtrip() -> None:
    trace = DecisionTrace(
        model_name="test-model",
        rationale="Placeholder rationale",
        assumptions=["liq stable"],
        warnings=["none"],
        faithfulness_score=0.93,
    )

    restored = DecisionTrace.model_validate_json(trace.model_dump_json())
    assert restored == trace


@pytest.mark.unit
def test_proposed_action_json_roundtrip() -> None:
    action = ProposedAction(
        direction=ActionDirection.BUY,
        size=2.0,
        risk_adjusted_size=1.5,
        cvar_impact=0.07,
    )

    restored = ProposedAction.model_validate_json(action.model_dump_json())
    assert restored == action


@pytest.mark.unit
def test_decision_json_roundtrip() -> None:
    event = MarketEvent(
        symbol="ETHUSD",
        price=3200.0,
        volume=200,
        timestamp=datetime.now(tz=UTC),
    )
    decision = Decision(
        market_event=event,
        proposed_action=ProposedAction(direction=ActionDirection.HOLD, size=0),
        trace=DecisionTrace(model_name="stub", rationale="No-op"),
    )

    restored = Decision.model_validate_json(decision.model_dump_json())
    assert restored == decision


@pytest.mark.unit
def test_decision_timestamp_rejects_naive_datetime() -> None:
    event = MarketEvent(
        symbol="SOLUSD",
        price=140,
        volume=5,
        timestamp=datetime.now(tz=UTC),
    )

    with pytest.raises(ValueError):
        Decision(
            timestamp=datetime.utcnow(),
            market_event=event,
            proposed_action=ProposedAction(direction=ActionDirection.HOLD, size=0),
            trace=DecisionTrace(model_name="stub", rationale="No-op"),
        )
