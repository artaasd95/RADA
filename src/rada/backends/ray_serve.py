"""Ray Serve LLM adapter with lora_config contract."""

from __future__ import annotations

import json
from pathlib import Path

from rada.backends.base import BaseLLMBackend, LLMCompletion, LoRAConfig
from rada.backends.stub import StubLLMBackend


class RayServeLLMAdapter(BaseLLMBackend):
    """Thin Ray Serve wrapper; delegates to stub until Ray runtime is wired."""

    def __init__(
        self,
        *,
        model_id: str,
        lora_config: LoRAConfig | None = None,
        endpoint: str | None = None,
    ) -> None:
        self._model_id = model_id
        self._lora_config = lora_config
        self._endpoint = endpoint
        adapter_path = Path(lora_config.adapter_path) if lora_config else None
        self._delegate = StubLLMBackend(model_id=model_id, adapter_path=adapter_path)

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def adapter_id(self) -> str | None:
        return self._delegate.adapter_id

    @property
    def lora_config(self) -> LoRAConfig | None:
        return self._lora_config

    @classmethod
    def from_lora_config_file(cls, path: Path, *, model_id: str) -> RayServeLLMAdapter:
        data = json.loads(path.read_text(encoding="utf-8"))
        lora = LoRAConfig.model_validate(data)
        return cls(model_id=model_id, lora_config=lora)

    async def complete(self, prompt: str, **kwargs: object) -> LLMCompletion:
        completion = await self._delegate.complete(prompt, **kwargs)
        meta = dict(completion.metadata)
        meta["backend"] = "ray_serve"
        if self._endpoint:
            meta["endpoint"] = self._endpoint
        return completion.model_copy(update={"metadata": meta})

    def with_lora(self, adapter_path: Path) -> RayServeLLMAdapter:
        lora_path = adapter_path / "lora_config.json"
        if lora_path.exists():
            lora = LoRAConfig.model_validate_json(lora_path.read_text(encoding="utf-8"))
            return RayServeLLMAdapter(model_id=self._model_id, lora_config=lora)
        lora = LoRAConfig(
            base_model_id=self._model_id,
            adapter_path=str(adapter_path),
        )
        return RayServeLLMAdapter(model_id=self._model_id, lora_config=lora)
