# Execution baseline — RADA (S16-01)

**Date:** 2026-07-17  
**Sprint:** S16 — Execution + Production Hygiene

## Environment

- Repo: `artaasd95/RADA` branch `develop`
- Local Python 3.9 (Anaconda); CI target Python 3.11+
- Metrics consolidation (S16-03) verified via unit tests

## Lightest experiment

Compare **ToolAwarePolicy** vs **HoldPolicy** on fixture `MarketEvent` (BTCUSD @ 58000).

- Code path: `tests/integration/test_decision_with_tools.py`
- Tool-aware policy emits ≥4 tool calls including `risk_calculator`
- Baseline HoldPolicy emits no tool trace

## Results

| Check | Status |
|-------|--------|
| Unit metrics tests | PASS |
| Observability import smoke | PASS |
| Integration tool-aware test | BLOCKED (Python 3.9 — `StrEnum` import) |
| S16-03 metrics consolidation | DONE |

## Blockers

- Re-run integration suite on Python 3.11+ for full S16-01 sign-off

## Artifacts

- `experiments/lightest/tool_aware_baseline_smoke.json`
- `reports/execution-summary.md`
