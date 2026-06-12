#!/usr/bin/env python3
"""Export audit events to NDJSON."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from rada.audit.store import AuditStore  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export audit events to NDJSON")
    parser.add_argument("--db", default="./rada_audit.db", help="Audit SQLite database path")
    parser.add_argument("--output", "-o", default="audit.ndjson", help="Output NDJSON file")
    parser.add_argument("--from", dest="from_", default=None, help="ISO timestamp lower bound")
    parser.add_argument("--to", default=None, help="ISO timestamp upper bound")
    parser.add_argument("--limit", type=int, default=10_000, help="Maximum rows to export")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    store = AuditStore(db_path=args.db)
    from_ts = datetime.fromisoformat(args.from_.replace("Z", "+00:00")) if args.from_ else None
    to_ts = datetime.fromisoformat(args.to.replace("Z", "+00:00")) if args.to else None
    events = await store.export_range(from_ts, to_ts)
    events = events[: args.limit]

    out_path = Path(args.output)
    with out_path.open("w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event.model_dump(mode="json")) + "\n")
    print(f"exported {len(events)} events to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
