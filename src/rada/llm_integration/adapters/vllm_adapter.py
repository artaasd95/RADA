"""vLLM OpenAI-compatible adapter (localhost:8000 default)."""

from __future__ import annotations

from rada.llm_integration.adapters._http_base import OpenAICompatibleAdapter
from rada.llm_integration.config import LLMConfig


class VLLMAdapter(OpenAICompatibleAdapter):
    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config, backend_id="vllm", default_base_url="http://localhost:8000")
