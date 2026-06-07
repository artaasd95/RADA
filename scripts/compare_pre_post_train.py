#!/usr/bin/env python3
"""Compare base model vs post-train LoRA adapter on shared fixtures."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from rada.evaluation.pre_post_compare import run_pre_post_compare, write_report  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Pre vs post-train comparison.")
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, default=None, help="Existing adapter dir")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--methods", default="reflection", help="Comma-separated: policy,reflection")
    parser.add_argument("--output-run-id", default="pre-post-smoke")
    parser.add_argument("--no-train", action="store_true", help="Skip mini-train; use --adapter only")
    return parser.parse_args()


async def _main_async(args: argparse.Namespace) -> int:
    methods = [m.strip() for m in args.methods.split(",") if m.strip()]
    report = await run_pre_post_compare(
        args.model_id,
        args.fixtures,
        methods=methods,  # type: ignore[arg-type]
        adapter_path=args.adapter,
        output_run_id=args.output_run_id,
        train=not args.no_train,
    )

    output = args.output
    if output is None:
        repo_root = Path(__file__).resolve().parents[1]
        output = repo_root / "reports" / f"pre_post_{args.model_id}.json"

    write_report(report, output)
    print(report.to_dict())
    print(f"Wrote {output}")
    return 0


def main() -> int:
    args = parse_args()
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    raise SystemExit(main())
