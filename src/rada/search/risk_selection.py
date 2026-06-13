"""Risk-constrained action selection with TailWarp stub adapter (S8-02)."""

from __future__ import annotations

from dataclasses import dataclass

from rada.schemas import ActionDirection, ProposedAction
from rada.search.constants import DEFAULT_CAPITAL_NOTIONAL


@dataclass(slots=True)
class TailWarpStub:
    """Mock TailWarp adapter returning tail-loss as a fraction of capital."""

    cvar_limit: float = 0.05
    capital: float = DEFAULT_CAPITAL_NOTIONAL

    def estimate_tail_loss(self, action: ProposedAction, *, price: float) -> float:
        """Return estimated tail loss as a fraction of capital (comparable to CVaR fractions)."""
        if price <= 0:
            return 0.0
        size = action.risk_adjusted_size if action.risk_adjusted_size is not None else action.size
        direction_scale = {
            ActionDirection.BUY: 1.0,
            ActionDirection.SELL: 1.2,
            ActionDirection.HOLD: 0.0,
        }[action.direction]
        notional = direction_scale * size * price
        return notional / self.capital


def select_cvar_feasible_action(
    candidates: list[ProposedAction],
    *,
    price: float,
    tailwarp: TailWarpStub | None = None,
) -> ProposedAction:
    """Pick the highest-size action whose estimated tail loss stays within CVaR budget."""
    adapter = tailwarp or TailWarpStub()
    feasible: list[ProposedAction] = []
    for action in candidates:
        tail_loss = adapter.estimate_tail_loss(action, price=price)
        if tail_loss <= adapter.cvar_limit:
            feasible.append(action)

    if not feasible:
        return ProposedAction(direction=ActionDirection.HOLD, size=0.0)

    return max(
        feasible,
        key=lambda a: a.risk_adjusted_size if a.risk_adjusted_size is not None else a.size,
    )
