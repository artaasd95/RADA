"""Rolling P&L analytics stubs from decision outcomes."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from rada.schemas import ActionDirection, Decision
from rada.utils.metrics import set_gauge


@dataclass
class RollingPnLTracker:
    """Maintains a rolling window of stub P&L values derived from decisions."""

    window: int = 10
    _values: deque[float] = field(default_factory=deque)

    def record(self, decision: Decision) -> float:
        pnl = pnl_stub_from_decision(decision)
        self._values.append(pnl)
        while len(self._values) > self.window:
            self._values.popleft()
        rolling = sum(self._values) / len(self._values)
        set_gauge("rada_rolling_pnl_stub", rolling)
        return rolling

    @property
    def rolling_average(self) -> float:
        if not self._values:
            return 0.0
        return sum(self._values) / len(self._values)


def pnl_stub_from_decision(decision: Decision) -> float:
    """Compute a deterministic stub P&L from action direction and event price."""
    action = decision.proposed_action
    size = action.risk_adjusted_size if action.risk_adjusted_size is not None else action.size
    price = decision.market_event.price

    if action.direction == ActionDirection.HOLD or size == 0:
        return 0.0
    if action.direction == ActionDirection.BUY:
        return round(size * price * 0.001, 4)
    return round(-size * price * 0.001, 4)


def compute_rolling_pnl(decisions: list[Decision], *, window: int = 10) -> float:
    """Return rolling average stub P&L over the last `window` decisions."""
    tracker = RollingPnLTracker(window=window)
    for decision in decisions:
        tracker.record(decision)
    return tracker.rolling_average
