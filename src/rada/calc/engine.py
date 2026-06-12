"""Local calc engine — pure Python/NumPy, no CUDA."""

from __future__ import annotations

from typing import Any

import numpy as np

from rada.calc.schemas import CalcConfidence, CalcResult


def _result(
    expression: str,
    value: float,
    units: str,
    confidence: CalcConfidence,
    method: str,
    context: dict[str, Any] | None = None,
) -> CalcResult:
    return CalcResult(
        expression=expression,
        value=float(value),
        units=units,
        confidence=confidence,
        method=method,
        context=context or {},
    )


def compute_cvar(returns: list[float], *, alpha: float = 0.05) -> CalcResult:
    if len(returns) < 5:
        return _result(
            "cvar",
            float("nan"),
            "fraction",
            CalcConfidence.LOW,
            "insufficient_samples",
            {"n": len(returns)},
        )
    arr = np.asarray(returns, dtype=np.float64)
    var_threshold = np.quantile(arr, alpha)
    tail = arr[arr <= var_threshold]
    if tail.size == 0:
        return _result(
            "cvar",
            float("nan"),
            "fraction",
            CalcConfidence.LOW,
            "empty_tail",
            {"alpha": alpha, "var_threshold": float(var_threshold)},
        )
    cvar = float(-np.mean(tail))
    conf = CalcConfidence.HIGH if len(returns) >= 20 else CalcConfidence.MEDIUM
    return _result("cvar", cvar, "fraction", conf, "historical_cvar", {"alpha": alpha, "n": len(returns)})


def compute_position_size(
    *,
    capital: float,
    risk_budget: float,
    price: float,
    volatility: float,
) -> CalcResult:
    if capital <= 0 or price <= 0 or volatility <= 0:
        return _result("position_size", 0.0, "units", CalcConfidence.LOW, "invalid_inputs")
    raw = (capital * risk_budget) / (price * volatility)
    size = float(max(0.0, raw))
    conf = CalcConfidence.HIGH if risk_budget > 0 and volatility < 1.0 else CalcConfidence.MEDIUM
    return _result(
        "position_size",
        size,
        "units",
        conf,
        "risk_budget_sizing",
        {"capital": capital, "risk_budget": risk_budget, "price": price, "volatility": volatility},
    )


def compute_drawdown(equity_curve: list[float]) -> CalcResult:
    if len(equity_curve) < 2:
        return _result("drawdown", 0.0, "fraction", CalcConfidence.LOW, "insufficient_samples")
    arr = np.asarray(equity_curve, dtype=np.float64)
    running_max = np.maximum.accumulate(arr)
    drawdowns = (running_max - arr) / np.where(running_max == 0, 1.0, running_max)
    max_dd = float(np.max(drawdowns))
    conf = CalcConfidence.HIGH if len(equity_curve) >= 10 else CalcConfidence.MEDIUM
    return _result("drawdown", max_dd, "fraction", conf, "running_max_drawdown", {"n": len(equity_curve)})
