"""Append-only human feedback storage."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path

from rada.feedback.schemas import FeedbackAction, HumanFeedback


class FeedbackStore:
    def __init__(self, db_path: str = "./rada_feedback.db") -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async def ensure_ready(self) -> None:
        def _run() -> None:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS human_feedback (
                        feedback_id TEXT PRIMARY KEY,
                        decision_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        note TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        reviewer TEXT NOT NULL,
                        status TEXT NOT NULL DEFAULT 'submitted'
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TRIGGER IF NOT EXISTS human_feedback_no_delete
                    BEFORE DELETE ON human_feedback
                    BEGIN
                        SELECT RAISE(ABORT, 'human_feedback is append-only');
                    END
                    """
                )
                conn.commit()

        await asyncio.to_thread(_run)

    async def submit(self, feedback: HumanFeedback) -> HumanFeedback:
        await self.ensure_ready()

        def _run() -> None:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO human_feedback
                    (feedback_id, decision_id, action, note, timestamp, reviewer, status)
                    VALUES (?, ?, ?, ?, ?, ?, 'submitted')
                    """,
                    (
                        feedback.feedback_id,
                        feedback.decision_id,
                        feedback.action.value,
                        feedback.note,
                        feedback.timestamp.isoformat(),
                        feedback.reviewer,
                    ),
                )
                conn.commit()

        await asyncio.to_thread(_run)
        return feedback

    async def list_pending(self) -> list[HumanFeedback]:
        await self.ensure_ready()

        def _run() -> list[HumanFeedback]:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    "SELECT feedback_id, decision_id, action, note, timestamp, reviewer "
                    "FROM human_feedback WHERE action = ? ORDER BY timestamp DESC",
                    (FeedbackAction.FLAG.value,),
                ).fetchall()
            return [
                HumanFeedback(
                    feedback_id=row[0],
                    decision_id=row[1],
                    action=FeedbackAction(row[2]),
                    note=row[3],
                    timestamp=__import__("datetime").datetime.fromisoformat(row[4]),
                    reviewer=row[5],
                )
                for row in rows
            ]

        return await asyncio.to_thread(_run)
