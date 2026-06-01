---
type: reference
project: rada
status: active
priority: p1
phase: foundation
area: data
tags:
  - project/rada
  - data-platform
  - usage
created: 2026-05-31
updated: 2026-05-31
---
# Data platform — RADA

**Copy target (code repo):** `docs/data-platform.md`

**Purpose:** Define how RADA ingests, normalizes, stores, and **exports** runtime data for usage (hot path) and reflection (batch, off hot path). RADA does **not** own ML train/eval splits — it owns event normalization, lineage, action DB, and feedback export to training repos.

**Portfolio context:** [[Knowledge/Data-Platform-Design]]

---

## Scope

| In scope | Out of scope |
|----------|--------------|
| Runtime ingest (`usage` mode) | Train/eval splits |
| Event normalization to Pydantic schemas | Engine label computation (raft-lm) |
| Hot + warm storage tiers | Scenario path generation (scenario-reasoner-lm) |
| Lineage and data quality hooks | Feature engineering for ML |
| Feedback export (`export` mode) | On-hot-path training loops |

---

## Mental model

```text
[stream | file replay]
    → normalize(MarketEvent)           # validation + lineage
    → persist(hot → warm tier)         # action DB source of truth
    → [async] reasoner feedback check  → FeedbackRecord
    → [batch] export(reflection)       # RayDataLLMAdapter / parquet / jsonl
```

**RADA trains decisions via reflection export — not via inline preprocessing on the hot path.**

---

## Modes

| Mode | Hot path? | Description |
|------|-----------|-------------|
| `usage` | Yes | Live ingest → calc → decision → store |
| `export` | No | Action DB → batch artifacts for reflection / downstream training |

---

## Record cards

### Runtime cards (existing — `src/rada/schemas.py`)

These remain the runtime contract; the data platform wraps them with pipeline config:

| Card | Role |
|------|------|
| `MarketEvent` | Normalized tick/quote from ingest |
| `MetricBundle` | CVaR, VaR, drawdown, survival from calc step |
| `PolicyProfile` | Threshold bands, size scaling |
| `DecisionTrace` | scenario_id, reasoning, faithfulness |
| `ProposedAction` | Direction, sizes, cvar_impact |
| `Decision` | Full decision record + optional outcome |
| `AuditorRecord` | Audit fields + optional raft-lm enrichment |
| `LLMCompletion` | Model response metadata |

### Export cards (new — `src/rada/data/cards/`)

**`DecisionExportRow`** — batch reflection / training export unit:

```yaml
fields:
  export_id: str
  decision_id: str
  timestamp: iso8601
  trigger_event: MarketEvent          # serialized
  metrics: MetricBundle
  trace: DecisionTrace
  action: ProposedAction
  outcome: dict | null                # P&L, fill status, etc.
  policy_id: str
  auditor_enrichment: dict | null     # optional RaftAuditor scores
metadata:
  export_batch_id: str
  lineage:
    ingest_source: str
    checksum: str | null
```

**`FeedbackRecord`** — shared cross-repo contract:

```yaml
fields:
  feedback_id: str
  timestamp: iso8601
  source: reasoner | auditor | human | tailwarp_stress
  target_project: raft-lm | scenario-reasoner-lm | rada
  target_card: PreferencePair | EngineLabelRow | ScenarioPathRow
  label_schema: outcome_match | chosen_rejected | engine_score
  payload: dict
  provenance:
    decision_id: str
    run_id: str | null
    scenario_id: str | null
labels:
  schema: outcome_match
  expected: str | dict
  actual: str | dict
  delta: float | null
  score: float                        # normalized feedback strength
```

---

## Datasource types

| Type | Usage mode | Export mode |
|------|------------|-------------|
| `stream` | Kafka / ZeroMQ / Redis via `bus.py` | — |
| `file` | CSV/JSONL replay for dev | Parquet/JSONL export sink |
| `db` | TimescaleDB hot/warm tier | Action DB read for export |
| `vector_store` | Optional reasoner context (future) | — |
| `databricks` | Enterprise warm tier (future) | Batch export sink (future) |

---

## Pipeline configuration

### `configs/data/usage.yaml`

