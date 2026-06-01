import pytest

from rada.search.vectorized_env import VectorizedSearchEnv


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_batch_returns_one_result_set_per_query() -> None:
    env = VectorizedSearchEnv(max_concurrency=8)

    results = await env.search_batch(["macro shock", "liquidity shock"], top_k=3)

    assert len(results) == 2
    assert len(results[0]) == 3
    assert results[0][0]["rank"] == "1"
    assert results[1][2]["rank"] == "3"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_run_parallel_episodes_smoke_100_without_external_broker() -> None:
    env = VectorizedSearchEnv(max_concurrency=100)

    episodes = await env.run_parallel_episodes(query="btc stress", episode_count=100, top_k=2)

    assert len(episodes) == 100
    assert all(len(hits) == 2 for hits in episodes)
    assert episodes[0][0]["query"].startswith("btc stress::episode-")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_returns_empty_for_non_positive_top_k() -> None:
    env = VectorizedSearchEnv()

    results = await env.search(query="anything", top_k=0)

    assert results == []
