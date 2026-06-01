# Timescale migrations

This folder contains Alembic migrations for the R6 time-series schema.

## Apply migrations

1. Start Postgres/Timescale containers:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.data.yml up -d
   ```

2. Set the database URL:

   ```bash
   export RADA_DATABASE_URL=postgresql://rada:rada@localhost:5433/rada
   ```

3. Run upgrade:

   ```bash
   alembic upgrade head
   ```

## Rollback

```bash
alembic downgrade -1
```