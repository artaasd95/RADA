"""Audit query API routes."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from rada.audit.store import AuditStore

router = APIRouter(prefix="/audit", tags=["audit"])


def _get_store(request: Request) -> AuditStore:
    store = getattr(request.app.state, "audit_store", None)
    if store is None:
        store = AuditStore()
        request.app.state.audit_store = store
    return store


@router.get("/decision/{decision_id}")
async def get_decision_audit(decision_id: str, request: Request) -> dict:
    store = _get_store(request)
    events = await store.list_for_decision(decision_id)
    return {
        "decision_id": decision_id,
        "events": [e.model_dump(mode="json") for e in events],
    }


@router.get("/export")
async def export_audit(
    request: Request,
    from_: str | None = None,
    to: str | None = None,
) -> StreamingResponse:
    store = _get_store(request)
    from_ts = datetime.fromisoformat(from_.replace("Z", "+00:00")) if from_ else None
    to_ts = datetime.fromisoformat(to.replace("Z", "+00:00")) if to else None
    events = await store.export_range(from_ts, to_ts)

    def _stream():
        for event in events:
            yield json.dumps(event.model_dump(mode="json")) + "\n"

    return StreamingResponse(_stream(), media_type="application/x-ndjson")
