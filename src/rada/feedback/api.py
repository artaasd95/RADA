"""Human feedback API routes."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status

from rada.audit.schemas import AuditEventType
from rada.audit.writer import AuditWriter
from rada.feedback.schemas import HumanFeedback, HumanFeedbackSubmit
from rada.feedback.store import FeedbackDuplicateError, FeedbackStore
from rada.security.auth import require_api_key

router = APIRouter(prefix="/feedback", tags=["feedback"], dependencies=[Depends(require_api_key)])


def _feedback_store(request: Request) -> FeedbackStore:
    store = getattr(request.app.state, "feedback_store", None)
    if store is None:
        store = FeedbackStore()
        request.app.state.feedback_store = store
    return store


def _audit_writer(request: Request) -> AuditWriter:
    writer = getattr(request.app.state, "audit_writer", None)
    if writer is None:
        writer = AuditWriter()
        writer.start()
        request.app.state.audit_writer = writer
    return writer


@router.post("/submit")
async def submit_feedback(payload: HumanFeedbackSubmit, request: Request) -> dict:
    store = _feedback_store(request)
    feedback = HumanFeedback(
        feedback_id=str(uuid4()),
        decision_id=payload.decision_id,
        action=payload.action,
        note=payload.note,
        timestamp=datetime.now(tz=UTC),
        reviewer=payload.reviewer,
    )
    try:
        saved = await store.submit(feedback)
    except FeedbackDuplicateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    _audit_writer(request).emit(
        AuditEventType.HUMAN_FEEDBACK,
        decision_id=saved.decision_id,
        payload_after=saved.model_dump(mode="json"),
    )
    return {"feedback_id": saved.feedback_id, "status": "submitted"}


@router.get("/pending")
async def pending_feedback(request: Request) -> dict:
    store = _feedback_store(request)
    items = await store.list_pending()
    return {"pending": [i.model_dump(mode="json") for i in items]}
