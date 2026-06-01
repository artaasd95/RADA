from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from rada.schemas import MarketEvent
from rada.search.game_theory import batch_nash_spread_search_stub, nash_spread_search_stub
from rada.search.uncertainty import attach_interval_to_action, interval_action_size_stub


def _sample_event(price: float = 50000.0) -> MarketEvent:
    return MarketEvent(
        symbol="BTCUSD",
        price=price,
        volume=1.0,
        timestamp=datetime(2026, 6, 1, tzinfo=UTC),
    )


@pytest.mark.unit
def test_nash_spread_search_stub_is_json_serializable() -> None:
    payload = nash_spread_search_stub(
        symbol="BTCUSD",
        reference_price=51000.0,
        market_hits=[{"query": "btc", "rank": "1", "score": "0.85"}],
        top_k=3,
    )

    encoded = json.dumps(payload)
    decoded = json.loads(encoded)

    assert decoded["method"] == "nash_spread_search_stub"
    assert "equilibrium_action" in decoded


@pytest.mark.unit
def test_batch_nash_spread_search_stub_requires_equal_lengths() -> None:
    with pytest.raises(ValueError, match="equal length"):
        batch_nash_spread_search_stub(events=[_sample_event()], batched_hits=[], top_k=2)


@pytest.mark.unit
def test_batch_nash_spread_search_stub_outputs_per_event() -> None:
    events = [_sample_event(50000.0), _sample_event(49000.0)]
    hits = [
        [{"query": "a", "rank": "1", "score": "0.7"}],
        [{"query": "b", "rank": "1", "score": "0.4"}],
    ]

    batch = batch_nash_spread_search_stub(events=events, batched_hits=hits, top_k=2)

    assert len(batch) == 2
    assert batch[0]["symbol"] == "BTCUSD"


@pytest.mark.unit
def test_interval_action_size_stub_bounds() -> None:
    interval = interval_action_size_stub(action_size=1.0, confidence=0.9, calibration_error=0.1)

    assert interval["method"] == "interval_stub"
    assert interval["lower"] <= interval["upper"]


@pytest.mark.unit
def test_attach_interval_to_action_is_json_serializable() -> None:
    action_payload = {
        "symbol": "BTCUSD",
        "equilibrium_action": {
            "direction": "HOLD",
            "size": 0.5,
            "spread_bps": 0.0,
        },
    }

    enriched = attach_interval_to_action(action_payload, confidence=0.85)
    encoded = json.dumps(enriched)
    decoded = json.loads(encoded)

    assert "uncertainty" in decoded
    assert decoded["uncertainty"]["confidence"] == pytest.approx(0.85)
