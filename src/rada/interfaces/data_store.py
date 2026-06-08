"""Persistence interface contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from rada.schemas import Decision


class BaseDataStore(ABC):
    """Persists and retrieves decisions."""

    @abstractmethod
    async def save_decision(self, decision: Decision) -> None:
        """Persist one decision artifact."""

    @abstractmethod
    async def get_decision(self, decision_id: str) -> Decision | None:
        """Fetch one decision artifact by immutable identifier."""

    async def list_decisions(
        self,
        *,
        since: datetime | None = None,
        limit: int | None = None,
        policy_ids: list[str] | None = None,
    ) -> list[Decision]:
        """List decisions for batch export; optional filters by time and policy."""
        raise NotImplementedError(f"{type(self).__name__} does not support list_decisions")
