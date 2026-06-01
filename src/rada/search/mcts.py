"""Monte Carlo Tree Search stubs for hybrid policy/simulation/risk planning."""

from __future__ import annotations

import os
from dataclasses import dataclass
from time import perf_counter

from rada.interfaces import BaseRiskOptimizer
from rada.schemas import ActionDirection, DecisionTrace, MarketEvent, ProposedAction


@dataclass(slots=True)
class MCTSConfig:
    iterations: int = 64
    rollout_depth: int = 3
    exploration: float = 1.414


class TrinityPolicyStub:
    """Deterministic policy-proposal stub used as MCTS prior."""

    source_name = "trinity-stub"

    def propose_candidates(self, event: MarketEvent, top_k: int = 3) -> list[ProposedAction]:
        top_k = max(1, top_k)
        base_size = max(event.volume / 10.0, 0.0)
        directions = [ActionDirection.BUY, ActionDirection.HOLD, ActionDirection.SELL]

        candidates: list[ProposedAction] = []
        for index in range(top_k):
            direction = directions[index % len(directions)]
            size = round(base_size * (1.0 + 0.1 * index), 6)
            if direction == ActionDirection.HOLD:
                size = 0.0
            candidates.append(ProposedAction(direction=direction, size=size))

        return candidates


@dataclass(slots=True)
class _Node:
    action: ProposedAction
    visits: int = 0
    value_sum: float = 0.0

    @property
    def mean_value(self) -> float:
        if self.visits == 0:
            return 0.0
        return self.value_sum / self.visits


class MCTSPlanner:
    """Hybrid planner that combines Trinity proposals, rollouts, and risk gating."""

    def __init__(
        self,
        *,
        risk_optimizer: BaseRiskOptimizer,
        policy_stub: TrinityPolicyStub | None = None,
        config: MCTSConfig | None = None,
    ) -> None:
        self._risk_optimizer = risk_optimizer
        self._policy_stub = policy_stub or TrinityPolicyStub()
        self._config = config or MCTSConfig()

    async def plan(self, event: MarketEvent, trace: DecisionTrace) -> dict[str, object]:
        candidates = self._policy_stub.propose_candidates(event, top_k=3)
        nodes = [_Node(action=candidate) for candidate in candidates]

        for iteration in range(self._config.iterations):
            node = nodes[iteration % len(nodes)]

            # Risk optimizer is consulted at expansion time.
            expanded_action = await self._risk_optimizer.optimize(node.action, trace)

            # Risk optimizer is consulted again during rollout to mirror hybrid design hooks.
            rollout_action = await self._risk_optimizer.optimize(expanded_action, trace)

            reward = _rollout_reward(event, rollout_action, depth=self._config.rollout_depth)
            node.visits += 1
            node.value_sum += reward

        best = max(nodes, key=lambda n: n.mean_value)
        best_action = await self._risk_optimizer.optimize(best.action, trace)

        return {
            "algorithm": "mcts-hybrid-stub",
            "policy_source": self._policy_stub.source_name,
            "event_symbol": event.symbol,
            "best_action": {
                "direction": best_action.direction.value,
                "size": best_action.size,
                "risk_adjusted_size": best_action.risk_adjusted_size,
                "cvar_impact": best_action.cvar_impact,
            },
            "search_stats": {
                "iterations": self._config.iterations,
                "rollout_depth": self._config.rollout_depth,
                "nodes": [
                    {
                        "direction": node.action.direction.value,
                        "size": node.action.size,
                        "visits": node.visits,
                        "mean_value": round(node.mean_value, 6),
                    }
                    for node in nodes
                ],
            },
        }


def _rollout_reward(event: MarketEvent, action: ProposedAction, *, depth: int) -> float:
    direction_multiplier = {
        ActionDirection.BUY: 1.0,
        ActionDirection.HOLD: 0.2,
        ActionDirection.SELL: -1.0,
    }[action.direction]
    size = action.risk_adjusted_size if action.risk_adjusted_size is not None else action.size
    scale = max(depth, 1)
    return direction_multiplier * size * event.price / (100000.0 * scale)


async def run_mcts_benchmark_fixture(
    planner: MCTSPlanner,
    *,
    event: MarketEvent,
    trace: DecisionTrace,
    budget_seconds: float | None = None,
) -> dict[str, object]:
    """Run a bounded benchmark fixture and return JSON-serializable summary."""
    default_budget = float(os.getenv("RADA_MCTS_BENCHMARK_BUDGET_SECONDS", "60"))
    target_budget = budget_seconds if budget_seconds is not None else default_budget

    start = perf_counter()
    result = await planner.plan(event, trace)
    elapsed_seconds = perf_counter() - start

    return {
        "result": result,
        "timing": {
            "elapsed_seconds": round(elapsed_seconds, 6),
            "budget_seconds": target_budget,
            "within_budget": elapsed_seconds <= target_budget,
        },
    }