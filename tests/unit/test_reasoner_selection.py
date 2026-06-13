from __future__ import annotations

from datetime import UTC, datetime

import pytest

from rada.adapters.real_reasoner import RealReasoner
from rada.adapters.scenario_reasoner import ScenarioReasoner
from rada.main import RuntimeSettings, build_reasoner
from rada.schemas import MarketEvent


@pytest.mark.unit
def test_build_reasoner_defaults_to_mock_under_pytest() -> None:
    reasoner = build_reasoner(RuntimeSettings())

    assert isinstance(reasoner, ScenarioReasoner)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_real_reasoner_can_use_mock_provider_config(tmp_path) -> None:
    config_path = tmp_path / "llm_mock.yaml"
    config_path.write_text("provider: mock\nmodel_id: qwen-local-test\n", encoding="utf-8")

    reasoner = build_reasoner(
        RuntimeSettings(
            reasoner_mode="real",
            llm_config_path=str(config_path),
        )
    )

    assert isinstance(reasoner, RealReasoner)

    trace = await reasoner.reason(
        MarketEvent(
            symbol="BTCUSD",
            price=62000.0,
            volume=1.5,
            timestamp=datetime(2026, 6, 1, tzinfo=UTC),
        )
    )

    assert trace.model_name == "mock:qwen-local-test"
    assert trace.rationale.startswith("[mock:qwen-local-test]")
    assert "provider=mock" in trace.assumptions