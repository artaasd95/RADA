"""OpenTelemetry tracer facade — no-op when OTel absent."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any


@dataclass
class _Span:
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)
    start: float = field(default_factory=time.perf_counter)

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def end(self) -> float:
        return (time.perf_counter() - self.start) * 1000.0


class _NoOpTracer:
    @contextmanager
    def start_span(self, name: str, **attrs: Any) -> Iterator[_Span]:
        span = _Span(name=name, attributes=dict(attrs))
        try:
            yield span
        finally:
            latency_ms = span.end()
            if os.getenv("RADA_OTEL_ENABLED", "").lower() in {"1", "true", "yes"}:
                print(f"[otel] span={name} latency_ms={latency_ms:.2f} attrs={span.attributes}")


_tracer: _NoOpTracer | None = None


def get_tracer() -> _NoOpTracer:
    global _tracer
    if _tracer is None:
        try:
            import opentelemetry  # noqa: F401

            _tracer = _NoOpTracer()
        except ImportError:
            _tracer = _NoOpTracer()
    return _tracer
