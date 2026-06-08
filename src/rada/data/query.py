"""Shared decision query helpers for storage backends."""

from __future__ import annotations

from datetime import UTC, datetime

from rada.schemas import Decision


def filter_decisions(
    decisions: list[Decision],
    *,
    since: datetime | None = None,
    limit: int | None = None,
    policy_ids: list[str] | None = None,
) -> list[Decision]:
    """Apply since/limit/policy filters and return newest-first ordering."""
    filtered = decisions
    if since is not None:
        since_utc = since.astimezone(UTC) if since.tzinfo else since.replace(tzinfo=UTC)
        filtered = [d for d in filtered if d.timestamp >= since_utc]
    if policy_ids:
        allowed = set(policy_ids)
        filtered = [d for d in filtered if d.policy_id in allowed]
    filtered.sort(key=lambda d: d.timestamp, reverse=True)
    if limit is not None and limit > 0:
        filtered = filtered[:limit]
    return filtered
