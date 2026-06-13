"""Append-only audit event storage."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime
from pathlib import Path

from rada.audit.schemas import AuditEvent, AuditEventType


class AuditStore:
    def __init__(self, db_path: str = "./rada_audit.db") -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def ensure_ready(self) -> None:
        def _run() -> None:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS audit_events (
                        event_id TEXT PRIMARY KEY,
                        decision_id TEXT,
                        event_type TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        payload_before TEXT,
                        payload_after TEXT,
                        metadata TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
                    BEFORE DELETE ON audit_events
                    BEGIN
                        SELECT RAISE(ABORT, 'audit_events is append-only');
                    END
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_audit_events_decision_id "
                    "ON audit_events(decision_id)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp "
                    "ON audit_events(timestamp)"
                )
                conn.commit()

        await asyncio.to_thread(_run)

    async def append(self, event: AuditEvent) -> None:
        await self.ensure_ready()

        def _run() -> None:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO audit_events
                    (
                        event_id,
                        decision_id,
                        event_type,
                        timestamp,
                        payload_before,
                        payload_after,
                        metadata
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event.event_id,
                        event.decision_id,
                        event.event_type.value,
                        event.timestamp.isoformat(),
                        json.dumps(event.payload_before) if event.payload_before else None,
                        json.dumps(event.payload_after) if event.payload_after else None,
                        json.dumps(event.metadata),
                    ),
                )
                conn.commit()

        await asyncio.to_thread(_run)

    async def list_for_decision(self, decision_id: str) -> list[AuditEvent]:
        await self.ensure_ready()

        def _run() -> list[AuditEvent]:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    "SELECT event_id, decision_id, event_type, timestamp, "
                    "payload_before, payload_after, metadata "
                    "FROM audit_events WHERE decision_id = ? ORDER BY timestamp",
                    (decision_id,),
                ).fetchall()
            events: list[AuditEvent] = []
            for row in rows:
                events.append(
                    AuditEvent(
                        event_id=row[0],
                        decision_id=row[1],
                        event_type=AuditEventType(row[2]),
                        timestamp=datetime.fromisoformat(row[3]),
                        payload_before=json.loads(row[4]) if row[4] else None,
                        payload_after=json.loads(row[5]) if row[5] else None,
                        metadata=json.loads(row[6]),
                    )
                )
            return events

        return await asyncio.to_thread(_run)

    async def export_range(
        self,
        from_ts: datetime | None,
        to_ts: datetime | None,
    ) -> list[AuditEvent]:
        await self.ensure_ready()

        def _run() -> list[AuditEvent]:
            query = (
                "SELECT event_id, decision_id, event_type, timestamp, "
                "payload_before, payload_after, metadata FROM audit_events"
            )
            params: list[str] = []
            clauses: list[str] = []
            if from_ts:
                clauses.append("timestamp >= ?")
                params.append(from_ts.isoformat())
            if to_ts:
                clauses.append("timestamp <= ?")
                params.append(to_ts.isoformat())
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            query += " ORDER BY timestamp"
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(query, params).fetchall()
            return [
                AuditEvent(
                    event_id=row[0],
                    decision_id=row[1],
                    event_type=AuditEventType(row[2]),
                    timestamp=datetime.fromisoformat(row[3]),
                    payload_before=json.loads(row[4]) if row[4] else None,
                    payload_after=json.loads(row[5]) if row[5] else None,
                    metadata=json.loads(row[6]),
                )
                for row in rows
            ]

        return await asyncio.to_thread(_run)
