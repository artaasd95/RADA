"""Policy interface contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from rada.schemas import DecisionTrace, MarketEvent, ProposedAction


class BasePolicy(ABC):
    """Maps market context + reasoning into a proposed action."""

    @abstractmethod
    async def propose(self, event: MarketEvent, trace: DecisionTrace) -> ProposedAction:
        """Return proposed action before risk optimization."""
