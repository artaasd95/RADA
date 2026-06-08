from __future__ import annotations

from datetime import UTC, datetime

import pytest

from rada.data.pipeline import ExportPipelineRunner, load_pipeline_config
from rada.schemas import ActionDirection, Decision, DecisionTrace, MarketEvent, ProposedAction

_REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]


def _decision(*, with_outcome: bool) -> Decision:
    event = MarketEvent(
        symbol="BTCUSD",
        price=100.0,
        volume=1.0,
        timestamp=datetime(2026, 6, 1, tzinfo=UTC),
    )
    return Decision(
        market_event=event,
        proposed_action=ProposedAction(direction=ActionDirection.HOLD, size=0),
        trace=DecisionTrace(model_name="stub", rationale="test"),
        outcome={"status": "filled", "pnl_stub": 0.0} if with_outcome else None,
    )


@pytest.mark.unit
def test_require_outcome_excludes_decisions_without_outcome() -> None:
    config = load_pipeline_config(_REPO_ROOT / "configs" / "data" / "export.yaml")
    runner = ExportPipelineRunner(config)
    decisions = [_decision(with_outcome=True), _decision(with_outcome=False)]
    filtered = runner.filter_decisions(decisions)
    assert len(filtered) == 1
    assert filtered[0].outcome is not None
