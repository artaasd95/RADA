"""Risk optimizer interface contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from rada.schemas import DecisionTrace, ProposedAction


class BaseRiskOptimizer(ABC):
    """Applies risk limits to proposed actions."""

    @abstractmethod
    async def optimize(self, action: ProposedAction, trace: DecisionTrace) -> ProposedAction:
        """Return a risk-adjusted action and update trace metadata if needed."""
