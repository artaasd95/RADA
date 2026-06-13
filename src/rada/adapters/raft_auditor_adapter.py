"""Adapter that loads raft-lm exported checkpoints for RADA decisioning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch

from rada.interfaces import BaseReasoner
from rada.schemas import ActionDirection, DecisionTrace, MarketEvent, ProposedAction


class RaftLMTrainedModelAdapter(BaseReasoner):
    """Checkpoint-backed reasoner for tool-aware policies."""

    def __init__(self, export_manifest_path: str | Path) -> None:
        self._manifest_path = Path(export_manifest_path)
        manifest = json.loads(self._manifest_path.read_text(encoding="utf-8"))
        self._manifest = manifest
        checkpoint_file = manifest.get("checkpoint_file", "model_checkpoint.pt")
        self._checkpoint_path = self._manifest_path.parent / checkpoint_file
        self._state = torch.load(self._checkpoint_path, map_location="cpu", weights_only=False)

    @property
    def model_id(self) -> str:
        return str(self._manifest.get("model_id", "unknown"))

    async def reason(self, event: MarketEvent) -> DecisionTrace:
        rationale = (
            f"Raft adapter {self.model_id} inspected {event.symbol} price={event.price:.2f} "
            f"volume={event.volume:.4f}"
        )
        return DecisionTrace(
            model_name="raft-lm-trained-adapter",
            rationale=rationale,
            assumptions=[f"manifest={self._manifest_path.name}"],
            faithfulness_score=0.8,
        )

    async def propose_from_event(self, event: MarketEvent) -> ProposedAction:
        # Deterministic heuristic placeholder until full model head is integrated.
        if event.volume <= 0:
            return ProposedAction(direction=ActionDirection.HOLD, size=0.0, cvar_impact=0.0)
        if event.price < 50000:
            return ProposedAction(direction=ActionDirection.BUY, size=min(event.volume, 2.0), cvar_impact=0.03)
        if event.price > 70000:
            return ProposedAction(direction=ActionDirection.SELL, size=min(event.volume, 2.0), cvar_impact=0.04)
        return ProposedAction(direction=ActionDirection.HOLD, size=0.0, cvar_impact=0.01)
