"""Human feedback schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class FeedbackAction(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    FLAG = "FLAG"
    ANNOTATE = "ANNOTATE"


class HumanFeedback(BaseModel):
    feedback_id: str = Field(default_factory=lambda: str(uuid4()))
    decision_id: str
    action: FeedbackAction
    note: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    reviewer: str = "operator"
