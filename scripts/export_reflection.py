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
from rada.data.export_batch import export_decisions
from rada.data.storage import InMemoryDecisionStore
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export decisions for reflection (batch, off hot path)")
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    parser.add_argument("--batch-id", default=None)
    parser.add_argument("--synthetic-count", type=int, default=0)
    args = parser.parse_args(argv)

    decisions: list[Decision] = []
    if args.synthetic_count > 0:
        decisions = asyncio.run(_synthetic_decisions(args.synthetic_count))

    if not decisions:
        print("No decisions to export; pass --synthetic-count N for smoke runs.", file=sys.stderr)
        return 1

    summary = export_decisions(decisions, output_dir=args.output_dir, batch_id=args.batch_id)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
