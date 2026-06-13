#!/usr/bin/env python3
"""Toy-market search demo — fixture/smoke only."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from rada.core.decision_loop import PassThroughRiskOptimizer  # noqa: E402
from rada.core.search_loop import SearchLoop  # noqa: E402
from rada.schemas import ActionDirection, DecisionTrace, ProposedAction  # noqa: E402
from rada.search.eval import evaluate_cases, load_fixture_set  # noqa: E402
from rada.search.simulation import ShockScenario, generate_shock_scenario  # noqa: E402


async def main() -> None:
    scenario = ShockScenario(
        name="demo-shock",
        symbol="BTCUSD",
        base_price=42000.0,
        price_delta_pct=-2.0,
        causality_chain=["liquidity"],
        steps=3,
        start_time=datetime(2026, 6, 1, tzinfo=UTC),
    )
    events = generate_shock_scenario(scenario)
    risk = PassThroughRiskOptimizer()
    search = SearchLoop(risk_optimizer=risk, enabled=True)
    trace = DecisionTrace(model_name="search-demo", rationale="fixture")

    outputs = []
    for event in events:
        hold = ProposedAction(direction=ActionDirection.HOLD, size=0.0)
        refined = await search.refine_proposal(event, trace, hold)
        outputs.append(
            {
                "symbol": event.symbol,
                "price": event.price,
                "direction": refined.direction.value,
                "size": refined.size,
            }
        )

    fixture_report = evaluate_cases(
        load_fixture_set(_ROOT / "benchmarks" / "search" / "fixture_cases.json")
    )
    print(json.dumps({"events": outputs, "eval": fixture_report.to_dict()}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
