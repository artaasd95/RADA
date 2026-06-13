"""Outcome and feedback tool implementations."""

from __future__ import annotations

from rada.schemas import ActionDirection
from rada.tools.base import BaseTool, ToolResult


class OutcomeEvaluatorImpl(BaseTool):
    name = "outcome_evaluator"

    def run(self, *, entry_price: float, exit_price: float, direction: ActionDirection | str, size: float) -> ToolResult:
        d = direction.value if isinstance(direction, ActionDirection) else str(direction)
        pnl = 0.0
        if d == ActionDirection.BUY.value:
            pnl = (exit_price - entry_price) * size
        elif d == ActionDirection.SELL.value:
            pnl = (entry_price - exit_price) * size
        return ToolResult(
            name=self.name,
            output={
                "pnl": float(round(pnl, 6)),
                "win": bool(pnl > 0),
                "direction": d,
                "size": float(size),
            },
        )


class FeedbackGeneratorImpl(BaseTool):
    name = "feedback_generator"

    def run(self, *, decision: str, risk_ok: bool, expected_return: float) -> ToolResult:
        summary = (
            f"Decision {decision} accepted with expected_return={expected_return:.4f}"
            if risk_ok
            else f"Decision {decision} rejected due to risk constraints"
        )
        return ToolResult(
            name=self.name,
            output={
                "decision": decision,
                "risk_ok": bool(risk_ok),
                "expected_return": float(expected_return),
                "summary": summary,
            },
        )
