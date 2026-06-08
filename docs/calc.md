# Calc contract

RADA verifies numerical claims on the hot path before LLM selection and risk gating.

## API

| Function | Input | Output units |
|----------|-------|--------------|
| `compute_cvar(returns, alpha=0.05)` | Return series | `fraction` |
| `compute_position_size(capital, risk_budget, price, volatility)` | Risk budget sizing | `units` |
| `compute_drawdown(equity_curve)` | Equity series | `fraction` |

Each returns `CalcResult`: `{expression, value, units, confidence, method, context}`.

Confidence levels: `HIGH`, `MEDIUM`, `LOW` (insufficient data → `LOW`).

## How RADA verifies numbers

1. `run_event_calcs(event)` runs on ingest fields.
2. Results attach to `DecisionTrace.calc_results` and `verified_context`.
3. Reasoner prompts receive **verified_context** only for numeric claims.
4. Risk gate uses calc CVaR for `TailWarpStub` budget.

## Verified vs unverified claims

**Verified** (backed by calc):

> "CVaR estimate is 0.032 (HIGH confidence, historical_cvar)."

**Unverified** (must not drive risk gate):

> "Market will recover 15% next week."

Unverified claims may appear in rationale but are excluded from `verified_context`.

## Related

- [`src/rada/calc/engine.py`](../src/rada/calc/engine.py)
- [`tests/fixtures/calc_known_answers.yaml`](../tests/fixtures/calc_known_answers.yaml)
