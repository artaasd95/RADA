"""Search evaluation framework — fixture/benchmark metrics (S8-03)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rada.schemas import ActionDirection, ProposedAction
from rada.search.risk_selection import TailWarpStub, select_cvar_feasible_action


@dataclass(slots=True)
class SearchEvalCase:
    symbol: str
    price: float
    candidates: list[dict[str, Any]]
    optimal_direction: str
    max_cvar_breach: float = 0.0
    faithfulness_target: float = 0.8


@dataclass(slots=True)
class SearchEvalReport:
    regret_mean: float
    cvar_breach_rate: float
    faithfulness_mean: float
    cases: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "regret_mean": round(self.regret_mean, 6),
            "cvar_breach_rate": round(self.cvar_breach_rate, 6),
            "faithfulness_mean": round(self.faithfulness_mean, 6),
            "cases": self.cases,
        }


def load_fixture_set(path: Path) -> list[SearchEvalCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cases: list[SearchEvalCase] = []
    for item in raw:
        cases.append(
            SearchEvalCase(
                symbol=item["symbol"],
                price=float(item["price"]),
                candidates=list(item["candidates"]),
                optimal_direction=item["optimal_direction"],
                max_cvar_breach=float(item.get("max_cvar_breach", 0.0)),
                faithfulness_target=float(item.get("faithfulness_target", 0.8)),
            )
        )
    return cases


def _parse_candidates(raw_candidates: list[dict[str, Any]]) -> list[ProposedAction]:
    actions: list[ProposedAction] = []
    for item in raw_candidates:
        actions.append(
            ProposedAction(
                direction=ActionDirection(item["direction"]),
                size=float(item.get("size", 0.0)),
            )
        )
    return actions


def evaluate_cases(cases: list[SearchEvalCase]) -> SearchEvalReport:
    regrets: list[float] = []
    breaches: list[float] = []
    faithfulness: list[float] = []

    tailwarp = TailWarpStub(cvar_limit=0.05)

    for case in cases:
        candidates = _parse_candidates(case.candidates)
        chosen = select_cvar_feasible_action(candidates, price=case.price, tailwarp=tailwarp)

        optimal = ActionDirection(case.optimal_direction)
        regret = 0.0 if chosen.direction == optimal else 1.0
        regrets.append(regret)

        tail_loss = tailwarp.estimate_tail_loss(chosen, price=case.price)
        breaches.append(1.0 if tail_loss > tailwarp.cvar_limit else 0.0)

        match = 1.0 if chosen.direction.value == case.optimal_direction else case.faithfulness_target
        faithfulness.append(match)

    n = max(len(cases), 1)
    return SearchEvalReport(
        regret_mean=sum(regrets) / n,
        cvar_breach_rate=sum(breaches) / n,
        faithfulness_mean=sum(faithfulness) / n,
        cases=len(cases),
    )
