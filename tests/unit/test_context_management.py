from __future__ import annotations

import json
from pathlib import Path

import pytest

from rada.llm_integration.config import LLMConfig
from rada.llm_integration.context import (
    PRIORITY_CRITICAL,
    PRIORITY_HISTORY,
    PRIORITY_SYSTEM,
    ContextBudget,
    ContextSegment,
    estimate_tokens,
    resolve_max_tokens,
    resolve_model_limits,
)
from rada.llm_integration.prompts import build_reasoning_prompt


def test_resolve_model_limits_known_model() -> None:
    limits = resolve_model_limits("gpt-4o-mini")
    assert limits.context_window == 128000
    assert limits.reserve_output_tokens == 1024
    assert limits.max_input_tokens == 128000 - 1024


def test_resolve_model_limits_unknown_model_uses_default() -> None:
    limits = resolve_model_limits("totally-unknown-model-xyz")
    assert limits.context_window == 8192
    assert limits.max_input_tokens == 8192 - 256


def test_resolve_model_limits_user_cap_via_config_extra() -> None:
    config = LLMConfig(
        provider="mock",
        model_id="mock",
        extra={"max_context_tokens": 4096, "reserve_output_tokens": 128},
    )
    limits = resolve_model_limits("gpt-4o-mini", config=config)
    assert limits.context_window == 4096
    assert limits.reserve_output_tokens == 128
    assert limits.max_input_tokens == 3968


def test_assemble_keeps_protected_verified_context() -> None:
    budget = ContextBudget("mock", max_context_override=200)
    segments = [
        ContextSegment("instructions", "sys", priority=PRIORITY_SYSTEM, protected=True),
        ContextSegment(
            "verified_context",
            json.dumps({"cvar": 0.03, "position_size": 1.0}),
            priority=PRIORITY_CRITICAL,
            protected=True,
        ),
        ContextSegment(
            "history",
            "x" * 5000,
            priority=PRIORITY_HISTORY,
        ),
    ]
    result = budget.assemble(segments)
    assert "verified_context" in result.segments_kept
    assert "instructions" in result.segments_kept
    assert result.estimated_tokens <= budget.max_input_tokens


def test_assemble_drops_low_priority_before_critical() -> None:
    budget = ContextBudget("mock", max_context_override=120)
    segments = [
        ContextSegment("critical", "keep-me", priority=PRIORITY_CRITICAL, protected=True),
        ContextSegment("history", "drop-me " * 200, priority=PRIORITY_HISTORY),
    ]
    result = budget.assemble(segments)
    assert "critical" in result.segments_kept
    assert "history" in result.segments_dropped or "history" in result.segments_truncated


def test_build_reasoning_prompt_includes_verified_context() -> None:
    assembled = build_reasoning_prompt(
        symbol="BTCUSD",
        price=42000.0,
        verified_context={"cvar": 0.02},
        model_id="mock",
        max_context_override=4096,
    )
    assert "BTCUSD" in assembled.text
    assert "cvar" in assembled.text
    assert "verified_context" in assembled.segments_kept


def test_resolve_max_tokens_from_registry() -> None:
    assert resolve_max_tokens("mock-local") == 256
    assert resolve_max_tokens("mock-local", kwargs_max_tokens=64) == 64


def test_estimate_tokens_heuristic_non_empty() -> None:
    assert estimate_tokens("hello world") >= 1


def test_registry_file_loads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    registry = tmp_path / "registry.yaml"
    registry.write_text(
        "default:\n  context_window: 1000\n  reserve_output_tokens: 50\nmodels: {}\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("RADA_MODEL_CONTEXT_PATH", str(registry))
    limits = resolve_model_limits("anything")
    assert limits.context_window == 1000
    assert limits.max_input_tokens == 950
