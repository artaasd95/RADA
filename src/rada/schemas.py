"""Core domain schemas for RADA."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

UtcDateTime = Annotated[
    datetime,
    Field(description="Timezone-aware datetime normalized to UTC"),
]


class ActionDirection(StrEnum):
    """Allowed action directions emitted by the decision pipeline."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class MarketEvent(BaseModel):
    """Normalized market input event consumed by the decision loop."""

    symbol: str
    price: float = Field(gt=0)
    volume: float = Field(ge=0)
    timestamp: UtcDateTime

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(UTC)


class DecisionTrace(BaseModel):
    """Traceability payload for why a decision was made."""

    model_name: str = "bootstrap-stub"
    rationale: str = ""
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    faithfulness_score: float | None = None
    calc_results: list[dict[str, Any]] = Field(default_factory=list)
    verified_context: dict[str, float] = Field(default_factory=dict)
    synthetic_context: dict[str, float] = Field(default_factory=dict)


class ProposedAction(BaseModel):
    """Action candidate emitted by policy/risk modules."""

    direction: ActionDirection = ActionDirection.HOLD
    size: float = Field(default=0, ge=0)
    risk_adjusted_size: float | None = Field(default=None, ge=0)
    cvar_impact: float | None = None


class Decision(BaseModel):
    """Final decision artifact persisted by RADA."""

    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    policy_id: str = "balanced"
    timestamp: UtcDateTime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description=(
            "UTC timestamp for decision creation. Use timezone-aware datetimes only; "
            "naive datetime inputs are rejected."
        ),
    )
    market_event: MarketEvent
    proposed_action: ProposedAction
    trace: DecisionTrace
    outcome: dict[str, Any] | None = None

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(UTC)
