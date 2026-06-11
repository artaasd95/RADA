from __future__ import annotations

import pytest

from rada.llm_integration.base import Completion, LLMProvider
from rada.llm_integration.config import LLMConfig


def test_completion_dataclass_fields() -> None:
    completion = Completion(
        text="ok",
        model_id="m",
        backend_id="mock",
        token_usage={"prompt_tokens": 1, "completion_tokens": 2},
        latency_ms=1.5,
    )
    assert completion.text == "ok"
    assert completion.backend_id == "mock"


def test_llm_config_resolve_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TEST_LLM_KEY", "secret")
    cfg = LLMConfig(provider="litellm", model_id="x", api_key_env="TEST_LLM_KEY")
    assert cfg.resolve_api_key() == "secret"


@pytest.mark.asyncio
async def test_mock_provider_complete() -> None:
    from rada.llm_integration.adapters.mock_adapter import MockLLMAdapter

    provider = MockLLMAdapter(LLMConfig(provider="mock", model_id="mock"))
    assert isinstance(provider, LLMProvider)
    out = await provider.complete("hello world", "mock")
    assert "mock" in out.text
    assert out.backend_id == "mock"
