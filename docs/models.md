# Qwen model portfolio

Canonical base models for RADA decision/reasoner experiments and LoRA fine-tuning.

## Registry

Portfolio definition: [`configs/models/qwen_portfolio.yaml`](../configs/models/qwen_portfolio.yaml)

| model_id | hub_path | size_tier | instruct | roles |
|----------|----------|-----------|----------|-------|
| qwen3-4b-instruct-2507 | Qwen/Qwen3-4B-Instruct-2507 | medium | yes | decision |
| qwen3-4b | Qwen/Qwen3-4B | medium | no | decision |
| qwen3-0.6b | Qwen/Qwen3-0.6B | small | no | reasoner |
| qwen2.5-coder-3b | Qwen/Qwen2.5-Coder-3B | small | no | decision, reasoner |
| qwen2.5-0.5b | Qwen/Qwen2.5-0.5B | tiny | no | reasoner |
| qwen2.5-3b | Qwen/Qwen2.5-3B | small | no | decision |
| qwen2.5-7b | Qwen/Qwen2.5-7B | large | no | decision, teacher |

## Default pairings

| tier | decision | reasoner |
|------|----------|----------|
| dev | qwen2.5-3b | qwen3-0.6b |
| prod_candidate | qwen3-4b-instruct-2507 | qwen3-0.6b |

Load pairings in code:

```python
from rada.models import load_model_registry

registry = load_model_registry()
dev = registry.get_pairing("dev")
# {"decision": "qwen2.5-3b", "reasoner": "qwen3-0.6b"}
```

## Local storage

Set in `.env`:

```bash
RADA_MODEL_CACHE_ROOT=D:/hf-cache      # read-only base models
RADA_ADAPTER_STORE_ROOT=D:/rada-adapters  # trained LoRA adapters
```

Resolver checks `{cache_root}/{hub_path}` first, then sanitized variants. If missing, downloads via `huggingface_hub.snapshot_download`.

```python
from rada.models import resolve_model_path

path = resolve_model_path("qwen3-0.6b")
```

Cache models with [`notebooks/00_download_models.ipynb`](../notebooks/00_download_models.ipynb).

## Serving with LoRA

After training, adapters include `lora_config.json` compatible with Ray Serve and vLLM:

```yaml
lora_config:
  base_model_id: qwen3-0.6b
  adapter_path: ${RADA_ADAPTER_STORE_ROOT}/smoke-001/qwen3-0.6b
  rank: 16
  alpha: 16
  target_modules: [q_proj, v_proj]
```

### Ray Serve example

```python
from pathlib import Path

from rada.backends import RayServeLLMAdapter

adapter_dir = Path("D:/rada-adapters/smoke-001/qwen3-0.6b")
backend = RayServeLLMAdapter.from_lora_config_file(
    adapter_dir / "lora_config.json",
    model_id="qwen3-0.6b",
)
```

### vLLM example

```python
from rada.backends import VLLMAdapter

backend = VLLMAdapter(model_id="qwen2.5-3b").with_lora(adapter_dir)
```

## Related

- [training.md](./training.md) — LoRA training and adapter layout
- [benchmarks/pre-post-comparison.md](./benchmarks/pre-post-comparison.md) — base vs post-train eval
