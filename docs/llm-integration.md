# LLM integration (BYOK)

RADA uses an optional `llm_integration` layer for **runtime inference only**. Training, CI, and committed configs default to the offline `mock` provider.

## Providers

| Provider | Config | Use case |
|----------|--------|----------|
| `mock` | `configs/llm_mock.yaml` | Default offline/tests |
| `vllm` | `configs/llm_single_gpu.yaml` | Single-GPU self-hosted |
| `ray_serve` | `configs/llm_distributed.yaml` | Multi-replica (mock without cluster in tests) |
| `litellm` | `configs/llm_cloud.yaml` | Cloud BYOK via `OPENAI_API_KEY` |
| `ollama` | `configs/llm_ollama.yaml` | Local lightweight |
| `custom` | `configs/llm_custom.yaml` | Internal endpoint template |

## Usage

```python
from rada.llm_integration import create_llm_provider

provider = create_llm_provider("configs/llm_mock.yaml")
completion = await provider.complete("Summarize risk posture", "mock")
```

Set `RADA_LLM_CONFIG_PATH` for the FastAPI app. API keys are read from env vars named in YAML (`api_key_env`) — never commit secrets.

## FAQ

- **Is LiteLLM required?** No — cloud adapter falls back to mock when LiteLLM or keys are absent.
- **Training jobs?** Use platform-managed training; do not wire BYOK into `reflection_train.py` defaults.
- **Custom backends?** See `src/rada/llm_integration/adapters/README_CUSTOM.md`.
