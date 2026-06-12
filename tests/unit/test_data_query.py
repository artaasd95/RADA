from __future__ import annotations

from datetime import UTC, datetime

import pytest

from rada.data.query import filter_decisions
from rada.schemas import ActionDirection, Decision, DecisionTrace, MarketEvent, ProposedAction


def _decision(
    *,
    decision_id: str,
    policy_id: str = "balanced",
    ts: datetime,
) -> Decision:
    event = MarketEvent(
        symbol="BTCUSD",
        price=100.0,
        volume=1.0,
        timestamp=ts,
    )
    return Decision(
        decision_id=decision_id,
        policy_id=policy_id,
        timestamp=ts,
        market_event=event,
        proposed_action=ProposedAction(direction=ActionDirection.HOLD, size=0),
        trace=DecisionTrace(),
    )


@pytest.mark.unit
def test_filter_decisions_since_limit_and_policy() -> None:
    t1 = datetime(2026, 6, 1, tzinfo=UTC)
    t2 = datetime(2026, 6, 2, tzinfo=UTC)
    decisions = [
        _decision(decision_id="a", policy_id="balanced", ts=t1),
        _decision(decision_id="b", policy_id="aggressive", ts=t2),
        _decision(decision_id="c", policy_id="balanced", ts=t2),
    ]
    filtered = filter_decisions(
        decisions,
        since=datetime(2026, 6, 2, tzinfo=UTC),
        limit=1,
        policy_ids=["balanced"],
    )
    assert len(filtered) == 1
    assert filtered[0].decision_id == "c"
