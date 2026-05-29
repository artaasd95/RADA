import pytest

from rada.data.ingestion import synthetic_market_events


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fake_ingest_yields_n_events() -> None:
    count = 5
    events = [event async for event in synthetic_market_events(count=count, seed=7)]

    assert len(events) == count
    assert all(event.symbol == "BTCUSD" for event in events)
    assert all(event.price > 0 for event in events)
