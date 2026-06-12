"""Fire-and-forget audit writer for pipeline stages."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from rada.audit.schemas import AuditEvent, AuditEventType
from rada.audit.store import AuditStore
from rada.observability.metrics import get_metrics

logger = logging.getLogger(__name__)


class AuditWriter:
    def __init__(
        self,
        store: AuditStore | None = None,
        queue_maxsize: int = 512,
        *,
        enqueue_timeout_sec: float = 5.0,
    ) -> None:
        self._store = store or AuditStore()
        self._queue: asyncio.Queue[AuditEvent | None] = asyncio.Queue(maxsize=queue_maxsize)
        self._task: asyncio.Task[None] | None = None
        self._enqueue_timeout_sec = enqueue_timeout_sec

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._consumer())

    async def stop(self) -> None:
        if self._task is not None:
            await self._queue.put(None)
            await self._task
            self._task = None

    def emit(
        self,
        event_type: AuditEventType,
        *,
        decision_id: str | None = None,
        payload_before: dict[str, Any] | None = None,
        payload_after: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        event = AuditEvent(
            event_type=event_type,
            decision_id=decision_id,
            payload_before=payload_before,
            payload_after=payload_after,
            metadata=metadata or {},
        )
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._enqueue_with_timeout(event))
            except RuntimeError:
                logger.error("audit queue full and no running loop; dropping event %s", event_type)
                get_metrics().inc("rada_audit_queue_drops_total")

    async def _enqueue_with_timeout(self, event: AuditEvent) -> None:
        try:
            await asyncio.wait_for(
                self._queue.put(event),
                timeout=self._enqueue_timeout_sec,
            )
        except TimeoutError:
            logger.error(
                "audit queue full after %.1fs; dropping %s for decision_id=%s",
                self._enqueue_timeout_sec,
                event.event_type,
                event.decision_id,
            )
            get_metrics().inc("rada_audit_queue_drops_total")

    async def _consumer(self) -> None:
        while True:
            event = await self._queue.get()
            if event is None:
                break
            try:
                await self._store.append(event)
            except Exception:
                logger.exception(
                    "audit append failed for %s decision_id=%s",
                    event.event_type,
                    event.decision_id,
                )
                get_metrics().inc("rada_loop_errors_total")
