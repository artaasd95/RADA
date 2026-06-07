# Training — Unsloth LoRA / PEFT

Offline training for reflection and policy updates. Training stays off the RADA hot path; consume exported or distilled JSONL artifacts.

## Overview

| Component | Path |
|-----------|------|
| Trainer | `src/rada/training/unsloth_trainer.py` |
| CLI | `scripts/reflection_train.py` |
| Dataset loaders | `src/rada/training/dataset.py` |
| Adapter export | `src/rada/training/adapter_export.py` |
| Model registry | `configs/models/qwen_portfolio.yaml` |

## Environment

```bash
RADA_MODEL_CACHE_ROOT=D:/hf-cache       # local base models (checked before Hub download)
RADA_ADAPTER_STORE_ROOT=D:/rada-adapters  # trained LoRA output
```

See [models.md](./models.md) for the Qwen portfolio and default decision/reasoner pairings.

## Install

Core package (CI, no GPU):

```bash
pip install -e ".[dev]"
```

GPU training with Unsloth (CUDA recommended; WSL2 on Windows):

```bash
pip install -e ".[unsloth]"
```

Notebooks:

```bash
pip install -e ".[notebooks]"
```

## Data sources

### Export (`data_source=export`)

Use JSONL from `scripts/export_reflection.py` or `export_decisions()` — each line is a `FeedbackRecord`.

### Distilled (`data_source=distilled`)

Teacher-generated corpora under `data/distilled/<name>/`. See [Distillation](#distillation) below.

## Train

Stub backend (CI / smoke, no GPU):

```bash
python scripts/reflection_train.py \
  --backend stub \
  --model-id qwen3-0.6b \
  --data benchmarks/training/toy_feedback.jsonl \
  --epochs 1 \
  --output-run-id smoke-001
```

Unsloth LoRA (GPU):

```bash
python scripts/reflection_train.py \
  --backend unsloth \
  --model-id qwen3-0.6b \
  --data path/to/feedback.jsonl \
  --epochs 1 \
  --output-run-id run-001
```

Distilled corpus:

```bash
python scripts/reflection_train.py \
  --backend stub \
  --model-id qwen2.5-3b \
  --data-source distilled \
  --distilled-name rada-v1 \
  --output-run-id distill-001
```

## Adapter layout

After training, artifacts land at:

```
{RADA_ADAPTER_STORE_ROOT}/{run_id}/{model_id}/
  adapter_config.json
  adapter_model.bin          # or safetensors with unsloth backend
  training_manifest.json
  lora_config.json           # Ray Serve / vLLM contract
```

Load in a stub backend for smoke tests:

```python
from pathlib import Path

from rada.backends import StubLLMBackend

backend = StubLLMBackend(model_id="qwen3-0.6b").with_lora(
    Path("D:/rada-adapters/smoke-001/qwen3-0.6b")
)
```

## Serving with lora_config

`lora_config.json` is emitted alongside PEFT weights. Use with `RayServeLLMAdapter` or `VLLMAdapter` — see [models.md](./models.md).

## Distillation

**Decision: Yes — required.**

Reflection and policy LoRA benefit from denser supervision than sparse runtime `FeedbackRecord` exports alone. The `ReflectionLoop` policy updater and `FeedbackRecord` training pipeline need higher-volume, teacher-aligned traces for stable SFT.

| Item | Location |
|------|----------|
| Colab notebook | `notebooks/distill_teacher_colab.ipynb` |
| Corpus layout | `data/distilled/<name>/` |
| Manifest | `data/distilled/<name>/manifest.json` |
| Training loader | `--data-source distilled --distilled-name <name>` |

**Rationale:** Runtime exports capture live decisions but are sparse. A stronger teacher (e.g. `qwen2.5-7b` or `qwen3-4b-instruct-2507`) generates decision/reflection traces aligned to `DecisionExportRow` / `FeedbackRecord`, improving label quality and volume for reflection_loop policy updates.

**Workflow:**

1. Export reflection JSONL from RADA (`scripts/export_reflection.py`).
2. Run `notebooks/distill_teacher_colab.ipynb` on Colab GPU with `HF_TOKEN` in secrets.
3. Upload output to `data/distilled/rada-v1/train.jsonl` with `manifest.json`.
4. Train with `--data-source distilled --distilled-name rada-v1`.

See `data/distilled/README.md` for manifest schema.

## Pre vs post-train comparison

Compare base model vs LoRA adapter on the same fixtures:

```bash
python scripts/compare_pre_post_train.py \
  --model-id qwen3-0.6b \
  --fixtures benchmarks/training/toy_feedback.jsonl
```

See [benchmarks/pre-post-comparison.md](./benchmarks/pre-post-comparison.md).

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `model not found locally` | Set `RADA_MODEL_CACHE_ROOT` or run `notebooks/00_download_models.ipynb` |
| Unsloth import error | `pip install -e ".[unsloth]"` on CUDA environment |
| CI without GPU | Use `--backend stub` |
| Distilled corpus missing | Generate via Colab notebook; check `manifest.json` |

## Related

- [models.md](./models.md)
- [data-platform.md](./data-platform.md)
- [architecture-overview.md](./architecture-overview.md)
