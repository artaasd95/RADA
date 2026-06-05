"""Decision loop orchestration for bootstrap milestone."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rada.interfaces import BaseDataStore, BasePolicy, BaseReasoner, BaseRiskOptimizer
from rada.schemas import ActionDirection, Decision, DecisionTrace, MarketEvent, ProposedAction

if TYPE_CHECKING:
    from rada.core.search_loop import SearchLoop


class NoOpReasoner(BaseReasoner):
    """Bootstrap reasoner returning a placeholder trace."""

    async def reason(self, event: MarketEvent) -> DecisionTrace:
        return DecisionTrace(
            model_name="bootstrap-noop-reasoner",
            rationale=f"No-op reasoner consumed {event.symbol}",
            warnings=["placeholder trace"],
        )


class HoldPolicy(BasePolicy):
    """Bootstrap policy always returning HOLD until strategy is implemented."""

    async def propose(self, event: MarketEvent, trace: DecisionTrace) -> ProposedAction:
        _ = event
        _ = trace
        return ProposedAction(direction=ActionDirection.HOLD, size=0)


class PassThroughRiskOptimizer(BaseRiskOptimizer):
    """Bootstrap risk optimizer that preserves action and annotates risk metadata."""

    async def optimize(self, action: ProposedAction, trace: DecisionTrace) -> ProposedAction:
        _ = trace
        return action.model_copy(update={"risk_adjusted_size": action.size, "cvar_impact": 0.0})


class DecisionLoop:
    """Consumes one event and emits one persisted decision."""

    def __init__(
        self,
        *,
        reasoner: BaseReasoner,
        policy: BasePolicy,
        risk_optimizer: BaseRiskOptimizer,
        data_store: BaseDataStore,
        search_loop: SearchLoop | None = None,
    ) -> None:
        self._reasoner = reasoner
        self._policy = policy
        self._risk_optimizer = risk_optimizer
        self._data_store = data_store
        self._search_loop = search_loop

    async def process_one(self, event: MarketEvent) -> Decision:
        trace = await self._reasoner.reason(event)
        proposed = await self._policy.propose(event, trace)
        if self._search_loop is not None and self._search_loop.enabled:
            proposed = await self._search_loop.refine_proposal(event, trace, proposed)
        optimized = await self._risk_optimizer.optimize(proposed, trace)

        decision = Decision(
            market_event=event,
            proposed_action=optimized,
            trace=trace,
        )
        await self._data_store.save_decision(decision)
        return decision
