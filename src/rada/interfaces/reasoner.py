"""Reasoner interface contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from rada.schemas import DecisionTrace, MarketEvent


class BaseReasoner(ABC):
    """Builds a decision trace from incoming market context."""

    @abstractmethod
    async def reason(self, event: MarketEvent) -> DecisionTrace:
        """Return a trace that explains market interpretation for one event."""
