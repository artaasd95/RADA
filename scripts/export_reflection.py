#!/usr/bin/env python3
"""Batch export CLI — off hot path (S6-08)."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))

from rada.core.decision_loop import (
    DecisionLoop,
    HoldPolicy,
    NoOpReasoner,
    PassThroughRiskOptimizer,
)
from rada.core.reflection_loop import stub_outcome
from rada.data.export_batch import export_decisions
from rada.data.storage import InMemoryDecisionStore
from rada.main import RuntimeSettings, build_data_store
from rada.schemas import Decision, MarketEvent


async def _synthetic_decisions(count: int) -> list[Decision]:
    store = InMemoryDecisionStore()
    loop = DecisionLoop(
        reasoner=NoOpReasoner(),
        policy=HoldPolicy(),
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=store,
    )
    out: list[Decision] = []
    for index in range(count):
        event = MarketEvent(
            symbol="SYN",
            price=100.0 + index,
            volume=1.0,
            timestamp=datetime(2026, 6, 1, tzinfo=UTC),
        )
        out.append(await loop.process_one(event))
    return out


async def _decisions_from_db(
    *,
    since: datetime | None,
    limit: int | None,
    policy_ids: list[str] | None,
) -> list[Decision]:
    settings = RuntimeSettings()
    store = build_data_store(settings)
    if hasattr(store, "ensure_ready"):
        await store.ensure_ready()  # type: ignore[attr-defined]
    try:
        return await store.list_decisions(since=since, limit=limit, policy_ids=policy_ids)
    finally:
        close = getattr(store, "close", None)
        if close is not None:
            await close()


def _parse_since(value: str | None) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export decisions for reflection (batch, off hot path)")
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    parser.add_argument("--batch-id", default=None)
    parser.add_argument("--synthetic-count", type=int, default=0)
    parser.add_argument("--from-db", action="store_true", help="Read decisions from configured data store")
    parser.add_argument("--since", default=None, help="ISO8601 lower bound for decision timestamp")
    parser.add_argument("--limit", type=int, default=None, help="Max decisions to export")
    parser.add_argument(
        "--policy-ids",
        nargs="*",
        default=None,
        help="Filter by policy_id (e.g. balanced conservative)",
    )
    args = parser.parse_args(argv)

    decisions: list[Decision] = []
    if args.synthetic_count > 0:
        decisions = asyncio.run(_synthetic_decisions(args.synthetic_count))
    elif args.from_db:
        decisions = asyncio.run(
            _decisions_from_db(
                since=_parse_since(args.since),
                limit=args.limit,
                policy_ids=args.policy_ids,
            )
        )

    if not decisions:
        print(
            "No decisions to export; pass --synthetic-count N or --from-db for store reads.",
            file=sys.stderr,
        )
        return 1

    decisions = [
        d if d.outcome is not None else d.model_copy(update={"outcome": stub_outcome(d)})
        for d in decisions
    ]
    summary = export_decisions(decisions, output_dir=args.output_dir, batch_id=args.batch_id)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
