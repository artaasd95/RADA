# LLM integration (BYOK)

RADA uses the `llm_integration` layer for runtime reasoning. Local runtime defaults to a real provider, while tests and CI stay on mock mode for deterministic validation.

## Providers

| Provider | Config | Use case |
|----------|--------|----------|
| `ollama` | `configs/llm_ollama.yaml` | Default local runtime with Qwen |
| `litellm` | `configs/llm_cloud.yaml` | BYOK cloud fallback via `OPENAI_API_KEY` |
| `mock` | `configs/llm_mock.yaml` | Tests, CI, explicit offline mode |
| `vllm` | `configs/llm_single_gpu.yaml` | Single-GPU self-hosted |
| `ray_serve` | `configs/llm_distributed.yaml` | Multi-replica (mock without cluster in tests) |
| `custom` | `configs/llm_custom.yaml` | Internal endpoint template |

## Default runtime behavior

- `RADA_REASONER_MODE=real` uses the LLM-backed reasoner.
- `configs/llm_ollama.yaml` is the default primary config.
- `configs/llm_cloud.yaml` is the BYOK fallback path for OpenAI-compatible providers.
- `RADA_REASONER_MODE=mock` keeps the deterministic scenario reasoner for tests or demos.

## Usage

```python
from rada.llm_integration import create_llm_provider

provider = create_llm_provider("configs/llm_ollama.yaml")
completion = await provider.complete("Summarize risk posture", "qwen2.5:0.5b")
```

Set `RADA_LLM_CONFIG_PATH` for the FastAPI app when overriding the default. API keys are read from env vars named in YAML (`api_key_env`) and should never be committed.

## FAQ

- **Is LiteLLM required?** No. It is only needed for BYOK cloud routing.
- **What is the default model?** Local `qwen2.5:0.5b` through Ollama.
- **What happens when Ollama is unavailable?** The real reasoner falls back to the cloud config, which itself degrades to mock mode when keys or LiteLLM are absent.
- **Training jobs?** Use platform-managed training; do not wire BYOK into `reflection_train.py` defaults.
- **Custom backends?** See `src/rada/llm_integration/adapters/README_CUSTOM.md`.
