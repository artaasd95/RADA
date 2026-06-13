# Tool Schema

RADA S15 tool layer uses OpenAI function-calling style schemas for deterministic tool invocation.

## Tool Set
- risk_calculator
- constraint_checker
- action_proposer
- outcome_evaluator
- feedback_generator

Schemas are defined in src/rada/tools/schemas.py as TOOL_SCHEMAS.
