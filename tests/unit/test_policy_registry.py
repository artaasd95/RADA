from __future__ import annotations

from datetime import UTC, datetime

import pytest

from rada.core.decision_loop import HoldPolicy
from rada.policies.registry import RiskGatedPolicy, load_profile
from rada.schemas import ActionDirection, DecisionTrace, MarketEvent, ProposedAction


class HighCvarPolicy(HoldPolicy):
    async def propose(self, event: MarketEvent, trace: DecisionTrace) -> ProposedAction:
        _ = event, trace
        return ProposedAction(direction=ActionDirection.BUY, size=10.0, cvar_impact=0.08)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_conservative_profile_breaches_to_hold() -> None:
    profile = load_profile("conservative")
    gated = RiskGatedPolicy(HighCvarPolicy(), profile)
    event = MarketEvent(
        symbol="BTC",
        price=100.0,
        volume=1.0,
        timestamp=datetime(2026, 6, 1, tzinfo=UTC),
    )
    action = await gated.propose(event, DecisionTrace(model_name="t", rationale="r"))
    assert action.direction == ActionDirection.HOLD


@pytest.mark.unit
@pytest.mark.asyncio
async def test_aggressive_profile_allows_higher_cvar() -> None:
    profile = load_profile("aggressive")
    gated = RiskGatedPolicy(HighCvarPolicy(), profile)
    event = MarketEvent(
        symbol="BTC",
        price=100.0,
        volume=1.0,
        timestamp=datetime(2026, 6, 1, tzinfo=UTC),
    )
    action = await gated.propose(event, DecisionTrace(model_name="t", rationale="r"))
    assert action.direction == ActionDirection.BUY


@pytest.mark.unit
def test_load_balanced_profile() -> None:
    profile = load_profile("balanced")
    assert profile.name == "balanced"
    assert profile.cvar_max == 0.05
