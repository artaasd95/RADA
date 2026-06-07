"""Deterministic LLM backend for CI and smoke tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from rada.backends.base import BaseLLMBackend, LLMCompletion


class StubLLMBackend(BaseLLMBackend):
    """Returns deterministic completions; simulates LoRA via adapter path hash."""

    def __init__(
        self,
        *,
        model_id: str,
        adapter_path: Path | None = None,
    ) -> None:
        self._model_id = model_id
        self._adapter_path = adapter_path
        self._adapter_id: str | None = None
        if adapter_path is not None:
            self._adapter_id = self._derive_adapter_id(adapter_path)

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def adapter_id(self) -> str | None:
        return self._adapter_id

    @staticmethod
    def _derive_adapter_id(adapter_path: Path) -> str:
        manifest = adapter_path / "training_manifest.json"
        if manifest.exists():
            data = json.loads(manifest.read_text(encoding="utf-8"))
            return str(data.get("adapter_id", adapter_path.name))
        return adapter_path.name

    async def complete(self, prompt: str, **kwargs: object) -> LLMCompletion:
        digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8]
        prefix = f"[{self._model_id}"
        if self._adapter_id:
            prefix += f"+{self._adapter_id}"
        prefix += "]"
        return LLMCompletion(
            text=f"{prefix} stub:{digest}",
            model_id=self._model_id,
            adapter_id=self._adapter_id,
            metadata={"backend": "stub"},
        )

    def with_lora(self, adapter_path: Path) -> StubLLMBackend:
        if not adapter_path.exists():
            msg = f"adapter path does not exist: {adapter_path}"
            raise FileNotFoundError(msg)
        return StubLLMBackend(model_id=self._model_id, adapter_path=adapter_path)
