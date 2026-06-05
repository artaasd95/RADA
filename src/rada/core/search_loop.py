"""Optional search layer hook before risk gate (S9-01)."""

from __future__ import annotations

import os

from rada.schemas import ActionDirection, DecisionTrace, MarketEvent, ProposedAction
from rada.search.mcts import MCTSPlanner, TrinityPolicyStub
from rada.interfaces import BaseRiskOptimizer
from rada.search.risk_selection import select_cvar_feasible_action
from rada.utils.metrics import record_search_invocation


def search_enabled() -> bool:
    return os.getenv("RADA_SEARCH_ENABLED", "").lower() in {"1", "true", "yes"}


class SearchLoop:
    """Runs MCTS + CVaR selection when enabled; otherwise transparent pass-through."""

    def __init__(
        self,
        *,
        risk_optimizer: BaseRiskOptimizer,
        enabled: bool | None = None,
    ) -> None:
        self._enabled = search_enabled() if enabled is None else enabled
        self._planner = MCTSPlanner(risk_optimizer=risk_optimizer)
        self._policy_stub = TrinityPolicyStub()

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def refine_proposal(
        self,
        event: MarketEvent,
        trace: DecisionTrace,
        proposed: ProposedAction,
    ) -> ProposedAction:
        record_search_invocation(self._enabled)
        if not self._enabled:
            return proposed

        plan = await self._planner.plan(event, trace)
        best = plan.get("best_action", {})
        direction = best.get("direction", proposed.direction.value)
        size = float(best.get("size", proposed.size))

        candidates = self._policy_stub.propose_candidates(event, top_k=3)
        if candidates:
            chosen = select_cvar_feasible_action(candidates, price=event.price)
            return chosen

        return ProposedAction(direction=ActionDirection(direction), size=size)
