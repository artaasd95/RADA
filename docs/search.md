# Search Layer (R6/R7)

This document covers the current simulation/search pipeline used for integration and benchmark preparation.

## Flow

1. Generate deterministic market events from `ShockScenario`.
2. Execute vectorized query retrieval with `VectorizedSearchEnv`.
3. Produce a batched Nash-style spread action payload.
4. Attach uncertainty intervals for dashboard-ready JSON outputs.

## Reference modules

- `src/rada/search/simulation.py`
- `src/rada/search/vectorized_env.py`
- `src/rada/search/game_theory.py`
- `src/rada/search/uncertainty.py`

## Integration test

Run the simulation-layer integration smoke:

```bash
python -m pytest tests/integration/test_simulation_layer.py -q -m integration
```

## Timescale smoke

Optional (requires Timescale running on `RADA_DATABASE_URL`):

```bash
python -m pytest tests/integration/test_timescale_store.py -q -m integration
```
