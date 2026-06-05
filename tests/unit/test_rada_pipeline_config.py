from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from rada.data.pipeline import ExportPipelineRunner, UsagePipelineRunner, load_pipeline_config
from rada.schemas import MarketEvent

_REPO = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_load_usage_config() -> None:
    config = load_pipeline_config(_REPO / "configs" / "data" / "usage.yaml")
    assert config.mode == "usage"
    assert config.datasources[0].type == "stream"


@pytest.mark.unit
def test_load_export_config() -> None:
    config = load_pipeline_config(_REPO / "configs" / "data" / "export.yaml")
    assert config.mode == "export"
    assert "reflection" in config.sinks


@pytest.mark.unit
def test_usage_runner_stages() -> None:
    config = load_pipeline_config(_REPO / "configs" / "data" / "usage.yaml")
    runner = UsagePipelineRunner(config)
    events = [
        MarketEvent(
            symbol="ETHUSD",
            price=3000.0,
            volume=2.0,
            timestamp=datetime(2026, 6, 1, tzinfo=UTC),
        )
    ]
    results = runner.run_batch(events)
    assert [r.stage for r in results] == ["normalize", "lineage"]
    assert results[-1].records_out == 1


@pytest.mark.unit
def test_export_runner_rejects_usage_config() -> None:
    config = load_pipeline_config(_REPO / "configs" / "data" / "usage.yaml")
    with pytest.raises(ValueError, match="export"):
        ExportPipelineRunner(config)
