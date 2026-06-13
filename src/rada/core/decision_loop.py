"""Decision loop orchestration for bootstrap milestone."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from rada.calc.runner import run_event_calcs, synthetic_context_from_results
from rada.core.reasoner_loop import ActionTarget, ReasonerLoop
from rada.interfaces import BaseDataStore, BasePolicy, BaseReasoner, BaseRiskOptimizer
from rada.schemas import ActionDirection, Decision, DecisionTrace, MarketEvent, ProposedAction
from rada.search.risk_selection import TailWarpStub, select_cvar_feasible_action

if TYPE_CHECKING:
    from rada.audit.writer import AuditWriter
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
        reasoner_loop: ReasonerLoop | None = None,
        cvar_limit: float = 0.05,
        audit_writer: AuditWriter | None = None,
    ) -> None:
        self._reasoner = reasoner
        self._policy = policy
        self._risk_optimizer = risk_optimizer
        self._data_store = data_store
        self._search_loop = search_loop
        self._reasoner_loop = reasoner_loop or ReasonerLoop(reasoner)
        self._cvar_limit = cvar_limit
        self._audit_writer = audit_writer

    def _effective_cvar_limit(self, synthetic_cvar: float | None) -> float:
        if synthetic_cvar is None or math.isnan(synthetic_cvar):
            return self._cvar_limit
        return min(self._cvar_limit, max(synthetic_cvar, 0.01))

    def _select_from_targets(
        self,
        event: MarketEvent,
        trace: DecisionTrace,
        targets: list[ActionTarget],
        *,
        cvar_limit: float,
    ) -> ProposedAction:
        _ = trace
        candidates = [t.action for t in targets]
        if not candidates:
            return ProposedAction(direction=ActionDirection.HOLD, size=0)
        return select_cvar_feasible_action(
            candidates,
            price=event.price,
            tailwarp=TailWarpStub(cvar_limit=cvar_limit),
        )

    async def process_one(self, event: MarketEvent) -> Decision:
        from rada.observability.metrics import LatencyTimer, get_metrics
        from rada.observability.tracer import get_tracer

        tracer = get_tracer()
        metrics = get_metrics()

        with LatencyTimer(), tracer.start_span("ingest", event_id=event.symbol) as ingest_span:
            ingest_span.set_attribute("symbol", event.symbol)

            with tracer.start_span("calc") as calc_span:
                calc_results = run_event_calcs(event)
                synthetic = synthetic_context_from_results(calc_results)
                cvar_raw = synthetic.get("cvar")
                cvar_value = cvar_raw if cvar_raw is not None else float("nan")
                effective_cvar_limit = self._effective_cvar_limit(
                    cvar_raw if cvar_raw is not None else None
                )
                calc_span.set_attribute("cvar_value", cvar_value)

            with tracer.start_span("select") as select_span:
                trace, targets = await self._reasoner_loop.propose_targets(event)
                assumptions = list(trace.assumptions)
                if not math.isnan(cvar_value):
                    assumptions.append(f"synthetic_cvar={cvar_value:.4f}")
                trace = trace.model_copy(
                    update={
                        "calc_results": [r.model_dump() for r in calc_results],
                        "synthetic_context": synthetic,
                        "assumptions": assumptions,
                    }
                )
                proposed = self._select_from_targets(
                    event,
                    trace,
                    targets,
                    cvar_limit=effective_cvar_limit,
                )
                if proposed.direction == ActionDirection.HOLD:
                    proposed = await self._policy.propose(event, trace)
                if self._search_loop is not None and self._search_loop.enabled:
                    proposed = await self._search_loop.refine_proposal(
                        event,
                        trace,
                        proposed,
                        cvar_limit=effective_cvar_limit,
                    )
                select_span.set_attribute("direction", proposed.direction.value)

            with tracer.start_span("risk_gate", cvar_value=cvar_value) as gate_span:
                optimized = await self._risk_optimizer.optimize(proposed, trace)
                if (
                    optimized.direction == ActionDirection.HOLD
                    and proposed.direction != ActionDirection.HOLD
                ):
                    metrics.inc("rada_risk_gate_rejections_total")
                    gate_span.set_attribute("rejected", True)

            decision = Decision(
                market_event=event,
                proposed_action=optimized,
                trace=trace,
            )

            with tracer.start_span("persist", decision_id=decision.decision_id) as persist_span:
                await self._data_store.save_decision(decision)
                persist_span.set_attribute("decision_id", decision.decision_id)

            if self._audit_writer is not None:
                from rada.audit.schemas import AuditEventType

                self._audit_writer.emit(
                    AuditEventType.DECISION,
                    decision_id=decision.decision_id,
                    payload_after=decision.model_dump(mode="json"),
                )
                self._audit_writer.emit(
                    AuditEventType.CALC,
                    decision_id=decision.decision_id,
                    payload_after={"synthetic_context": synthetic},
                )

            metrics.inc("rada_decisions_total")
            return decision
