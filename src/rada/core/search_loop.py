"""Optional search layer hook before risk gate (S9-01)."""

from __future__ import annotations

import os

from rada.interfaces import BaseRiskOptimizer
from rada.schemas import ActionDirection, DecisionTrace, MarketEvent, ProposedAction
from rada.search.mcts import MCTSPlanner, TrinityPolicyStub
from rada.search.risk_selection import TailWarpStub, select_cvar_feasible_action
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
        cvar_limit: float = 0.05,
    ) -> None:
        self._enabled = search_enabled() if enabled is None else enabled
        self._cvar_limit = cvar_limit
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
        *,
        cvar_limit: float | None = None,
    ) -> ProposedAction:
        _ = trace
        record_search_invocation(self._enabled)
        if not self._enabled:
            return proposed

        effective_limit = cvar_limit if cvar_limit is not None else self._cvar_limit
        tailwarp = TailWarpStub(cvar_limit=effective_limit)

        plan = await self._planner.plan(event, trace)
        best = plan.get("best_action", {})
        try:
            mcts_direction = ActionDirection(best.get("direction", proposed.direction.value))
        except ValueError:
            mcts_direction = proposed.direction
        mcts_size = float(best.get("size", proposed.size))
        mcts_action = ProposedAction(direction=mcts_direction, size=mcts_size)

        candidates = self._policy_stub.propose_candidates(event, top_k=3)
        merged: list[ProposedAction] = [mcts_action]
        for candidate in candidates:
            if candidate.direction != mcts_action.direction or candidate.size != mcts_action.size:
                merged.append(candidate)

        if merged:
            return select_cvar_feasible_action(
                merged,
                price=event.price,
                tailwarp=tailwarp,
            )

        return mcts_action
