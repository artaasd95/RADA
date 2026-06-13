# Tool Integration

ToolAwarePolicy coordinates deterministic tool execution in this order:
1. action_proposer
2. risk_calculator
3. constraint_checker
4. outcome_evaluator
5. feedback_generator

Each call is appended to DecisionTrace.tool_calls and consumed by downstream observability/audit layers.
