from __future__ import annotations

import json
from datetime import UTC, datetime

import pytest

from rada.core.decision_loop import DecisionLoop, HoldPolicy, NoOpReasoner, PassThroughRiskOptimizer
from rada.data.cards import DecisionExportRow, FeedbackRecord
from rada.data.storage import InMemoryDecisionStore
from rada.schemas import MarketEvent


@pytest.mark.unit
@pytest.mark.asyncio
async def test_decision_export_row_round_trip() -> None:
    store = InMemoryDecisionStore()
    loop = DecisionLoop(
        reasoner=NoOpReasoner(),
        policy=HoldPolicy(),
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=store,
    )
    event = MarketEvent(
        symbol="BTCUSD",
        price=50000.0,
        volume=1.0,
        timestamp=datetime(2026, 6, 1, tzinfo=UTC),
    )
    decision = await loop.process_one(event)
    row = DecisionExportRow.from_decision(decision, batch_id="batch-1")
    payload = json.loads(row.model_dump_json())
    assert payload["decision_id"] == decision.decision_id
    assert payload["metadata"]["export_batch_id"] == "batch-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_feedback_record_validates_score_bounds() -> None:
    store = InMemoryDecisionStore()
    loop = DecisionLoop(
        reasoner=NoOpReasoner(),
        policy=HoldPolicy(),
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=store,
    )
    decision = await loop.process_one(
        MarketEvent(
            symbol="BTCUSD",
            price=1.0,
            volume=1.0,
            timestamp=datetime(2026, 6, 1, tzinfo=UTC),
        )
    )
    record = FeedbackRecord.from_decision_stub(decision, score=0.75)
    assert record.labels.score == 0.75
    json.loads(record.model_dump_json())
