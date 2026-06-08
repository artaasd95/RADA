"""Human feedback API routes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from rada.audit.schemas import AuditEventType
from rada.audit.writer import AuditWriter
from rada.feedback.schemas import HumanFeedback
from rada.feedback.store import FeedbackStore

router = APIRouter(prefix="/feedback", tags=["feedback"])


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
async def submit_feedback(feedback: HumanFeedback, request: Request) -> dict:
    store = _feedback_store(request)
    saved = await store.submit(feedback)
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
