from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rada.core.decision_loop import DecisionLoop, HoldPolicy, NoOpReasoner, PassThroughRiskOptimizer
from rada.core.reflection_loop import stub_outcome
from rada.data.export_batch import export_decisions
from rada.data.storage import InMemoryDecisionStore
from rada.schemas import MarketEvent


@pytest.mark.integration
@pytest.mark.asyncio
async def test_batch_export_writes_jsonl_artifacts(tmp_path: Path) -> None:
    store = InMemoryDecisionStore()
    loop = DecisionLoop(
        reasoner=NoOpReasoner(),
        policy=HoldPolicy(),
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=store,
    )
    decisions = []
    for index in range(3):
        event = MarketEvent(
            symbol="BTCUSD",
            price=1000.0 + index,
            volume=1.0,
            timestamp=datetime(2026, 6, 1, 12, index, tzinfo=UTC),
        )
        decisions.append(await loop.process_one(event))

    decisions = [d.model_copy(update={"outcome": stub_outcome(d)}) for d in decisions]
    summary = export_decisions(decisions, output_dir=tmp_path, batch_id="test-batch")
    reflection = Path(summary["reflection"])
    feedback = Path(summary["feedback"])

    assert reflection.exists()
    assert feedback.exists()
    reflection_lines = reflection.read_text(encoding="utf-8").strip().splitlines()
    assert len(reflection_lines) == 3
    first = json.loads(reflection_lines[0])
    assert first["metadata"]["export_batch_id"] == "test-batch"
