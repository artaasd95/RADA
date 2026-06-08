"""Storage adapters for RADA decisions."""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path

from rada.data.query import filter_decisions
from rada.interfaces import BaseDataStore
from rada.schemas import Decision


def _sqlite_path_from_url(db_url: str) -> str:
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "", 1)
    return db_url


class InMemoryDecisionStore(BaseDataStore):
    """Simple in-memory store for tests and local mock flows."""

    def __init__(self) -> None:
        self._items: dict[str, Decision] = {}

    async def save_decision(self, decision: Decision) -> None:
        if decision.decision_id in self._items:
            raise ValueError("decision_id must be immutable and unique")
        self._items[decision.decision_id] = decision

    async def get_decision(self, decision_id: str) -> Decision | None:
        return self._items.get(decision_id)

    async def list_decisions(
        self,
        *,
        since: datetime | None = None,
        limit: int | None = None,
        policy_ids: list[str] | None = None,
    ) -> list[Decision]:
        return filter_decisions(
            list(self._items.values()),
            since=since,
            limit=limit,
            policy_ids=policy_ids,
        )


class SQLiteDecisionStore(BaseDataStore):
    """SQLite fallback store used for CI/local deterministic runs."""

    def __init__(self, db_url: str = "sqlite:///./rada.db") -> None:
        self._db_path = _sqlite_path_from_url(db_url)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

    async def _execute(self, query: str, params: tuple[object, ...] = ()) -> None:
        def _run() -> None:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(query, params)
                conn.commit()

        await asyncio.to_thread(_run)

    async def _fetchone(self, query: str, params: tuple[object, ...] = ()) -> tuple[str] | None:
        def _run() -> tuple[str] | None:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(query, params).fetchone()
                return row

        return await asyncio.to_thread(_run)

    async def _fetchall(self, query: str, params: tuple[object, ...] = ()) -> list[tuple[str]]:
        def _run() -> list[tuple[str]]:
            with sqlite3.connect(self._db_path) as conn:
                return list(conn.execute(query, params).fetchall())

        return await asyncio.to_thread(_run)

    async def ensure_ready(self) -> None:
        await self._execute(
            """
            CREATE TABLE IF NOT EXISTS decisions (
                decision_id TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            )
            """
        )

    async def save_decision(self, decision: Decision) -> None:
        await self.ensure_ready()

        try:
            await self._execute(
                "INSERT INTO decisions (decision_id, payload) VALUES (?, ?)",
                (decision.decision_id, decision.model_dump_json()),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("decision_id must be immutable and unique") from exc

    async def get_decision(self, decision_id: str) -> Decision | None:
        await self.ensure_ready()
        row = await self._fetchone(
            "SELECT payload FROM decisions WHERE decision_id = ?",
            (decision_id,),
        )
        if row is None:
            return None
        return Decision.model_validate_json(row[0])

    async def list_decisions(
        self,
        *,
        since: datetime | None = None,
        limit: int | None = None,
        policy_ids: list[str] | None = None,
    ) -> list[Decision]:
        await self.ensure_ready()
        rows = await self._fetchall("SELECT payload FROM decisions")
        decisions = [Decision.model_validate_json(row[0]) for row in rows]
        return filter_decisions(decisions, since=since, limit=limit, policy_ids=policy_ids)
