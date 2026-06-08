"""TimescaleDB-backed decision store."""

from __future__ import annotations

import json
from datetime import datetime

import asyncpg

from rada.data.query import filter_decisions
from rada.interfaces import BaseDataStore
from rada.schemas import Decision


def _normalize_database_url(database_url: str) -> str:
    """Convert SQLAlchemy-style URL to asyncpg-compatible DSN if needed."""
    return database_url.replace("+asyncpg", "")


class TimescaleDecisionStore(BaseDataStore):
    """Postgres/Timescale decision store with warm-tier time-series tables."""

    def __init__(
        self,
        database_url: str,
        *,
        min_pool_size: int = 1,
        max_pool_size: int = 10,
    ) -> None:
        if min_pool_size < 1:
            raise ValueError("min_pool_size must be >= 1")
        if max_pool_size < min_pool_size:
            raise ValueError("max_pool_size must be >= min_pool_size")

        self._dsn = _normalize_database_url(database_url)
        self._min_pool_size = min_pool_size
        self._max_pool_size = max_pool_size
        self._pool: asyncpg.Pool | None = None

    async def _pool_or_create(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=self._dsn,
                min_size=self._min_pool_size,
                max_size=self._max_pool_size,
            )
        return self._pool

    async def ensure_ready(self) -> None:
        pool = await self._pool_or_create()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decisions (
                    decision_id TEXT PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    payload JSONB NOT NULL
                )
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS market_events (
                    decision_id TEXT PRIMARY KEY
                        REFERENCES decisions(decision_id) ON DELETE CASCADE,
                    ts TIMESTAMPTZ NOT NULL,
                    symbol TEXT NOT NULL,
                    price DOUBLE PRECISION NOT NULL,
                    volume DOUBLE PRECISION NOT NULL
                )
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS decision_traces (
                    decision_id TEXT PRIMARY KEY
                        REFERENCES decisions(decision_id) ON DELETE CASCADE,
                    ts TIMESTAMPTZ NOT NULL,
                    model_name TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    faithfulness_score DOUBLE PRECISION,
                    assumptions JSONB NOT NULL DEFAULT '[]'::jsonb,
                    warnings JSONB NOT NULL DEFAULT '[]'::jsonb
                )
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_market_events_symbol_ts
                ON market_events(symbol, ts DESC)
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_decision_traces_model_ts
                ON decision_traces(model_name, ts DESC)
                """
            )

            has_timescaledb = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb')"
            )
            if has_timescaledb:
                await conn.execute(
                    """
                    SELECT create_hypertable(
                        'market_events',
                        'ts',
                        if_not_exists => TRUE,
                        migrate_data => TRUE
                    )
                    """
                )
                await conn.execute(
                    """
                    SELECT create_hypertable(
                        'decision_traces',
                        'ts',
                        if_not_exists => TRUE,
                        migrate_data => TRUE
                    )
                    """
                )

    async def save_decision(self, decision: Decision) -> None:
        await self.ensure_ready()
        pool = await self._pool_or_create()

        payload = json.loads(decision.model_dump_json())
        async with pool.acquire() as conn:
            async with conn.transaction():
                try:
                    await conn.execute(
                        "INSERT INTO decisions (decision_id, payload) VALUES ($1, $2::jsonb)",
                        decision.decision_id,
                        json.dumps(payload),
                    )
                except asyncpg.UniqueViolationError as exc:
                    raise ValueError("decision_id must be immutable and unique") from exc

                await conn.execute(
                    """
                    INSERT INTO market_events (decision_id, ts, symbol, price, volume)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (decision_id) DO NOTHING
                    """,
                    decision.decision_id,
                    decision.market_event.timestamp,
                    decision.market_event.symbol,
                    decision.market_event.price,
                    decision.market_event.volume,
                )
                await conn.execute(
                    """
                    INSERT INTO decision_traces (
                        decision_id,
                        ts,
                        model_name,
                        rationale,
                        faithfulness_score,
                        assumptions,
                        warnings
                    )
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb)
                    ON CONFLICT (decision_id) DO NOTHING
                    """,
                    decision.decision_id,
                    decision.timestamp,
                    decision.trace.model_name,
                    decision.trace.rationale,
                    decision.trace.faithfulness_score,
                    json.dumps(decision.trace.assumptions),
                    json.dumps(decision.trace.warnings),
                )

    async def get_decision(self, decision_id: str) -> Decision | None:
        await self.ensure_ready()
        pool = await self._pool_or_create()

        async with pool.acquire() as conn:
            payload = await conn.fetchval(
                "SELECT payload::text FROM decisions WHERE decision_id = $1",
                decision_id,
            )
        if payload is None:
            return None
        return Decision.model_validate_json(payload)

    async def list_decisions(
        self,
        *,
        since: datetime | None = None,
        limit: int | None = None,
        policy_ids: list[str] | None = None,
    ) -> list[Decision]:
        await self.ensure_ready()
        pool = await self._pool_or_create()

        query = "SELECT payload::text FROM decisions"
        params: list[object] = []
        if since is not None:
            query += " WHERE created_at >= $1"
            params.append(since)
        query += " ORDER BY created_at DESC"
        if limit is not None and limit > 0:
            query += f" LIMIT ${len(params) + 1}"
            params.append(limit)

        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        decisions = [Decision.model_validate_json(row[0]) for row in rows]
        if policy_ids:
            decisions = filter_decisions(decisions, policy_ids=policy_ids)
        return decisions

    async def close(self) -> None:
        """Gracefully close pool for process shutdown hooks and tests."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None