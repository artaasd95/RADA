"""Action proposer tool implementations."""

from __future__ import annotations

from rada.schemas import ActionDirection
from rada.tools.base import BaseTool, ToolResult


class ActionProposerImpl(BaseTool):
    name = "action_proposer"

    def run(self, *, symbol: str, price: float, reference_price: float, volume: float) -> ToolResult:
        delta = price - reference_price
        if abs(delta) < 1e-6:
            direction = ActionDirection.HOLD
            size = 0.0
        elif delta < 0:
            direction = ActionDirection.BUY
            size = max(0.1, min(volume, 5.0))
        else:
            direction = ActionDirection.SELL
            size = max(0.1, min(volume, 5.0))

        return ToolResult(
            name=self.name,
            output={
                "symbol": symbol,
                "direction": direction.value,
                "size": float(size),
                "reference_price": float(reference_price),
                "delta": float(delta),
            },
        )
