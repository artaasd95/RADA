# Production runbook

Operator guide for RADA v1.0 — no source reading required.

## Deploy

```bash
cp env.example.prod .env
docker compose -f docker-compose.prod.yml up -d --build
./scripts/deploy_check.sh
```

Expected: all services healthy within ~2 minutes.

## Verify decision path

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{"symbol":"BTCUSD","price":60000,"volume":1.0,"timestamp":"2026-06-01T12:00:00Z"}'
```

Copy `decision_id` from response:

```bash
curl http://localhost:8000/audit/decision/<decision_id>
```

## Streamlit review queue

```bash
pip install streamlit httpx
export RADA_API_URL=http://localhost:8000
streamlit run apps/streamlit/dashboard.py
```

Flagged decisions (CVaR breach, low confidence) appear in the Review Queue tab.

## Batch export

```bash
python scripts/export_reflection.py --from-db --output-dir ./tmp/export
```

## Rollback

```bash
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```

Data persists in `rada_app_data` and `rada_pg_data` volumes unless removed with `-v`.

## Incident recovery

| Symptom | Action |
|---------|--------|
| `/health` fails | `docker compose -f docker-compose.prod.yml restart rada` |
| DB connection errors | Check `postgres` health; verify `RADA_POSTGRES_PASSWORD` |
| High latency | Check `rada_loop_errors_total` in `/metrics`; scale resources |
| Audit gap | Query `GET /audit/export?from=&to=` for NDJSON replay |

## CI enablement

GitHub Actions workflow at `.github/workflows/ci.yml`:

- `ruff check .`
- `pytest tests/unit` and `pytest tests/integration -m integration`
- `docker build -t rada:ci .` (no push)

Enable on your fork by pushing to `main`; branch protection can require the `test` and `image` jobs.

## Related

- [calc.md](./calc.md) — numerical verification contract
- [architecture.md](./architecture.md) — system overview
