"""Token-budget context assembly for LLM prompts."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from rada.llm_integration.config import LLMConfig

logger = logging.getLogger(__name__)

DEFAULT_CONTEXT_WINDOW = 8192
DEFAULT_RESERVE_OUTPUT = 256
DEFAULT_REGISTRY_PATH = Path("configs/model_context.yaml")
CHARS_PER_TOKEN_HEURISTIC = 4
HEURISTIC_SAFETY_MARGIN = 1.1

PRIORITY_SYSTEM = 0
PRIORITY_CRITICAL = 1
PRIORITY_RETRIEVED = 2
PRIORITY_HISTORY = 3


@dataclass(slots=True)
class ContextSegment:
    """One logical block in a prompt with packing priority."""

    name: str
    content: str
    priority: int = PRIORITY_RETRIEVED
    protected: bool = False


@dataclass(slots=True)
class ModelContextLimits:
    context_window: int
    reserve_output_tokens: int
    max_input_tokens: int


@dataclass(slots=True)
class AssembledContext:
    text: str
    segments_kept: list[str] = field(default_factory=list)
    segments_dropped: list[str] = field(default_factory=list)
    segments_truncated: list[str] = field(default_factory=list)
    estimated_tokens: int = 0
    max_input_tokens: int = 0
    reserve_output_tokens: int = 0

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "segments_kept": self.segments_kept,
            "segments_dropped": self.segments_dropped,
            "segments_truncated": self.segments_truncated,
            "estimated_tokens": self.estimated_tokens,
            "max_input_tokens": self.max_input_tokens,
            "reserve_output_tokens": self.reserve_output_tokens,
        }


def estimate_tokens(text: str, *, model_id: str = "gpt-4") -> int:
    """Estimate token count; prefers tiktoken when available."""
    if not text:
        return 0
    try:
        import tiktoken

        try:
            enc = tiktoken.encoding_for_model(model_id)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        return max(1, int(len(text) / CHARS_PER_TOKEN_HEURISTIC * HEURISTIC_SAFETY_MARGIN))


def max_context_from_env() -> int | None:
    val = os.getenv("RADA_LLM_MAX_CONTEXT_TOKENS")
    return int(val) if val else None


def load_model_registry(path: Path | str | None = None) -> dict[str, Any]:
    registry_path = Path(
        path or os.getenv("RADA_MODEL_CONTEXT_PATH", DEFAULT_REGISTRY_PATH)
    )
    if not registry_path.exists():
        return {
            "default": {
                "context_window": DEFAULT_CONTEXT_WINDOW,
                "reserve_output_tokens": DEFAULT_RESERVE_OUTPUT,
            },
            "models": {},
        }
    raw = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    return raw


def _match_model_entry(model_id: str, models: dict[str, Any]) -> dict[str, Any] | None:
    if model_id in models:
        return models[model_id]
    model_id_lower = model_id.lower()
    best_key = ""
    best_entry: dict[str, Any] | None = None
    for key, entry in models.items():
        key_lower = key.lower()
        if model_id_lower.startswith(key_lower) or key_lower in model_id_lower:
            if len(key) > len(best_key):
                best_key = key
                best_entry = entry
    return best_entry


def resolve_model_limits(
    model_id: str,
    *,
    registry: dict[str, Any] | None = None,
    config: LLMConfig | None = None,
    max_context_override: int | None = None,
) -> ModelContextLimits:
    reg = registry or load_model_registry()
    default = reg.get("default", {})
    models = reg.get("models", {})
    entry = _match_model_entry(model_id, models) or default

    context_window = int(entry.get("context_window", DEFAULT_CONTEXT_WINDOW))
    reserve_output = int(entry.get("reserve_output_tokens", DEFAULT_RESERVE_OUTPUT))

    if config:
        extra = config.extra or {}
        if "context_window" in extra:
            context_window = int(extra["context_window"])
        if "reserve_output_tokens" in extra:
            reserve_output = int(extra["reserve_output_tokens"])
        if "max_context_tokens" in extra:
            cap = int(extra["max_context_tokens"])
            max_context_override = (
                cap if max_context_override is None else min(max_context_override, cap)
            )

    env_cap = max_context_from_env()
    if env_cap is not None:
        max_context_override = (
            env_cap
            if max_context_override is None
            else min(max_context_override, env_cap)
        )

    if max_context_override is not None:
        context_window = min(context_window, max_context_override)

    max_input = max(1, context_window - reserve_output)
    return ModelContextLimits(
        context_window=context_window,
        reserve_output_tokens=reserve_output,
        max_input_tokens=max_input,
    )


def _truncate_to_tokens(text: str, max_tokens: int, *, model_id: str) -> str:
    if max_tokens <= 0 or not text:
        return ""
    if estimate_tokens(text, model_id=model_id) <= max_tokens:
        return text
    lo, hi = 0, len(text)
    best = ""
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = text[:mid]
        if estimate_tokens(candidate, model_id=model_id) <= max_tokens:
            best = candidate
            lo = mid + 1
        else:
            hi = mid - 1
    return best.rstrip() if best else ""


class ContextBudget:
    """Assemble prioritized prompt segments within a model's input token budget."""

    def __init__(
        self,
        model_id: str,
        *,
        config: LLMConfig | None = None,
        registry: dict[str, Any] | None = None,
        max_context_override: int | None = None,
    ) -> None:
        self.model_id = model_id
        self.config = config
        self.limits = resolve_model_limits(
            model_id,
            registry=registry,
            config=config,
            max_context_override=max_context_override,
        )

    @property
    def max_input_tokens(self) -> int:
        return self.limits.max_input_tokens

    @property
    def reserve_output_tokens(self) -> int:
        return self.limits.reserve_output_tokens

    def assemble(self, segments: list[ContextSegment]) -> AssembledContext:
        if not segments:
            return AssembledContext(
                text="",
                max_input_tokens=self.max_input_tokens,
                reserve_output_tokens=self.reserve_output_tokens,
            )

        order = {seg.name: idx for idx, seg in enumerate(segments)}
        protected = [seg for seg in segments if seg.protected]
        unprotected = [seg for seg in segments if not seg.protected]
        ranked_unprotected = sorted(unprotected, key=lambda s: (s.priority, order[s.name]))

        kept: list[tuple[str, str]] = []
        dropped: list[str] = []
        truncated: list[str] = []
        budget = self.max_input_tokens

        def _separator_reserve(count: int) -> int:
            if count <= 1:
                return 0
            return estimate_tokens("\n\n" * (count - 1), model_id=self.model_id)

        for seg in protected:
            tokens = estimate_tokens(seg.content, model_id=self.model_id)
            reserve = _separator_reserve(len(kept) + 1)
            if tokens + reserve > budget:
                trimmed = _truncate_to_tokens(
                    seg.content,
                    max(1, budget - reserve),
                    model_id=self.model_id,
                )
                if trimmed:
                    kept.append((seg.name, trimmed))
                    truncated.append(seg.name)
                    budget -= estimate_tokens(trimmed, model_id=self.model_id) + reserve
                else:
                    dropped.append(seg.name)
                continue
            kept.append((seg.name, seg.content))
            budget -= tokens + reserve

        for seg in ranked_unprotected:
            tokens = estimate_tokens(seg.content, model_id=self.model_id)
            reserve = _separator_reserve(len(kept) + 1)
            if tokens + reserve <= budget:
                kept.append((seg.name, seg.content))
                budget -= tokens + reserve
                continue

            remaining = budget - reserve
            if remaining > 0:
                trimmed = _truncate_to_tokens(seg.content, remaining, model_id=self.model_id)
                if trimmed:
                    kept.append((seg.name, trimmed))
                    truncated.append(seg.name)
                    budget -= estimate_tokens(trimmed, model_id=self.model_id) + reserve
                    continue

            dropped.append(seg.name)

        kept.sort(key=lambda pair: order.get(pair[0], 999))
        text = "\n\n".join(content for _, content in kept if content)
        estimated = estimate_tokens(text, model_id=self.model_id)

        result = AssembledContext(
            text=text,
            segments_kept=[name for name, _ in kept],
            segments_dropped=dropped,
            segments_truncated=truncated,
            estimated_tokens=estimated,
            max_input_tokens=self.max_input_tokens,
            reserve_output_tokens=self.reserve_output_tokens,
        )
        logger.debug("assembled context: %s", result.to_log_dict())
        return result


def assemble_context(
    segments: list[ContextSegment],
    model_id: str,
    *,
    config: LLMConfig | None = None,
    max_context_override: int | None = None,
) -> AssembledContext:
    """Convenience wrapper around ContextBudget.assemble."""
    return ContextBudget(
        model_id,
        config=config,
        max_context_override=max_context_override,
    ).assemble(segments)


def resolve_max_tokens(
    model_id: str,
    *,
    config: LLMConfig | None = None,
    kwargs_max_tokens: int | None = None,
    max_context_override: int | None = None,
) -> int:
    """Resolve completion max_tokens from model budget unless explicitly overridden."""
    if kwargs_max_tokens is not None:
        return int(kwargs_max_tokens)
    limits = resolve_model_limits(
        model_id,
        config=config,
        max_context_override=max_context_override,
    )
    return limits.reserve_output_tokens
