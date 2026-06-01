from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rada.data.timescale_store import TimescaleDecisionStore
from rada.schemas import ActionDirection, Decision, DecisionTrace, MarketEvent, ProposedAction


def _timescale_url() -> str:
    return os.getenv("RADA_DATABASE_URL", "postgresql://rada:rada@localhost:5433/rada")


def _sample_decision() -> Decision:
    return Decision(
        market_event=MarketEvent(
            symbol="BTCUSD",
            price=50000.0,
            volume=1.25,
            timestamp=datetime(2026, 6, 1, tzinfo=UTC),
        ),
        proposed_action=ProposedAction(
            direction=ActionDirection.HOLD,
            size=0.0,
            risk_adjusted_size=0.0,
            cvar_impact=0.0,
        ),
        trace=DecisionTrace(
            model_name="timescale-smoke",
            rationale="integration check",
            assumptions=["stub"],
            warnings=[],
            faithfulness_score=1.0,
        ),
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_timescale_store_roundtrip_or_skip_when_unavailable() -> None:
    store = TimescaleDecisionStore(_timescale_url())
    try:
        try:
            await store.ensure_ready()
        except Exception as exc:  # pragma: no cover - environment-dependent
            pytest.skip(f"Timescale unavailable in test environment: {exc}")

        decision = _sample_decision()
        await store.save_decision(decision)
        restored = await store.get_decision(decision.decision_id)

        assert restored is not None
        assert restored.decision_id == decision.decision_id
    finally:
        await store.close()


@pytest.mark.integration
def test_timescale_migration_revision_contains_s1_compatibility_and_hypertables() -> None:
    migration_file = Path("migrations/timescale/versions/20260601_0001_timescale_schema.py")
    assert migration_file.exists()

    content = migration_file.read_text(encoding="utf-8")
    assert "payload::jsonb" in content
    assert "create_hypertable('market_events'" in content
    assert "create_hypertable('decision_traces'" in content
