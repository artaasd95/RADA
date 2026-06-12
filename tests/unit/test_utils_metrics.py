from __future__ import annotations

import pytest

from rada.utils import metrics as legacy_metrics


@pytest.mark.unit
def test_legacy_metrics_increment_and_render() -> None:
    legacy_metrics.increment_counter("rada_decisions_processed_total", 2)
    snapshot = legacy_metrics.get_metrics_snapshot()
    assert snapshot["decisions_processed"] >= 2
    rendered = legacy_metrics.render_prometheus_text()
    assert "rada_decisions_processed_total" in rendered
