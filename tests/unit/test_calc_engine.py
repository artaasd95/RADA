from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from rada.calc.engine import compute_cvar, compute_drawdown, compute_position_size
from rada.calc.schemas import CalcConfidence

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "calc_known_answers.yaml"


@pytest.mark.unit
def test_known_cvar_fixtures() -> None:
    data = yaml.safe_load(_FIXTURES.read_text(encoding="utf-8"))
    for case in data["cvar"]:
        result = compute_cvar(case["returns"], alpha=case.get("alpha", 0.05))
        if "min_value" in case:
            assert result.value >= case["min_value"]
        if "max_value" in case:
            assert result.value <= case["max_value"]
        assert result.units == "fraction"


@pytest.mark.unit
def test_known_position_size_fixtures() -> None:
    data = yaml.safe_load(_FIXTURES.read_text(encoding="utf-8"))
    for case in data["position_size"]:
        result = compute_position_size(
            capital=case["capital"],
            risk_budget=case["risk_budget"],
            price=case["price"],
            volatility=case["volatility"],
        )
        if "min_value" in case:
            assert result.value >= case["min_value"]
        if "max_value" in case:
            assert result.value <= case["max_value"]


@pytest.mark.unit
def test_known_drawdown_fixtures() -> None:
    data = yaml.safe_load(_FIXTURES.read_text(encoding="utf-8"))
    for case in data["drawdown"]:
        result = compute_drawdown(case["equity"])
        if "min_value" in case:
            assert result.value >= case["min_value"]
        if "max_value" in case:
            assert result.value <= case["max_value"]


@pytest.mark.unit
def test_cvar_low_confidence_short_series() -> None:
    result = compute_cvar([0.01, 0.02])
    assert result.confidence == CalcConfidence.LOW
