"""Persistence interface contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from rada.schemas import Decision


class BaseDataStore(ABC):
    """Persists and retrieves decisions."""

    @abstractmethod
    async def save_decision(self, decision: Decision) -> None:
        """Persist one decision artifact."""

    @abstractmethod
    async def get_decision(self, decision_id: str) -> Decision | None:
        """Fetch one decision artifact by immutable identifier."""
