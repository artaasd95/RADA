# Data platform

How RADA ingests, normalizes, stores, and exports runtime data for **usage** (hot path) and **reflection** (batch, off hot path). RADA does not own ML train/eval splits — it owns event normalization, lineage, the action DB, and feedback export to training repos.

## Scope

| In scope | Out of scope |
|----------|--------------|
| Runtime ingest (`usage` mode) | Train/eval splits |
| Event normalization to Pydantic schemas | Engine label computation (raft-lm) |
| Hot + warm storage tiers | Scenario path generation (scenario-reasoner-lm) |
| Lineage and data quality hooks | Feature engineering for ML |
| Feedback export (`export` mode) | On-hot-path training loops |

## Mental model

```text
[stream | file replay]
    → normalize(MarketEvent)
    → persist(hot → warm tier)
    → [async] reasoner feedback check  → FeedbackRecord
    → [batch] export(reflection)
```

RADA trains decisions via reflection export — not via inline preprocessing on the hot path.

## Modes

| Mode | Hot path? | Config | Runner |
|------|-----------|--------|--------|
| `usage` | Yes | `configs/data/usage.yaml` | `UsagePipelineRunner` |
| `export` | No | `configs/data/export.yaml` | `ExportPipelineRunner` |

## Record cards

Runtime contracts live in `src/rada/schemas.py`. Export cards live in `src/rada/data/cards/`:

- **DecisionExportRow** — batch reflection / training export unit
- **FeedbackRecord** — shared cross-repo feedback contract

## Pipeline layout

```text
src/rada/data/pipeline/
  config.py      # YAML loader
  runner.py      # usage | export stage runners
```

Batch export CLI: `scripts/export_reflection.py`

## Feedback pipeline

```text
Reasoner (async) → FeedbackRecord → feedback/outgoing/*.jsonl
Auditor (async)  → DecisionExportRow → exports/reflection/*.jsonl
reflection_loop  → policy checkpoint (S3-03)
```

## Related

- [architecture-overview.md](./architecture-overview.md)
- [decisions.md](./decisions.md)
- Source design note: `Data-Platform.md` (vault copy target)
