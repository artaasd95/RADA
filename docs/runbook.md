# RADA Operator Runbook

Manual deploy and recovery procedures for environments that **must not depend solely on GitHub Actions**.

During MVP, production deploys are operator-driven: copy artifacts, configure env, run `docker compose`, verify health, and retain rollback paths without CI.

## Policy

- **Production must not depend solely on GitHub Actions.** CI samples live under `samples/github-actions/` and are opt-in copies; they are not required for deploy or recovery.
- Keep a tagged release artifact (container image or git tag + env file) for every production deploy.
- Document every manual deploy in your change log (who, when, image/tag, rollback target).

## Prerequisites

- Docker Engine 24+ and Docker Compose v2
- Python 3.11+ (for local smoke without containers)
- Access to host secrets store (not committed to git)

## Environment variables

Copy `.env.example` to `.env` and adjust for the target environment.

| Variable | Purpose | Default (dev) |
|----------|---------|---------------|
| `RADA_ENV` | Runtime profile (`dev`, `staging`, `prod`) | `dev` |
| `RADA_LOG_LEVEL` | Log verbosity | `INFO` |
| `RADA_EVENT_BUS_MODE` | Event bus backend: `inmemory`, `redis`, `kafka`, `zeromq` | `inmemory` |
| `RADA_REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `RADA_DATABASE_URL` | Postgres/Timescale URL (required when `RADA_DATA_STORE_MODE=timescale`) | _(unset — set explicitly)_ |
| `RADA_SQLITE_URL` | SQLite fallback for local/CI | `sqlite:///./rada.db` |
| `RADA_API_KEY` | API key for `/ingest`, `/audit/*`, `/feedback/*` | _(empty in dev — optional)_ |
| `RADA_KAFKA_BOOTSTRAP` | Kafka brokers (when overlay enabled) | `localhost:9092` |
| `RADA_ZMQ_ENDPOINT` | ZeroMQ bind/connect endpoint | `tcp://127.0.0.1:5555` |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Postgres container bootstrap | `rada` |

Reference config: `configs/dev.yaml`.

## Docker Compose deploy

### Base stack (Redis + Postgres)

```bash
docker compose up -d
docker compose ps
curl -sf http://localhost:8000/health   # after app is started
```

Bring the app up locally (example):

```bash
pip install -e ".[dev]"
uvicorn rada.main:app --host 0.0.0.0 --port 8000
```

### Data overlay (optional Kafka / ZeroMQ / Timescale)

```bash
docker compose -f docker-compose.yml -f docker-compose.data.yml up -d
```

Set `RADA_EVENT_BUS_MODE=kafka` or `zeromq` when using the overlay. See `docker-compose.data.yml` for service ports.

### Verify

1. `docker compose ps` — all services `healthy` or `running`
2. `GET /health` returns `{"status":"ok"}`
3. `POST /bootstrap-demo` returns a `decision_id` (smoke)
4. Redis: `redis-cli ping` → `PONG`
5. Postgres: `pg_isready -U rada -d rada`

## Backup

### Postgres

```bash
# One-off dump (adjust host/credentials)
docker compose exec postgres pg_dump -U rada -d rada -Fc -f /tmp/rada_backup.dump
docker compose cp postgres:/tmp/rada_backup.dump ./backups/rada_$(date +%Y%m%d_%H%M).dump
```

Schedule daily dumps off-host. Retain at least 7 daily + 4 weekly backups.

### Redis

Redis holds ephemeral event-bus queues in MVP. **Do not treat Redis as source of truth** for decisions; Postgres/SQLite decision store is authoritative.

If you must snapshot Redis for debugging:

```bash
docker compose exec redis redis-cli SAVE
docker compose cp redis:/data/dump.rdb ./backups/redis_$(date +%Y%m%d_%H%M).rdb
```

### Application state

- Tag the git commit or image digest deployed.
- Archive the `.env` used (secrets vault copy, not git).

## Rollback

1. **Stop traffic** to the bad revision (load balancer or scale app to 0).
2. **Record incident** start time and symptoms.
3. **Redeploy previous artifact:**
   - Container: `docker pull <registry>/rada:<previous-tag>` and restart service.
   - Git: checkout previous tag, rebuild/restart with saved `.env`.
4. **Database:** if schema migrated forward, restore from pre-deploy dump or run documented down migration. MVP schema is minimal; restoring Postgres dump is the primary path.
5. **Verify** `/health`, bootstrap smoke, and a sample decision read.
6. **Resume traffic** and monitor (see [monitoring.md](./monitoring.md)).

Never rollback only the app while leaving incompatible DB state unless you have verified schema compatibility.

## Incident checklist

### Redis failure

| Symptom | Checks | Recovery |
|---------|--------|----------|
| App cannot enqueue/dequeue | `redis-cli ping`, container logs, `RADA_REDIS_URL` | Restart `redis` service; if data loss acceptable, flush and restart app with `RADA_EVENT_BUS_MODE=inmemory` temporarily |
| Intermittent timeouts | Memory pressure, persistence lag | Increase memory limit; restart Redis; reduce queue depth |

### Postgres failure

| Symptom | Checks | Recovery |
|---------|--------|----------|
| Decisions not persisting | `pg_isready`, app logs, disk space | Restart `postgres`; restore from latest dump if corrupted |
| Connection refused | Wrong URL, port conflict | Fix `RADA_DATABASE_URL`; ensure compose network |
| Slow queries | Connections, disk | Restart; scale disk; fall back to SQLite only in **non-prod** emergencies |

### Application failure

| Symptom | Checks | Recovery |
|---------|--------|----------|
| `/health` not OK | Process down, port bind | Restart uvicorn/container; check logs |
| 500 on `/bootstrap-demo` | Store/bus misconfig | Verify env vars; switch to inmemory bus + SQLite for isolation test |
| Crash loop | Import errors, bad config | Roll back to previous image/tag; diff `.env` |

### Post-incident

- Capture logs and metrics snapshot (see [monitoring.md](./monitoring.md)).
- Update this runbook if a step was missing.
- File a decision-log entry in [decisions.md](./decisions.md) when policy or architecture changes.

## Related docs

- [monitoring.md](./monitoring.md) — metrics, logs, alerts
- [decisions.md](./decisions.md) — architecture decision log
- [../samples/github-actions/README.md](../samples/github-actions/README.md) — optional CI (not required for deploy)
