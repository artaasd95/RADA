# Spike: kdb+ hot tier vs Timescale warm tier

**Status:** Documentation spike only — no production kdb+ deployment.

## Context

RADA currently persists decisions via SQLite (CI/local), Postgres, or Timescale (`TimescaleDecisionStore`). The vault data-platform design describes a **hot** tick path and a **warm** analytics tier.

## Options compared

| Dimension | kdb+ (hot) | Timescale (warm) |
|-----------|------------|------------------|
| Latency | Sub-ms columnar tick queries | Low-ms SQL time-series |
| Ops model | Specialized kdb+ ops / licensing | Postgres ecosystem |
| RADA fit today | No adapter in repo | Shipped (`timescale_store.py`) |
| Reflection export | Would need q→JSONL bridge | SQL → `DecisionExportRow` |
| Team skill | q/kdb expertise required | SQL/Alembic already used |

## Recommendation (spike)

Stay on **Timescale warm tier** for MVP and CI. Revisit kdb+ when:

- Ingest exceeds ~50k events/sec sustained on a single symbol set, **and**
- Sub-10ms rolling window queries block the decision loop on Postgres.

A future `kdb_hot_source` would sit behind `interfaces/data_store.py` as a read-only tick cache; the action DB of record remains SQL-friendly for export batches.

## Prototype sketch (not implemented)

```text
[kdb+ tick table] --async replicate--> [Timescale market_events]
                      Decision persist --> decisions (Timescale)
```

## Related

- [../data-platform.md](../data-platform.md)
- [../decisions.md](../decisions.md) — ADR-007
