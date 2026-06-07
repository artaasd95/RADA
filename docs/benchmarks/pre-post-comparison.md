# Pre vs post-train comparison

Protocol for measuring decision and reflection quality **before** and **after** Unsloth LoRA fine-tuning on the same fixtures.

## Goal

For each base model (e.g. `qwen3-0.6b`), compare:

- **Pre:** registry base model (no adapter)
- **Post:** same base + LoRA adapter trained on fixture or production JSONL

Report per-metric deltas for hire-me demo narratives.

## Metrics

| Metric | Description |
|--------|-------------|
| `risk_gate_pass_rate` | Share of fixture cases passing CVaR risk gate |
| `mean_audit_score` | Mean faithfulness from `ReflectionLoop` + auditor |
| `reflection_quality` | Mean `FeedbackLabels.score` on fixture set |

## Run

```bash
python scripts/compare_pre_post_train.py \
  --model-id qwen3-0.6b \
  --fixtures benchmarks/training/toy_feedback.jsonl \
  --output reports/pre_post_qwen3-0.6b.json
```

Options:

- `--methods policy,reflection` — tag training methods (default: `reflection`)
- `--adapter path/to/adapter` — skip mini-train, use existing adapter
- `--no-train` — eval only with `--adapter`

## Example output

```json
{
  "model_id": "qwen3-0.6b",
  "pre": {
    "risk_gate_pass_rate": 1.0,
    "mean_audit_score": 0.5,
    "reflection_quality": 0.85,
    "cases": 15
  },
  "post": {
    "risk_gate_pass_rate": 1.0,
    "mean_audit_score": 0.7,
    "reflection_quality": 0.85,
    "cases": 15
  },
  "delta": {
    "risk_gate_pass_rate": 0.0,
    "mean_audit_score": 0.2,
    "reflection_quality": 0.0
  }
}
```

## CI

Integration test `tests/integration/test_pre_post_compare.py` uses stub trainer and mock adapters — no GPU required.

## Related

- [training.md](../training.md)
- [models.md](../models.md)
