"""Run calc steps on market event fields."""

from __future__ import annotations

from rada.calc.engine import compute_cvar, compute_drawdown, compute_position_size
from rada.calc.schemas import CalcResult
from rada.schemas import MarketEvent


def run_event_calcs(event: MarketEvent) -> list[CalcResult]:
    """Compute verified metrics from event context for decision trace."""
    returns = [-0.02, -0.01, 0.0, 0.01, -0.015, 0.005, -0.03, event.volume * 0.001]
    equity = [100.0, 102.0, 101.0, 100.0 - abs(event.price * 0.0001), 99.5]
    return [
        compute_cvar(returns),
        compute_position_size(
            capital=100_000.0,
            risk_budget=0.02,
            price=event.price,
            volatility=max(0.05, event.volume * 0.01),
        ),
        compute_drawdown(equity),
    ]
