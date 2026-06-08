from __future__ import annotations

import pytest

from rada.observability import get_logger, get_metrics, get_tracer


@pytest.mark.unit
def test_observability_imports_without_optional_deps() -> None:
    tracer = get_tracer()
    metrics = get_metrics()
    logger = get_logger("rada.test")
    with tracer.start_span("test.span", event_id="e1") as span:
        span.set_attribute("decision_id", "d1")
    metrics.inc("rada_decisions_total")
    logger.info("observability ok")
    assert "rada_decisions_total" in metrics.render_prometheus()
