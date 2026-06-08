"""Training configuration for reflection/policy LoRA."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

DataSource = Literal["export", "distilled"]
TrainingBackend = Literal["unsloth", "stub"]
TrainingMethod = Literal["policy", "reflection"]


class LoRASettings(BaseModel):
    rank: int = 16
    alpha: int = 16
    target_modules: list[str] = Field(default_factory=lambda: ["q_proj", "v_proj"])
    dropout: float = 0.0


class TrainingConfig(BaseModel):
    model_id: str
    backend: TrainingBackend = "stub"
    data_source: DataSource = "export"
    data_path: Path | None = None
    distilled_name: str | None = None
    method: TrainingMethod = "reflection"
    epochs: int = 1
    batch_size: int = 2
    learning_rate: float = 2e-4
    max_seq_length: int = 512
    output_run_id: str = "default"
    checkpoint_interval: int = 100
    checkpoint_keep_last: int = 3
    resume_from: str | None = None
    lora: LoRASettings = Field(default_factory=LoRASettings)
