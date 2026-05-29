"""Synthetic market data ingestion utilities."""

from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from rada.schemas import MarketEvent


async def synthetic_market_events(
    *,
    symbol: str = "BTCUSD",
    count: int = 10,
    interval_seconds: float = 0.0,
    seed: int = 42,
) -> AsyncIterator[MarketEvent]:
    """Yield deterministic synthetic market events for bootstrap testing."""
    rng = random.Random(seed)
    price = 50000.0

    for _ in range(count):
        price += rng.uniform(-50.0, 50.0)
        volume = max(rng.uniform(0.1, 10.0), 0.0)

        yield MarketEvent(
            symbol=symbol,
            price=round(price, 2),
            volume=round(volume, 4),
            timestamp=datetime.now(tz=UTC),
        )

        if interval_seconds > 0:
            await asyncio.sleep(interval_seconds)
