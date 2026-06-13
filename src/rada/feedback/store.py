"""Append-only human feedback storage."""

from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path

from rada.feedback.schemas import FeedbackAction, HumanFeedback


class FeedbackDuplicateError(Exception):
    """Raised when feedback_id already exists."""


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
                try:
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
                except sqlite3.IntegrityError as exc:
                    raise FeedbackDuplicateError(
                        f"feedback_id already exists: {feedback.feedback_id}"
                    ) from exc

        await asyncio.to_thread(_run)
        return feedback

    async def list_pending(self, *, limit: int = 100) -> list[HumanFeedback]:
        await self.ensure_ready()

        def _run() -> list[HumanFeedback]:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT feedback_id, decision_id, action, note, timestamp, reviewer
                    FROM human_feedback
                    WHERE action = ? AND status = 'submitted'
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (FeedbackAction.FLAG.value, limit),
                ).fetchall()
            seen: set[str] = set()
            items: list[HumanFeedback] = []
            for row in rows:
                decision_id = row[1]
                if decision_id in seen:
                    continue
                seen.add(decision_id)
                items.append(
                    HumanFeedback(
                        feedback_id=row[0],
                        decision_id=decision_id,
                        action=FeedbackAction(row[2]),
                        note=row[3],
                        timestamp=datetime.fromisoformat(row[4]),
                        reviewer=row[5],
                    )
                )
            return items

        return await asyncio.to_thread(_run)
