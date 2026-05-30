from datetime import UTC, datetime

import pytest

from rada.data.analytics import compute_rolling_pnl, pnl_stub_from_decision
from rada.data.quality import compute_event_checksum, validate_ingest_event
from rada.schemas import ActionDirection, Decision, DecisionTrace, MarketEvent, ProposedAction


def _decision(direction: ActionDirection, price: float, size: float) -> Decision:
    event = MarketEvent(
        symbol="BTCUSD",
        price=price,
        volume=1.0,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return Decision(
        market_event=event,
        proposed_action=ProposedAction(direction=direction, size=size, risk_adjusted_size=size),
        trace=DecisionTrace(model_name="test"),
    )


@pytest.mark.unit
def test_compute_event_checksum_is_stable() -> None:
    event = MarketEvent(
        symbol="ETHUSD",
        price=3000.0,
        volume=2.0,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert compute_event_checksum(event) == compute_event_checksum(event)


@pytest.mark.unit
def test_validate_ingest_rejects_bad_price() -> None:
    event = MarketEvent.model_construct(
        symbol="BTCUSD",
        price=-1.0,
        volume=1.0,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
    result = validate_ingest_event(event, source="unit-test")
    assert not result.accepted


@pytest.mark.unit
def test_validate_ingest_accepts_and_lineage() -> None:
    event = MarketEvent(
        symbol="BTCUSD",
        price=50000.0,
        volume=1.0,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
    result = validate_ingest_event(event, source="fake-ingest")
    assert result.accepted
    assert result.lineage is not None
    assert result.lineage.source == "fake-ingest"
    assert result.lineage.event_symbol == "BTCUSD"


@pytest.mark.unit
def test_pnl_stub_buy_sell_hold() -> None:
    hold = pnl_stub_from_decision(_decision(ActionDirection.HOLD, 50000.0, 1.0))
    buy = pnl_stub_from_decision(_decision(ActionDirection.BUY, 50000.0, 2.0))
    sell = pnl_stub_from_decision(_decision(ActionDirection.SELL, 50000.0, 2.0))

    assert hold == 0.0
    assert buy > 0
    assert sell < 0


@pytest.mark.unit
def test_rolling_pnl_on_synthetic_stream() -> None:
    stream = [
        _decision(ActionDirection.BUY, 50000.0, 1.0),
        _decision(ActionDirection.SELL, 51000.0, 1.0),
        _decision(ActionDirection.HOLD, 50500.0, 0.0),
    ]
    rolling = compute_rolling_pnl(stream, window=3)
    assert isinstance(rolling, float)
