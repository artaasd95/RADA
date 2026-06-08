"""Calc request/result schemas for verified numerical claims."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CalcConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class CalcRequest(BaseModel):
    expression: str
    context: dict[str, Any] = Field(default_factory=dict)
    expected_units: str


class CalcResult(BaseModel):
    expression: str
    value: float
    units: str
    confidence: CalcConfidence
    method: str
    context: dict[str, Any] = Field(default_factory=dict)
