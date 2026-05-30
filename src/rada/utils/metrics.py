"""Minimal metrics and OpenTelemetry hook stubs for MVP.

Post-MVP (S9) production monitoring will expand these into full OTel export.
See docs/monitoring.md for endpoint and alert documentation.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable
from typing import Any

_lock = threading.Lock()
_counters: dict[str, int] = {
    "rada_decisions_processed_total": 0,
    "rada_events_ingested_total": 0,
    "rada_ingest_quality_rejected_total": 0,
}
_gauges: dict[str, float] = {
    "rada_rolling_pnl_stub": 0.0,
}

_otel_hooks: list[Callable[[str, dict[str, Any]], None]] = []


def increment_counter(name: str, amount: int = 1) -> None:
    with _lock:
        _counters[name] = _counters.get(name, 0) + amount


def set_gauge(name: str, value: float) -> None:
    with _lock:
        _gauges[name] = value


def record_decision_processed() -> None:
    increment_counter("rada_decisions_processed_total")
    _emit_otel("decision.processed", {})


def record_event_ingested(source: str = "unknown") -> None:
    increment_counter("rada_events_ingested_total")
    _emit_otel("event.ingested", {"source": source})


def record_quality_rejection(reason: str) -> None:
    increment_counter("rada_ingest_quality_rejected_total")
    _emit_otel("ingest.quality_rejected", {"reason": reason})


def register_otel_hook(hook: Callable[[str, dict[str, Any]], None]) -> None:
    """Register a post-MVP OpenTelemetry exporter callback."""
    _otel_hooks.append(hook)


def _emit_otel(event: str, attributes: dict[str, Any]) -> None:
    if os.getenv("RADA_OTEL_ENABLED", "").lower() in {"1", "true", "yes"}:
        for hook in _otel_hooks:
            hook(event, attributes)


def get_metrics_snapshot() -> dict[str, int | float]:
    with _lock:
        return {**_counters, **_gauges}


def render_prometheus_text() -> str:
    """Render a minimal Prometheus exposition format body."""
    lines: list[str] = []
    with _lock:
        for name, value in _counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        for name, value in _gauges.items():
            lines.append(f"# TYPE {name} gauge")
            lines.append(f"{name} {value}")
    return "\n".join(lines) + "\n"
