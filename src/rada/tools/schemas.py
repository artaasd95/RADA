"""OpenAI function-calling schemas for RADA tools."""

from __future__ import annotations

from typing import Any


def _base_schema(name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


RISK_CALCULATOR_SCHEMA = _base_schema(
    "risk_calculator",
    "Estimate cvar-style risk from direction, size, and price.",
    {
        "direction": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
        "size": {"type": "number"},
        "price": {"type": "number"},
    },
    ["direction", "size", "price"],
)

CONSTRAINT_CHECKER_SCHEMA = _base_schema(
    "constraint_checker",
    "Validate action against configured cvar and size limits.",
    {
        "size": {"type": "number"},
        "cvar": {"type": "number"},
        "max_size": {"type": "number"},
        "max_cvar": {"type": "number"},
    },
    ["size", "cvar", "max_size", "max_cvar"],
)

ACTION_PROPOSER_SCHEMA = _base_schema(
    "action_proposer",
    "Produce initial action candidate from market movement signal.",
    {
        "symbol": {"type": "string"},
        "price": {"type": "number"},
        "reference_price": {"type": "number"},
        "volume": {"type": "number"},
    },
    ["symbol", "price", "reference_price", "volume"],
)

OUTCOME_EVALUATOR_SCHEMA = _base_schema(
    "outcome_evaluator",
    "Evaluate realized pnl and drawdown after decision.",
    {
        "entry_price": {"type": "number"},
        "exit_price": {"type": "number"},
        "direction": {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
        "size": {"type": "number"},
    },
    ["entry_price", "exit_price", "direction", "size"],
)

FEEDBACK_GENERATOR_SCHEMA = _base_schema(
    "feedback_generator",
    "Generate deterministic feedback summary from tool signals.",
    {
        "decision": {"type": "string"},
        "risk_ok": {"type": "boolean"},
        "expected_return": {"type": "number"},
    },
    ["decision", "risk_ok", "expected_return"],
)

TOOL_SCHEMAS = [
    RISK_CALCULATOR_SCHEMA,
    CONSTRAINT_CHECKER_SCHEMA,
    ACTION_PROPOSER_SCHEMA,
    OUTCOME_EVALUATOR_SCHEMA,
    FEEDBACK_GENERATOR_SCHEMA,
]
