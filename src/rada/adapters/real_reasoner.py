"""LLM-backed reasoner with local-first and BYOK fallback behavior."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from rada.interfaces import BaseReasoner
from rada.llm_integration.base import Completion, LLMProvider
from rada.llm_integration.config import LLMConfig
from rada.llm_integration.factory import create_llm_provider
from rada.llm_integration.prompts import build_reasoning_prompt
from rada.schemas import DecisionTrace, MarketEvent

logger = logging.getLogger(__name__)

_DEFAULT_INSTRUCTIONS = (
    "You are RADA, a risk-aware decision reasoning engine. "
    "Summarize the market state, point out the dominant risk signal, and keep the "
    "explanation concise and operational."
)


def _load_llm_config(config_path: str | Path) -> LLMConfig:
    path = Path(config_path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return LLMConfig.model_validate(raw)


class RealReasoner(BaseReasoner):
    """Build decision traces from a configured LLM provider."""

    def __init__(
        self,
        *,
        primary_provider: LLMProvider,
        primary_config: LLMConfig,
        fallback_provider: LLMProvider | None = None,
        fallback_config: LLMConfig | None = None,
    ) -> None:
        self._primary_provider = primary_provider
        self._primary_config = primary_config
        self._fallback_provider = fallback_provider
        self._fallback_config = fallback_config

    @classmethod
    def from_config_paths(
        cls,
        primary_path: str | Path,
        fallback_path: str | Path | None = None,
    ) -> RealReasoner:
        primary_config = _load_llm_config(primary_path)
        fallback_config = _load_llm_config(fallback_path) if fallback_path else None
        return cls(
            primary_provider=create_llm_provider(primary_path),
            primary_config=primary_config,
            fallback_provider=create_llm_provider(fallback_path) if fallback_path else None,
            fallback_config=fallback_config,
        )

    async def reason(self, event: MarketEvent) -> DecisionTrace:
        prompt = build_reasoning_prompt(
            symbol=event.symbol,
            price=event.price,
            verified_context={"price": event.price, "volume": event.volume},
            instructions=_DEFAULT_INSTRUCTIONS,
            model_id=self._primary_config.model_id,
            config=self._primary_config,
        )

        warnings: list[str] = []
        completion, warnings = await self._complete_with_fallback(prompt.text, warnings)
        assumptions = [
            f"provider={completion.backend_id}",
            f"prompt_tokens={completion.token_usage.get('prompt_tokens', 0)}",
            f"completion_tokens={completion.token_usage.get('completion_tokens', 0)}",
        ]
        faithfulness = 0.55 if completion.backend_id == "mock" else 0.8

        return DecisionTrace(
            model_name=f"{completion.backend_id}:{completion.model_id}",
            rationale=completion.text.strip(),
            assumptions=assumptions,
            warnings=warnings,
            faithfulness_score=faithfulness,
            verified_context={"price": event.price, "volume": event.volume},
        )

    async def _complete_with_fallback(
        self,
        prompt: str,
        warnings: list[str],
    ) -> tuple[Completion, list[str]]:
        try:
            completion = await self._primary_provider.complete(
                prompt,
                self._primary_config.model_id,
            )
            return completion, warnings
        except Exception as exc:  # noqa: BLE001
            logger.warning("primary reasoner provider failed: %s", exc)
            warnings.append(f"primary_provider_failed={type(exc).__name__}")

        if self._fallback_provider is not None and self._fallback_config is not None:
            try:
                completion = await self._fallback_provider.complete(
                    prompt,
                    self._fallback_config.model_id,
                )
                warnings.append("fallback_provider_used")
                return completion, warnings
            except Exception as exc:  # noqa: BLE001
                logger.warning("fallback reasoner provider failed: %s", exc)
                warnings.append(f"fallback_provider_failed={type(exc).__name__}")

        completion = await self._primary_provider.complete(prompt, self._primary_config.model_id)
        return completion, warnings