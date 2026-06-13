"""Risk and constraint calculator tool implementations."""

from __future__ import annotations

from rada.schemas import ActionDirection
from rada.tools.base import BaseTool, ToolResult


class RiskCalculatorImpl(BaseTool):
    name = "risk_calculator"

    def run(self, *, direction: ActionDirection | str, size: float, price: float) -> ToolResult:
        direction_value = direction.value if isinstance(direction, ActionDirection) else str(direction)
        direction_factor = 0.0 if direction_value == ActionDirection.HOLD.value else 1.0
        cvar = round(min(0.25, (abs(size) * price / 100000.0) * direction_factor), 6)
        expected_return = round((0.002 * size * price) * (1 if direction_value == "BUY" else -1 if direction_value == "SELL" else 0), 6)
        return ToolResult(
            name=self.name,
            output={
                "direction": direction_value,
                "size": float(size),
                "price": float(price),
                "cvar": cvar,
                "expected_return": expected_return,
            },
        )


class ConstraintCheckerImpl(BaseTool):
    name = "constraint_checker"

    def run(self, *, size: float, cvar: float, max_size: float, max_cvar: float) -> ToolResult:
        size_ok = abs(size) <= max_size
        cvar_ok = cvar <= max_cvar
        return ToolResult(
            name=self.name,
            output={
                "size_ok": bool(size_ok),
                "cvar_ok": bool(cvar_ok),
                "allowed": bool(size_ok and cvar_ok),
                "max_size": float(max_size),
                "max_cvar": float(max_cvar),
            },
        )
