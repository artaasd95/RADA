"""Causal market shock simulation for replay into the decision loop."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from rada.schemas import MarketEvent


class ShockScenario(BaseModel):
    """Configurable shock with explicit causality chain."""

    name: str
    symbol: str = "BTCUSD"
    base_price: float = Field(default=50000.0, gt=0)
    price_delta_pct: float = Field(description="Total percent move applied across steps")
    causality_chain: list[str] = Field(
        min_length=1,
        description="Ordered causal factors, e.g. ['macro', 'liquidity', 'price']",
    )
    steps: int = Field(default=3, ge=1)
    base_volume: float = Field(default=1.0, ge=0)
    start_time: datetime | None = None


def generate_shock_scenario(scenario: ShockScenario) -> list[MarketEvent]:
    """Generate a deterministic MarketEvent stream for a shock scenario."""
    start = scenario.start_time or datetime(2026, 1, 1, tzinfo=UTC)
    chain_len = len(scenario.causality_chain)
    per_step_pct = scenario.price_delta_pct / scenario.steps
    price = scenario.base_price
    events: list[MarketEvent] = []

    for step in range(scenario.steps):
        factor = scenario.causality_chain[step % chain_len]
        price *= 1.0 + (per_step_pct / 100.0)
        volume = max(scenario.base_volume * (1.0 + 0.1 * step), 0.0)

        events.append(
            MarketEvent(
                symbol=scenario.symbol,
                price=round(price, 2),
                volume=round(volume, 4),
                timestamp=start + timedelta(seconds=step),
            )
        )

        _ = factor  # causality factor name available for trace extensions

    return events


def iter_shock_events(scenario: ShockScenario) -> Iterator[MarketEvent]:
    """Iterator wrapper for replay into decision_loop or event bus."""
    yield from generate_shock_scenario(scenario)
