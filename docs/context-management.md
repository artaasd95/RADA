# Context management

RADA uses a **token-budget context manager** in `rada.llm_integration.context` to prevent prompt overflow and keep high-value data in the LLM context window.

## Method

1. **Model registry** — `configs/model_context.yaml` maps model IDs/prefixes to `context_window` and `reserve_output_tokens`.
2. **Token estimation** — `tiktoken` when installed, otherwise a conservative chars/4 heuristic.
3. **Priority packing** — `ContextBudget.assemble()` packs segments by priority:
   - `0` system/instructions (protected)
   - `1` verified numerical context and market event (protected / critical)
   - `2` retrieved/supporting evidence
   - `3` history/extras (droppable first)
4. **Adapter output budget** — HTTP and LiteLLM adapters use `resolve_max_tokens()` instead of a hard-coded `256`.

## Settings

| Variable | Purpose |
|----------|---------|
| `RADA_LLM_MAX_CONTEXT_TOKENS` | Cap total context window below the model limit (cost control) |
| `RADA_MODEL_CONTEXT_PATH` | Override path to `model_context.yaml` |
| `LLM YAML extra.max_context_tokens` | Per-deployment cap in `configs/llm_*.yaml` |
| `LLM YAML extra.reserve_output_tokens` | Override completion token reserve |

## RADA-specific usage

Use `build_reasoning_prompt()` from `rada.llm_integration.prompts` to assemble decision prompts with **verified_context** as a protected segment. This prepares the decision path for optional BYOK reasoners without dropping verified calc results.

```python
from rada.llm_integration.prompts import build_reasoning_prompt

assembled = build_reasoning_prompt(
    symbol=event.symbol,
    price=event.price,
    verified_context=verified,
    history=prior_events,
    model_id=config.model_id,
    config=config,
)
prompt = assembled.text
```

Check `assembled.segments_dropped` / `assembled.segments_truncated` in logs when debugging context pressure.
