from datetime import UTC, datetime

import pytest

from rada.data.bus import InMemoryEventBus, build_event_bus


@pytest.mark.unit
@pytest.mark.asyncio
async def test_inmemory_bus_roundtrip() -> None:
    bus = InMemoryEventBus()
    event = MarketEvent(
        symbol="BTCUSD",
        price=60000.0,
        volume=1.0,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
    await bus.enqueue(event)
    restored = await bus.dequeue()
    assert restored.symbol == event.symbol
    assert restored.price == event.price


@pytest.mark.unit
@pytest.mark.asyncio
async def test_build_event_bus_defaults_inmemory() -> None:
    bus = await build_event_bus("inmemory")
    assert isinstance(bus, InMemoryEventBus)
