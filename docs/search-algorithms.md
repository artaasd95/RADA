# Search algorithms

Toy-market and fixture documentation for the RADA search layer. This is **not** production trading guidance.

## Components

| Module | Role |
|--------|------|
| `simulation.py` | Causal shock scenarios → `MarketEvent` streams |
| `vectorized_env.py` | Batched retrieval stub |
| `game_theory.py` | Nash-style spread action batching |
| `mcts.py` | Hybrid MCTS planner with risk gating |
| `risk_selection.py` | CVaR-feasible action pick (TailWarp stub) |
| `eval.py` | Regret, CVaR breach rate, faithfulness on fixtures |

## Risk-constrained selection

`select_cvar_feasible_action` filters candidate actions using `TailWarpStub.estimate_tail_loss` and picks the largest feasible size within the CVaR budget.

## Evaluation

Fixture set: `benchmarks/search/fixture_cases.json`

```bash
python scripts/benchmark_search.py
pytest tests/unit/test_search_eval.py -q
```

## Demo

```bash
python examples/search_demo.py
```

## Feature flag (decision integration)

Set `RADA_SEARCH_ENABLED=true` to enable the optional `SearchLoop` before the risk gate. Default is off.
