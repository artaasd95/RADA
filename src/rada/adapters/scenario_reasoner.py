"""Mock scenario reasoner using shock fixtures."""

from __future__ import annotations

from rada.interfaces import BaseReasoner
from rada.schemas import ActionDirection, DecisionTrace, MarketEvent, ProposedAction
from rada.search.simulation import ShockScenario


class ScenarioReasoner(BaseReasoner):
    """Proposes actions from shock scenario context; mock adapter for demos."""

    def __init__(self, scenario: ShockScenario | None = None) -> None:
        self._scenario = scenario or ShockScenario(
            name="macro-liquidity-shock",
            symbol="BTCUSD",
            base_price=60000.0,
            price_delta_pct=-8.0,
            causality_chain=["macro", "liquidity", "price"],
            steps=3,
        )

    def _shock_threshold_price(self) -> float:
        return self._scenario.base_price * (1.0 + self._scenario.price_delta_pct / 100.0)

    def _is_shock_active(self, event: MarketEvent) -> bool:
        if event.symbol != self._scenario.symbol:
            return False
        return event.price < self._shock_threshold_price()

    def _suggested_size(self, event: MarketEvent) -> float:
        return max(0.1, min(event.volume, 10.0))

    async def reason(self, event: MarketEvent) -> DecisionTrace:
        shock_active = self._is_shock_active(event)
        direction = ActionDirection.SELL if shock_active else ActionDirection.HOLD
        return DecisionTrace(
            model_name="scenario-reasoner-mock",
            rationale=(
                f"Shock scenario {self._scenario.name}: live price {event.price:.2f} "
                f"vs threshold {self._shock_threshold_price():.2f} -> {direction.value}"
            ),
            assumptions=[
                f"price_delta_pct={self._scenario.price_delta_pct}",
                f"event_volume={event.volume}",
            ],
            faithfulness_score=0.75 if shock_active else 0.9,
        )

    async def propose_from_event(self, event: MarketEvent) -> ProposedAction:
        shock_active = self._is_shock_active(event)
        if shock_active:
            return ProposedAction(
                direction=ActionDirection.SELL,
                size=self._suggested_size(event),
                cvar_impact=0.04,
            )
        return ProposedAction(direction=ActionDirection.HOLD, size=0.0, cvar_impact=0.0)
