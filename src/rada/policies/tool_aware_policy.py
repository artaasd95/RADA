"""Tool-aware decision policy integrating deterministic tools and optional model adapter."""

from __future__ import annotations

from rada.interfaces import BasePolicy
from rada.schemas import ActionDirection, DecisionTrace, MarketEvent, ProposedAction
from rada.tools import (
    ActionProposer,
    ConstraintChecker,
    FeedbackGenerator,
    OutcomeEvaluator,
    RiskCalculator,
)


class ToolAwarePolicy(BasePolicy):
    """Generates proposals through tool calls and records tool traces."""

    def __init__(self, *, max_size: float = 5.0, max_cvar: float = 0.05) -> None:
        self._max_size = max_size
        self._max_cvar = max_cvar
        self._risk = RiskCalculator()
        self._constraint = ConstraintChecker()
        self._proposer = ActionProposer()
        self._outcome = OutcomeEvaluator()
        self._feedback = FeedbackGenerator()

    async def propose(self, event: MarketEvent, trace: DecisionTrace) -> ProposedAction:
        reference_price = event.price
        if "last_price" in trace.synthetic_context:
            reference_price = float(trace.synthetic_context["last_price"])

        proposed = self._proposer.run(
            symbol=event.symbol,
            price=event.price,
            reference_price=reference_price,
            volume=event.volume,
        )
        direction = ActionDirection(proposed.output["direction"])
        size = float(proposed.output["size"])

        risk = self._risk.run(direction=direction, size=size, price=event.price)
        constraints = self._constraint.run(
            size=size,
            cvar=float(risk.output["cvar"]),
            max_size=self._max_size,
            max_cvar=self._max_cvar,
        )

        allowed = bool(constraints.output["allowed"])
        final_direction = direction if allowed else ActionDirection.HOLD
        final_size = size if allowed else 0.0

        outcome = self._outcome.run(
            entry_price=event.price,
            exit_price=event.price,
            direction=final_direction,
            size=final_size,
        )
        feedback = self._feedback.run(
            decision=final_direction.value,
            risk_ok=allowed,
            expected_return=float(risk.output["expected_return"]),
        )

        if not hasattr(trace, "tool_calls"):
            setattr(trace, "tool_calls", [])
        trace.tool_calls.extend(
            [
                {"name": proposed.name, "output": proposed.output},
                {"name": risk.name, "output": risk.output},
                {"name": constraints.name, "output": constraints.output},
                {"name": outcome.name, "output": outcome.output},
                {"name": feedback.name, "output": feedback.output},
            ]
        )

        return ProposedAction(
            direction=final_direction,
            size=final_size,
            risk_adjusted_size=final_size,
            cvar_impact=float(risk.output["cvar"]),
        )
