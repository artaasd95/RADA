"""Search environment interface contract."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseSearchEnv(ABC):
    """Provides environment search primitives for simulation/planning."""

    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> list[dict[str, str]]:
        """Return ranked search hits from an environment index."""
