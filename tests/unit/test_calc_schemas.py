from __future__ import annotations

import pytest
from pydantic import ValidationError

from rada.calc.schemas import CalcConfidence, CalcRequest, CalcResult


@pytest.mark.unit
def test_calc_request_roundtrip() -> None:
    req = CalcRequest(expression="cvar", context={"alpha": 0.05}, expected_units="fraction")
    restored = CalcRequest.model_validate_json(req.model_dump_json())
    assert restored == req


@pytest.mark.unit
def test_calc_result_roundtrip() -> None:
    res = CalcResult(
        expression="drawdown",
        value=0.12,
        units="fraction",
        confidence=CalcConfidence.HIGH,
        method="running_max",
    )
    restored = CalcResult.model_validate_json(res.model_dump_json())
    assert restored.confidence == CalcConfidence.HIGH


@pytest.mark.unit
def test_calc_result_rejects_invalid_confidence() -> None:
    with pytest.raises(ValidationError):
        CalcResult(
            expression="x",
            value=1.0,
            units="u",
            confidence="INVALID",  # type: ignore[arg-type]
            method="m",
        )
