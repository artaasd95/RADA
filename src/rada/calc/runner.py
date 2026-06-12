"""Run calc steps on market event fields."""

from __future__ import annotations

import math

from rada.calc.engine import compute_cvar, compute_drawdown, compute_position_size
from rada.calc.schemas import CalcResult
from rada.schemas import MarketEvent

_MAX_SYNTHETIC_VOLATILITY = 1.0


def run_event_calcs(event: MarketEvent) -> list[CalcResult]:
    """Compute illustrative metrics from event context (synthetic, not verified)."""
    returns = [-0.02, -0.01, 0.0, 0.01, -0.015, 0.005, -0.03, event.volume * 0.001]
    equity = [100.0, 102.0, 101.0, 100.0 - abs(event.price * 0.0001), 99.5]
    volatility = min(_MAX_SYNTHETIC_VOLATILITY, max(0.05, event.volume * 0.01))
    results = [
        compute_cvar(returns),
        compute_position_size(
            capital=100_000.0,
            risk_budget=0.02,
            price=event.price,
            volatility=volatility,
        ),
        compute_drawdown(equity),
    ]
    for result in results:
        result.context["synthetic"] = True
    return results


def synthetic_context_from_results(results: list[CalcResult]) -> dict[str, float]:
    """Build synthetic context map, omitting NaN values."""
    context: dict[str, float] = {}
    for result in results:
        if math.isnan(result.value):
            continue
        context[result.expression] = result.value
    return context
