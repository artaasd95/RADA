from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from rada.llm_integration.adapters._http_base import OpenAICompatibleAdapter
from rada.llm_integration.config import LLMConfig


@pytest.mark.unit
@pytest.mark.asyncio
async def test_http_adapter_retries_transient_error() -> None:
    config = LLMConfig(provider="custom", model_id="test-model", base_url="http://localhost:9000")
    adapter = OpenAICompatibleAdapter(config, backend_id="test", default_base_url="http://localhost:9000")

    response_ok = httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": "ok"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        },
        request=httpx.Request("POST", "http://localhost:9000/v1/chat/completions"),
    )
    response_fail = httpx.Response(
        503,
        request=httpx.Request("POST", "http://localhost:9000/v1/chat/completions"),
    )

    mock_client = AsyncMock()
    mock_client.is_closed = False
    mock_client.post = AsyncMock(side_effect=[response_fail, response_ok])

    with patch.object(adapter, "_get_client", return_value=mock_client):
        completion = await adapter.complete("hello", "test-model")

    assert completion.text == "ok"
    assert mock_client.post.await_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_http_adapter_rejects_empty_choices() -> None:
    config = LLMConfig(provider="custom", model_id="test-model", base_url="http://localhost:9000")
    adapter = OpenAICompatibleAdapter(config, backend_id="test", default_base_url="http://localhost:9000")

    response_ok = httpx.Response(
        200,
        json={"choices": []},
        request=httpx.Request("POST", "http://localhost:9000/v1/chat/completions"),
    )
    mock_client = AsyncMock()
    mock_client.is_closed = False
    mock_client.post = AsyncMock(return_value=response_ok)

    with patch.object(adapter, "_get_client", return_value=mock_client):
        with pytest.raises(ValueError, match="missing choices"):
            await adapter.complete("hello", "test-model")