```yaml
version: 1
mode: usage

datasources:
  - id: live_stream
    type: stream
    uri: ${RADA_BUS_BACKEND:-redis}
    contract: MarketEvent
    options:
      topic: market_events
      backend: redis                 # redis | kafka | zeromq

preprocessing:
  stages:
    - normalize: { contract: MarketEvent }
    - lineage: { via: quality_hooks }   # src/rada/data/quality.py

sinks:
  hot:
    type: db
    contract: Decision
    options:
      store: timescale               # or postgres for MVP
  warm:
    type: db
    options:
      tables: [market_events, decision_traces]
```

### `configs/data/export.yaml`

```yaml
version: 1
mode: export

datasources:
  - id: action_db
    type: db
    uri: ${RADA_DATABASE_URL}
    contract: Decision
    options:
      since: "2026-01-01T00:00:00Z"
      policy_ids: [balanced, conservative]

preprocessing:
  stages:
    - normalize: { contract: DecisionExportRow }
    - enrich: { via: raft_auditor, optional: true }
    - filter: { require_outcome: false }

sinks:
  reflection:
    type: file
    uri: exports/reflection/{batch_id}.jsonl
    format: jsonl
  feedback:
    type: file
    uri: feedback/outgoing/{batch_id}.jsonl
    contract: FeedbackRecord
```

---

## Target code layout

```text
configs/data/
  usage.yaml
  export.yaml
docs/
  data-platform.md                  ← copy of this document
src/rada/data/
  pipeline/
    config.py
    runner.py
    stages/
      normalize.py
      lineage.py
      export.py
      feedback_emit.py
  cards/
    decision_export.py
    feedback_record.py
  sources/
    stream_source.py                # wraps bus.py
    file_replay_source.py
    db_source.py
scripts/
  export_reflection.py              # batch export CLI
tests/
  unit/test_export_cards.py
  integration/test_usage_pipeline.py
  integration/test_export_pipeline.py
```

---

## Feedback pipeline

```text
Reasoner pipeline (async)
  compare reasoner output vs stored Decision + outcome
        │
        ▼
  FeedbackRecord (label_schema: outcome_match)
        │
        ├── feedback/outgoing/*.jsonl  → raft-lm / scenario-reasoner-lm
        └── local reflection_loop consumption

In-system auditor (rada-audit)
  immutable AuditorRecord + optional RaftAuditor enrichment
        │
        ▼
  DecisionExportRow with auditor_enrichment
        │
        ▼
  export batch → downstream training repos
```

**Contract:** Feedback JSONL must validate against shared `FeedbackRecord` schema documented in [[Knowledge/Data-Platform-Design]].

---

## Integration with RADA architecture

| Component | Role |
|-----------|------|
| `rada-ingest` | Stream/file datasource → normalize stage |
| `rada-store` | Hot/warm sinks |
| `rada-audit` | Enrichment on export; FeedbackRecord source |
| `rada-reasoner` | Outcome_match feedback generation |
| `reflection_loop` | Consumes export batches (S3-03) |
| `RayDataLLMAdapter` | Batch scoring of export JSONL |

---

## Relationship to S6 data foundation

| Existing S6 work | Data platform extension |
|------------------|-------------------------|
| S6-01 `bus.py` | `stream` datasource adapter |
| S6-02 TimescaleDB | `db` sink for warm tier |
| S6-03 `quality.py` | `lineage` preprocessing stage |
| **S6-05** | Publish `docs/data-platform.md` |
| **S6-06** | Pipeline config loader + usage/export runners |
| **S6-07** | FeedbackRecord card + export validation |
| **S6-08** | `export_reflection.py` batch CLI + integration test |

---

## Sprint tasks

Seeds appended to [issues/sprint-s6.yaml](issues/sprint-s6.yaml): S6-05 … S6-08

---

## Related

- Architecture: [[Architecture]]
- S6 data foundation: [issues/sprint-s6.yaml](issues/sprint-s6.yaml)
- raft-lm consumer: [[Projects/raft-lm/Data-Platform]]
- scenario-reasoner consumer: [[Projects/scenario-reasoner-lm/Data-Platform]]
