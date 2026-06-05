"""FeedbackRecord — shared cross-repo feedback contract."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from rada.schemas import Decision

UtcDateTime = Annotated[
    datetime,
    Field(description="Timezone-aware datetime normalized to UTC"),
]

FeedbackSource = Literal["reasoner", "auditor", "human", "tailwarp_stress"]
TargetProject = Literal["raft-lm", "scenario-reasoner-lm", "rada"]
LabelSchema = Literal["outcome_match", "chosen_rejected", "engine_score"]


class FeedbackProvenance(BaseModel):
    decision_id: str
    run_id: str | None = None
    scenario_id: str | None = None


class FeedbackLabels(BaseModel):
    schema: LabelSchema = "outcome_match"
    expected: str | dict[str, Any] | None = None
    actual: str | dict[str, Any] | None = None
    delta: float | None = None
    score: float = Field(ge=0.0, le=1.0)


class FeedbackRecord(BaseModel):
    feedback_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: UtcDateTime = Field(default_factory=lambda: datetime.now(tz=UTC))
    source: FeedbackSource
    target_project: TargetProject
    target_card: str
    label_schema: LabelSchema
    payload: dict[str, Any] = Field(default_factory=dict)
    provenance: FeedbackProvenance
    labels: FeedbackLabels

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(UTC)

    @classmethod
    def from_decision_stub(
        cls,
        decision: Decision,
        *,
        score: float = 0.9,
        source: FeedbackSource = "auditor",
    ) -> FeedbackRecord:
        return cls(
            source=source,
            target_project="rada",
            target_card="PreferencePair",
            label_schema="outcome_match",
            payload={"symbol": decision.market_event.symbol},
            provenance=FeedbackProvenance(decision_id=decision.decision_id),
            labels=FeedbackLabels(score=score, actual=decision.proposed_action.direction.value),
        )
