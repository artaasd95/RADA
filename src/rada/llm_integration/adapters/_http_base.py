"""Shared HTTP helper for OpenAI-compatible adapters."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from rada.llm_integration.base import Completion, LLMProvider
from rada.llm_integration.config import LLMConfig
from rada.llm_integration.context import resolve_max_tokens

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_RETRY_STATUS_CODES = {408, 429, 500, 502, 503, 504}


class OpenAICompatibleAdapter(LLMProvider):
    """Base for vLLM/Ollama/custom OpenAI-compatible endpoints."""

    def __init__(self, config: LLMConfig, *, backend_id: str, default_base_url: str) -> None:
        self._config = config
        self._backend_id = backend_id
        self._base_url = (config.base_url or default_base_url).rstrip("/")
        self._client: httpx.AsyncClient | None = None

    @property
    def backend_id(self) -> str:
        return self._backend_id

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=60.0)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _extract_completion_text(self, data: dict[str, Any]) -> str:
        choices = data.get("choices")
        if not choices:
            msg = "LLM response missing choices"
            raise ValueError(msg)
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            msg = "LLM response missing message"
            raise ValueError(msg)
        content = message.get("content")
        if content is None:
            msg = "LLM response content is null"
            raise ValueError(msg)
        return str(content)

    async def _post_with_retries(
        self,
        url: str,
        *,
        payload: dict[str, Any],
        headers: dict[str, str],
    ) -> dict[str, Any]:
        client = await self._get_client()
        last_error: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code in _RETRY_STATUS_CODES and attempt < _MAX_RETRIES - 1:
                    await response.aread()
                    continue
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt >= _MAX_RETRIES - 1:
                    break
        if last_error is not None:
            raise last_error
        msg = "LLM request failed without error"
        raise RuntimeError(msg)

    async def complete(self, prompt: str, model_id: str, **kwargs: Any) -> Completion:
        api_key = self._config.resolve_api_key()
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        max_tokens = resolve_max_tokens(
            model_id,
            config=self._config,
            kwargs_max_tokens=kwargs.get("max_tokens"),
        )
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
        url = f"{self._base_url}/v1/chat/completions"
        started = time.perf_counter()
        data = await self._post_with_retries(url, payload=payload, headers=headers)
        choice = self._extract_completion_text(data)
        usage = data.get("usage", {})
        latency_ms = (time.perf_counter() - started) * 1000
        return Completion(
            text=choice,
            model_id=model_id,
            backend_id=self._backend_id,
            token_usage={
                "prompt_tokens": int(usage.get("prompt_tokens", 0)),
                "completion_tokens": int(usage.get("completion_tokens", 0)),
            },
            latency_ms=latency_ms,
        )
