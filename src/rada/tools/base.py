"""Base abstractions for deterministic tool execution."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Normalized tool execution payload."""

    name: str
    output: dict[str, Any]
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """Tool interface used by tool-aware policy."""

    name: str

    @abstractmethod
    def run(self, **kwargs: Any) -> ToolResult:
        """Execute tool logic and return normalized result."""
