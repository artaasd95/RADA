"""Fire-and-forget audit writer for pipeline stages."""

from __future__ import annotations

import asyncio
from typing import Any

from rada.audit.schemas import AuditEvent, AuditEventType
from rada.audit.store import AuditStore
from rada.observability.metrics import get_metrics


class AuditWriter:
    def __init__(self, store: AuditStore | None = None, queue_maxsize: int = 512) -> None:
        self._store = store or AuditStore()
        self._queue: asyncio.Queue[AuditEvent | None] = asyncio.Queue(maxsize=queue_maxsize)
        self._task: asyncio.Task[None] | None = None

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
            get_metrics().inc("rada_loop_errors_total")

    async def _consumer(self) -> None:
        while True:
            event = await self._queue.get()
            if event is None:
                break
            await self._store.append(event)
