from __future__ import annotations

import json

import pytest
import torch

from rada.adapters import RaftLMTrainedModelAdapter
from rada.schemas import ActionDirection, MarketEvent


@pytest.mark.integration
@pytest.mark.asyncio
async def test_raft_adapter_loads_manifest_and_proposes(tmp_path) -> None:
    checkpoint_path = tmp_path / "model_checkpoint.pt"
    torch.save({"model_state_dict": {"w": torch.zeros((1,))}}, checkpoint_path)
    manifest_path = tmp_path / "export_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "format": "rada_checkpoint_export_v1",
                "checkpoint_file": "model_checkpoint.pt",
                "model_id": "test-model",
            }
        ),
        encoding="utf-8",
    )

    adapter = RaftLMTrainedModelAdapter(manifest_path)
    event = MarketEvent.model_validate(
        {
            "symbol": "BTCUSD",
            "price": 48000.0,
            "volume": 1.0,
            "timestamp": "2026-01-01T00:00:00Z",
        }
    )
    trace = await adapter.reason(event)
    action = await adapter.propose_from_event(event)

    assert trace.model_name == "raft-lm-trained-adapter"
    assert action.direction in {ActionDirection.BUY, ActionDirection.SELL, ActionDirection.HOLD}
