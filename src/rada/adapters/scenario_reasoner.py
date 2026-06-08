"""Mock scenario reasoner using shock fixtures."""

from __future__ import annotations

from rada.interfaces import BaseReasoner
from rada.schemas import ActionDirection, DecisionTrace, MarketEvent, ProposedAction
from rada.search.simulation import ShockScenario, generate_shock_scenario


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

    async def reason(self, event: MarketEvent) -> DecisionTrace:
        events = generate_shock_scenario(self._scenario)
        shock_active = any(
            e.symbol == event.symbol and e.price < self._scenario.base_price for e in events
        )
        direction = ActionDirection.SELL if shock_active else ActionDirection.HOLD
        return DecisionTrace(
            model_name="scenario-reasoner-mock",
            rationale=f"Shock scenario {self._scenario.name}: suggest {direction.value}",
            assumptions=[f"price_delta_pct={self._scenario.price_delta_pct}"],
            faithfulness_score=0.75 if shock_active else 0.9,
        )

    async def propose_from_event(self, event: MarketEvent) -> ProposedAction:
        trace = await self.reason(event)
        if "SELL" in trace.rationale:
            return ProposedAction(direction=ActionDirection.SELL, size=1.0, cvar_impact=0.04)
        return ProposedAction(direction=ActionDirection.HOLD, size=0.0, cvar_impact=0.0)
