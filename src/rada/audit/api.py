"""Audit query API routes."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from rada.audit.store import AuditStore
from rada.security.auth import require_api_key

router = APIRouter(prefix="/audit", tags=["audit"], dependencies=[Depends(require_api_key)])

_MAX_EXPORT_ROWS = 10_000


def _get_store(request: Request) -> AuditStore:
    store = getattr(request.app.state, "audit_store", None)
    if store is None:
        store = AuditStore()
        request.app.state.audit_store = store
    return store


def _parse_iso_timestamp(value: str, *, field: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"invalid {field} timestamp: {value}",
        ) from exc


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
    limit: int = Query(default=1000, ge=1, le=_MAX_EXPORT_ROWS),
) -> StreamingResponse:
    store = _get_store(request)
    from_ts = _parse_iso_timestamp(from_, field="from") if from_ else None
    to_ts = _parse_iso_timestamp(to, field="to") if to else None
    events = await store.export_range(from_ts, to_ts)
    events = events[:limit]

    def _stream():
        for event in events:
            yield json.dumps(event.model_dump(mode="json")) + "\n"

    return StreamingResponse(_stream(), media_type="application/x-ndjson")
