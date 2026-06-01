"""Search environment interface contract."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseSearchEnv(ABC):
    """Provides environment search primitives for simulation/planning."""

    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> list[dict[str, str]]:
        """Return ranked search hits from an environment index."""

    async def search_batch(self, queries: list[str], top_k: int = 5) -> list[list[dict[str, str]]]:
        """Return one ranked hit-list per query.

        Implementations may override this method for true vectorized execution.
        The default behavior preserves compatibility by calling ``search`` per query.
        """
        return [await self.search(query=query, top_k=top_k) for query in queries]
