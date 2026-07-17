# QA Checklist — RADA S16

**Date:** 2026-07-17

## Sprint hygiene

- [x] `issues/` mirrors projects-management vault sprint seeds
- [x] `issues/sprint-s16-production-hygiene.yaml` present
- [x] `issues/README.md` indexes sprints

## S16-03 Metrics consolidation

- [x] Single registry backs `/metrics`
- [x] `utils/metrics.py` delegates to `observability/metrics.py`
- [x] `tests/unit/test_utils_metrics.py` passes
- [x] `tests/unit/test_observability.py` passes

## S16-01 Experiment

- [x] Experiment spec in `experiments/lightest/tool_aware_baseline_smoke.json`
- [ ] Integration test pass on Python 3.11+ CI

## Documentation

- [x] `logs/exec-baseline.md` captures environment
- [x] `reports/execution-summary.md` summarizes outcomes

## Open for next sprint slice

- [ ] S16-04 RADAError hierarchy
- [ ] S16-05 Rate limiting
- [ ] S16-06 BaseSettings
- [ ] S16-07 Dashboard UX
