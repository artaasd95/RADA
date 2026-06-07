# Distilled training corpora

Teacher-generated JSONL aligned with `FeedbackRecord` for reflection/policy LoRA training.

## Layout

```
data/distilled/
  <name>/
    manifest.json    # corpus metadata (required)
    train.jsonl      # one FeedbackRecord per line
```

Corpus directories are gitignored; only this README is committed. Generate corpora via `notebooks/distill_teacher_colab.ipynb`.

## manifest.json schema

```json
{
  "name": "rada-v1",
  "teacher_model_id": "qwen2.5-7b",
  "created_at": "2026-06-07",
  "row_count": 1200,
  "schema_version": "feedback_record_v1",
  "source": "colab_distill_teacher"
}
```

## Train from distilled corpus

```bash
python scripts/reflection_train.py \
  --backend stub \
  --model-id qwen2.5-3b \
  --data-source distilled \
  --distilled-name rada-v1 \
  --output-run-id distill-001
```

## Related

- [docs/training.md](../../docs/training.md) — distillation rationale and workflow
- [notebooks/distill_teacher_colab.ipynb](../../notebooks/distill_teacher_colab.ipynb)
