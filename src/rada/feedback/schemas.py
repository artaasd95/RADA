"""Human feedback schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class FeedbackAction(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    FLAG = "FLAG"
    ANNOTATE = "ANNOTATE"


class HumanFeedbackSubmit(BaseModel):
    """Client-submitted feedback payload (server assigns id/timestamp)."""

    decision_id: str = Field(min_length=1, max_length=128)
    action: FeedbackAction
    note: str = Field(default="", max_length=4000)
    reviewer: str = Field(default="operator", min_length=1, max_length=128)

    @field_validator("decision_id", "reviewer")
    @classmethod
    def strip_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped


class HumanFeedback(BaseModel):
    feedback_id: str
    decision_id: str
    action: FeedbackAction
    note: str = ""
    timestamp: datetime
    reviewer: str = "operator"
