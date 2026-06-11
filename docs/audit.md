# Immutable audit trail

Append-only audit events for every pipeline step.

## API

- `GET /audit/decision/{id}` — events for one decision
- `GET /audit/export` — NDJSON export

## CLI

```bash
python scripts/export_audit.py --output audit.ndjson
```

Audit store rejects DELETE operations; events are immutable.
