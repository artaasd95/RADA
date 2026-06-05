from __future__ import annotations

from pathlib import Path

import pytest

from rada.search.eval import evaluate_cases, load_fixture_set

_REPO = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_evaluate_fixture_set() -> None:
    cases = load_fixture_set(_REPO / "benchmarks" / "search" / "fixture_cases.json")
    report = evaluate_cases(cases)
    assert report.cases == 3
    assert 0.0 <= report.regret_mean <= 1.0
    assert 0.0 <= report.cvar_breach_rate <= 1.0
