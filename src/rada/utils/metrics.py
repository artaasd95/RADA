"""Metrics helpers — delegates to the unified observability registry."""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import Any

from rada.observability.metrics import get_metrics

_otel_hooks: list[Callable[[str, dict[str, Any]], None]] = []
_alert_hooks: list[Callable[[str, dict[str, Any]], None]] = []


def increment_counter(name: str, amount: int = 1) -> None:
    get_metrics().inc(name, amount)


def set_gauge(name: str, value: float) -> None:
    get_metrics().set_gauge(name, value)


def record_decision_processed() -> None:
    get_metrics().inc("rada_decisions_processed_total")
    get_metrics().inc("rada_decisions_total")
    _emit_otel("decision.processed", {})


def record_event_ingested(source: str = "unknown") -> None:
    get_metrics().inc("rada_events_ingested_total")
    _emit_otel("event.ingested", {"source": source})


def record_quality_rejection(reason: str) -> None:
    get_metrics().inc("rada_ingest_quality_rejected_total")
    _emit_otel("ingest.quality_rejected", {"reason": reason})


def record_reflection_processed(mean_faithfulness: float) -> None:
    get_metrics().inc("rada_reflection_processed_total")
    get_metrics().set_gauge("rada_reflection_mean_faithfulness", mean_faithfulness)
    _emit_otel("reflection.processed", {"mean_faithfulness": mean_faithfulness})


def record_search_invocation(enabled: bool) -> None:
    if enabled:
        get_metrics().inc("rada_search_invocations_total")
    _emit_otel("search.invocation", {"enabled": enabled})


def register_alert_hook(hook: Callable[[str, dict[str, Any]], None]) -> None:
    _alert_hooks.append(hook)


def emit_alert(name: str, *, severity: str = "warning", **attributes: Any) -> None:
    payload = {"severity": severity, **attributes}
    for hook in _alert_hooks:
        hook(name, payload)
    _emit_otel(f"alert.{name}", payload)


def register_otel_hook(hook: Callable[[str, dict[str, Any]], None]) -> None:
    _otel_hooks.append(hook)


def _emit_otel(event: str, attributes: dict[str, Any]) -> None:
    if os.getenv("RADA_OTEL_ENABLED", "").lower() in {"1", "true", "yes"}:
        for hook in _otel_hooks:
            hook(event, attributes)


def get_metrics_snapshot() -> dict[str, int | float]:
    return get_metrics().flat_snapshot()


def render_prometheus_text() -> str:
    """Deprecated: use get_metrics().render_prometheus() directly."""
    return get_metrics().render_prometheus()
