from __future__ import annotations

import pytest

from rada.schemas import ActionDirection, ProposedAction
from rada.search.risk_selection import TailWarpStub, select_cvar_feasible_action


@pytest.mark.unit
def test_selects_largest_feasible_action() -> None:
    candidates = [
        ProposedAction(direction=ActionDirection.BUY, size=10.0),
        ProposedAction(direction=ActionDirection.BUY, size=100.0),
        ProposedAction(direction=ActionDirection.SELL, size=50.0),
    ]
    chosen = select_cvar_feasible_action(
        candidates,
        price=50000.0,
        tailwarp=TailWarpStub(cvar_limit=1.0),
    )
    assert chosen.size == 100.0


@pytest.mark.unit
def test_falls_back_to_hold_when_none_feasible() -> None:
    candidates = [ProposedAction(direction=ActionDirection.BUY, size=1_000_000.0)]
    chosen = select_cvar_feasible_action(
        candidates,
        price=1_000_000.0,
        tailwarp=TailWarpStub(cvar_limit=0.0001),
    )
    assert chosen.direction == ActionDirection.HOLD
    assert chosen.size == 0.0
