"""Budget-aware prompt builders for RADA decision reasoning."""

from __future__ import annotations

import json
from typing import Any

from rada.llm_integration.config import LLMConfig
from rada.llm_integration.context import (
    PRIORITY_CRITICAL,
    PRIORITY_HISTORY,
    PRIORITY_SYSTEM,
    AssembledContext,
    ContextBudget,
    ContextSegment,
    max_context_from_env,
)


def build_reasoning_prompt(
    *,
    symbol: str,
    price: float,
    verified_context: dict[str, Any],
    history: list[str] | None = None,
    instructions: str | None = None,
    model_id: str = "mock",
    config: LLMConfig | None = None,
    max_context_override: int | None = None,
) -> AssembledContext:
    """
    Assemble a decision prompt with verified numerical context as protected priority-1.

    Verified context is never dropped; market-event history is the droppable tier.
    """
    override = max_context_override if max_context_override is not None else max_context_from_env()
    segments: list[ContextSegment] = [
        ContextSegment(
            name="instructions",
            content=instructions
            or (
                "You are RADA, a risk-aware decision assistant. "
                "Use verified numerical context for all risk claims."
            ),
            priority=PRIORITY_SYSTEM,
            protected=True,
        ),
        ContextSegment(
            name="verified_context",
            content=(
                "Verified numerical context (do not override):\n"
                f"{json.dumps(verified_context, sort_keys=True)}"
            ),
            priority=PRIORITY_CRITICAL,
            protected=True,
        ),
        ContextSegment(
            name="market_event",
            content=f"Symbol: {symbol}\nPrice: {price}",
            priority=PRIORITY_CRITICAL,
        ),
    ]
    if history:
        segments.append(
            ContextSegment(
                name="history",
                content="\n".join(history),
                priority=PRIORITY_HISTORY,
            )
        )

    budget = ContextBudget(
        model_id,
        config=config,
        max_context_override=override,
    )
    return budget.assemble(segments)
