"""Audit event schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    DECISION = "DECISION"
    CALC = "CALC"
    LLM_CALL = "LLM_CALL"
    RISK_GATE = "RISK_GATE"
    HUMAN_FEEDBACK = "HUMAN_FEEDBACK"
    POLICY_UPDATE = "POLICY_UPDATE"


class AuditEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    decision_id: str | None = None
    event_type: AuditEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    payload_before: dict[str, Any] | None = None
    payload_after: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
