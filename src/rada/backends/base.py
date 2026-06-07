"""LLM backend contracts for decision/reasoner experiments."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from pydantic import BaseModel, Field


class LLMCompletion(BaseModel):
    """Model response metadata for training and serving."""

    text: str
    model_id: str
    adapter_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)


class LoRAConfig(BaseModel):
    """PEFT adapter contract compatible with Ray Serve / vLLM deploy snippets."""

    base_model_id: str
    adapter_path: str
    rank: int = 16
    alpha: int = 16
    target_modules: list[str] = Field(default_factory=lambda: ["q_proj", "v_proj"])


class BaseLLMBackend(ABC):
    """Abstract LLM backend behind decision/reasoner policy updates."""

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Canonical registry model id."""

    @property
    def adapter_id(self) -> str | None:
        """Optional LoRA adapter id when loaded."""
        return None

    @abstractmethod
    async def complete(self, prompt: str, **kwargs: object) -> LLMCompletion:
        """Return a completion for the given prompt."""

    @abstractmethod
    def with_lora(self, adapter_path: Path) -> BaseLLMBackend:
        """Return a backend instance with the given PEFT adapter loaded."""
