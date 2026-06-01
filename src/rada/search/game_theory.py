"""Game-theoretic search stubs for spread/action proposals."""

from __future__ import annotations

from rada.schemas import MarketEvent


def _signal_strength(market_hits: list[dict[str, str]]) -> float:
    scores: list[float] = []
    for hit in market_hits:
        raw_score = hit.get("score")
        if raw_score is None:
            continue
        try:
            scores.append(float(raw_score))
        except ValueError:
            continue

    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 6)


def nash_spread_search_stub(
    *,
    symbol: str,
    reference_price: float,
    market_hits: list[dict[str, str]],
    top_k: int = 3,
) -> dict[str, object]:
    """Return a deterministic Nash-style spread search result.

    The output is a JSON-serializable dashboard payload and intentionally
    lightweight until full game-theory models are introduced.
    """
    top_k = max(1, top_k)
    signal = _signal_strength(market_hits)
    candidate_spreads_bps = [-5.0, 0.0, 5.0][:top_k]

    candidates: list[dict[str, object]] = []
    for spread_bps in candidate_spreads_bps:
        utility = signal - abs(spread_bps) / 100.0
        candidates.append(
            {
                "spread_bps": spread_bps,
                "signal": signal,
                "utility": round(utility, 6),
            }
        )

    best = max(candidates, key=lambda item: float(item["utility"]))
    spread_bps = float(best["spread_bps"])
    if spread_bps > 0:
        direction = "BUY"
    elif spread_bps < 0:
        direction = "SELL"
    else:
        direction = "HOLD"

    size = max(reference_price / 100000.0, 0.0)

    return {
        "symbol": symbol,
        "method": "nash_spread_search_stub",
        "equilibrium_action": {
            "direction": direction,
            "size": round(size, 6),
            "spread_bps": spread_bps,
        },
        "candidates": candidates,
        "meta": {
            "top_k": top_k,
            "signal_strength": signal,
        },
    }


def batch_nash_spread_search_stub(
    events: list[MarketEvent],
    batched_hits: list[list[dict[str, str]]],
    top_k: int = 3,
) -> list[dict[str, object]]:
    """Run the Nash-style stub over a batch of events and retrieved hit-lists."""
    if len(events) != len(batched_hits):
        raise ValueError("events and batched_hits must have equal length")

    return [
        nash_spread_search_stub(
            symbol=event.symbol,
            reference_price=event.price,
            market_hits=hits,
            top_k=top_k,
        )
        for event, hits in zip(events, batched_hits, strict=True)
    ]