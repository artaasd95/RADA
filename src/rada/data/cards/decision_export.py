"""DecisionExportRow — batch reflection / training export unit."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from rada.schemas import Decision, DecisionTrace, MarketEvent, ProposedAction

UtcDateTime = Annotated[
    datetime,
    Field(description="Timezone-aware datetime normalized to UTC"),
]


class ExportLineage(BaseModel):
    ingest_source: str = "unknown"
    checksum: str | None = None


class ExportMetadata(BaseModel):
    export_batch_id: str
    lineage: ExportLineage = Field(default_factory=ExportLineage)


class DecisionExportRow(BaseModel):
    export_id: str = Field(default_factory=lambda: str(uuid4()))
    decision_id: str
    timestamp: UtcDateTime
    trigger_event: MarketEvent
    trace: DecisionTrace
    action: ProposedAction
    outcome: dict[str, Any] | None = None
    policy_id: str = "balanced"
    auditor_enrichment: dict[str, Any] | None = None
    metadata: ExportMetadata

    @field_validator("timestamp")
    @classmethod
    def normalize_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(UTC)

    @classmethod
    def from_decision(
        cls,
        decision: Decision,
        *,
        batch_id: str,
        ingest_source: str = "action_db",
        auditor_enrichment: dict[str, Any] | None = None,
    ) -> DecisionExportRow:
        return cls(
            decision_id=decision.decision_id,
            timestamp=decision.timestamp,
            trigger_event=decision.market_event,
            trace=decision.trace,
            action=decision.proposed_action,
            auditor_enrichment=auditor_enrichment,
            metadata=ExportMetadata(
                export_batch_id=batch_id,
                lineage=ExportLineage(ingest_source=ingest_source),
            ),
        )
