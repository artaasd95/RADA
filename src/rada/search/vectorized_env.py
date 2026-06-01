"""Asyncio-first vectorized search environment.

This module provides a broker-free, deterministic vectorized environment that can
run many parallel episodes for search simulations.
"""

from __future__ import annotations

import asyncio

from rada.interfaces import BaseSearchEnv


class VectorizedSearchEnv(BaseSearchEnv):
    """Runs single-query and batched-query searches with bounded concurrency."""

    def __init__(self, max_concurrency: int = 100) -> None:
        if max_concurrency < 1:
            raise ValueError("max_concurrency must be >= 1")
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def search(self, query: str, top_k: int = 5) -> list[dict[str, str]]:
        if top_k < 1:
            return []

        normalized = query.strip().lower() or "empty"
        async with self._semaphore:
            # Yield control to keep fairness under high episode fan-out.
            await asyncio.sleep(0)
            return [
                {
                    "query": normalized,
                    "rank": str(rank),
                    "score": f"{1.0 / rank:.6f}",
                }
                for rank in range(1, top_k + 1)
            ]

    async def search_batch(self, queries: list[str], top_k: int = 5) -> list[list[dict[str, str]]]:
        tasks = [self.search(query=query, top_k=top_k) for query in queries]
        if not tasks:
            return []
        return await asyncio.gather(*tasks)

    async def run_parallel_episodes(
        self,
        *,
        query: str,
        episode_count: int,
        top_k: int = 5,
    ) -> list[list[dict[str, str]]]:
        """Run many independent episodes in parallel for one scenario query."""
        if episode_count < 0:
            raise ValueError("episode_count must be >= 0")

        episode_queries = [f"{query}::episode-{index}" for index in range(episode_count)]
        return await self.search_batch(episode_queries, top_k=top_k)