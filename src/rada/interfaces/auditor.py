"""Auditor interface contract."""

from __future__ import annotations

from abc import ABC, abstractmethod

from rada.schemas import Decision, DecisionTrace


class BaseAuditor(ABC):
    """Scores faithfulness or consistency of decisions."""

    @abstractmethod
    async def audit(self, decision: Decision) -> DecisionTrace:
        """Return trace enriched with audit metadata."""
