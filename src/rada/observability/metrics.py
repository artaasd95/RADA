"""Prometheus-style metrics facade — single registry for all RADA metrics."""

from __future__ import annotations

import threading
import time
from typing import Any

_DEFAULT_COUNTERS: dict[str, int] = {
    "rada_decisions_total": 0,
    "rada_risk_gate_rejections_total": 0,
    "rada_loop_errors_total": 0,
    "rada_decisions_processed_total": 0,
    "rada_events_ingested_total": 0,
    "rada_ingest_quality_rejected_total": 0,
    "rada_reflection_processed_total": 0,
    "rada_search_invocations_total": 0,
}

_DEFAULT_GAUGES: dict[str, float] = {
    "rada_rolling_pnl_stub": 0.0,
    "rada_reflection_mean_faithfulness": 0.0,
}


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = dict(_DEFAULT_COUNTERS)
        self._gauges: dict[str, float] = dict(_DEFAULT_GAUGES)
        self._histograms: dict[str, list[float]] = {
            "rada_decision_latency_seconds": [],
        }

    def inc(self, name: str, amount: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + amount

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def observe(self, name: str, value: float) -> None:
        with self._lock:
            self._histograms.setdefault(name, []).append(value)

    def render_prometheus(self) -> str:
        lines: list[str] = []
        with self._lock:
            for name, value in self._counters.items():
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {value}")
            for name, value in self._gauges.items():
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name} {value}")
            for name, values in self._histograms.items():
                lines.append(f"# TYPE {name} histogram")
                if values:
                    lines.append(f"{name}_sum {sum(values)}")
                    lines.append(f"{name}_count {len(values)}")
                else:
                    lines.append(f"{name}_sum 0")
                    lines.append(f"{name}_count 0")
        return "\n".join(lines) + "\n"

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {k: len(v) for k, v in self._histograms.items()},
            }

    def flat_snapshot(self) -> dict[str, int | float]:
        """Flat counter + gauge map for legacy JSON /metrics/json consumers."""
        with self._lock:
            merged: dict[str, int | float] = {**self._counters, **self._gauges}
            return merged


_registry: MetricsRegistry | None = None


def get_metrics() -> MetricsRegistry:
    global _registry
    if _registry is None:
        _registry = MetricsRegistry()
    return _registry


class LatencyTimer:
    def __init__(self, histogram: str = "rada_decision_latency_seconds") -> None:
        self._histogram = histogram
        self._start = 0.0

    def __enter__(self) -> LatencyTimer:
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        get_metrics().observe(self._histogram, time.perf_counter() - self._start)
