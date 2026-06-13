from __future__ import annotations

from datetime import UTC, datetime

import pytest

from rada.feedback.auto_flag import should_auto_flag
from rada.schemas import ActionDirection, Decision, DecisionTrace, MarketEvent, ProposedAction


def _decision(
    *,
    faithfulness_score: float | None = None,
    verified_context: dict | None = None,
    cvar_impact: float | None = None,
) -> Decision:
    event = MarketEvent(
        symbol="BTC",
        price=100.0,
        volume=1.0,
        timestamp=datetime(2026, 6, 1, tzinfo=UTC),
    )
    trace = DecisionTrace(
        model_name="t",
        rationale="r",
        faithfulness_score=faithfulness_score,
        verified_context=verified_context or {},
    )
    action = ProposedAction(direction=ActionDirection.HOLD, size=0, cvar_impact=cvar_impact)
    return Decision(market_event=event, proposed_action=action, trace=trace)


@pytest.mark.unit
def test_auto_flag_cvar_breach() -> None:
    d = _decision(verified_context={"cvar": 0.09})
    flag, reason = should_auto_flag(d, cvar_limit=0.05)
    assert flag is True
    assert "CVaR" in reason


@pytest.mark.unit
def test_auto_flag_low_confidence() -> None:
    d = _decision(faithfulness_score=0.5)
    flag, reason = should_auto_flag(d)
    assert flag is True
    assert "confidence" in reason


@pytest.mark.unit
def test_no_flag_when_clean() -> None:
    d = _decision(faithfulness_score=0.9, verified_context={"cvar": 0.02})
    flag, _ = should_auto_flag(d)
    assert flag is False
