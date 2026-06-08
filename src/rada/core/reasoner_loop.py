"""Async reasoner loop — proposes action targets without executing trades."""

from __future__ import annotations

from dataclasses import dataclass

from rada.interfaces import BaseReasoner
from rada.schemas import ActionDirection, DecisionTrace, MarketEvent, ProposedAction


@dataclass(slots=True)
class ActionTarget:
    """Candidate action proposed by the reasoner loop."""

    action: ProposedAction
    confidence: float = 1.0
    rationale: str = ""


class ReasonerLoop:
    """Async-only reasoner that emits ActionTarget candidates; never executes trades."""

    def __init__(self, reasoner: BaseReasoner) -> None:
        self._reasoner = reasoner

    async def propose_targets(self, event: MarketEvent) -> tuple[DecisionTrace, list[ActionTarget]]:
        trace = await self._reasoner.reason(event)
        confidence = trace.faithfulness_score if trace.faithfulness_score is not None else 0.5
        propose_from = getattr(self._reasoner, "propose_from_event", None)
        if propose_from is not None:
            action = await propose_from(event)
        else:
            action = ProposedAction(direction=ActionDirection.HOLD, size=0.0)
        targets = [
            ActionTarget(
                action=action,
                confidence=confidence,
                rationale=trace.rationale,
            )
        ]
        return trace, targets
