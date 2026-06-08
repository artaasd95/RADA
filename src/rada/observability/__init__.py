"""Observability facades with graceful degradation."""

from rada.observability.logger import get_logger
from rada.observability.metrics import get_metrics
from rada.observability.tracer import get_tracer

__all__ = ["get_logger", "get_metrics", "get_tracer"]
