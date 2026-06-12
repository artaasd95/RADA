# Immutable audit trail

Append-only audit events for every pipeline step.

## API

All audit endpoints require `X-API-Key` when `RADA_API_KEY` is set (required in production).

- `GET /audit/decision/{id}` — events for one decision
- `GET /audit/export?from=&to=&limit=` — NDJSON export (default limit 1000, max 10000)

## CLI

```bash
python scripts/export_audit.py --output audit.ndjson
python scripts/export_audit.py --db ./rada_audit.db --from 2026-06-01T00:00:00Z --limit 5000
```

Audit store rejects DELETE operations; events are immutable.
