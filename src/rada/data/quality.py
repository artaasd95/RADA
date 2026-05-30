"""Data quality and ingest lineage hooks."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from rada.schemas import MarketEvent
from rada.utils.metrics import record_event_ingested, record_quality_rejection


class IngestLineage(BaseModel):
    """Lineage metadata attached at ingest time."""

    source: str
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(tz=UTC))
    checksum: str
    event_symbol: str


@dataclass(frozen=True)
class QualityResult:
    accepted: bool
    lineage: IngestLineage | None = None
    reason: str | None = None


def compute_event_checksum(event: MarketEvent) -> str:
    """Stable SHA-256 checksum over normalized event payload."""
    payload = event.model_dump_json()
    return hashlib.sha256(payload.encode()).hexdigest()


def validate_ingest_event(event: MarketEvent, *, source: str) -> QualityResult:
    """Apply MVP quality gates and build lineage metadata."""
    if event.price <= 0:
        record_quality_rejection("non_positive_price")
        return QualityResult(accepted=False, reason="price must be positive")

    if event.volume < 0:
        record_quality_rejection("negative_volume")
        return QualityResult(accepted=False, reason="volume must be non-negative")

    lineage = IngestLineage(
        source=source,
        checksum=compute_event_checksum(event),
        event_symbol=event.symbol,
    )
    record_event_ingested(source=source)
    return QualityResult(accepted=True, lineage=lineage)


async def ingest_with_lineage(
    event: MarketEvent,
    *,
    source: str,
) -> tuple[MarketEvent, IngestLineage]:
    """Validate event and return it with lineage (raises on rejection)."""
    result = validate_ingest_event(event, source=source)
    if not result.accepted or result.lineage is None:
        raise ValueError(result.reason or "ingest rejected")
    return event, result.lineage
