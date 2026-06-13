#!/usr/bin/env python3
"""Run search eval fixtures (not live market)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from rada.search.eval import evaluate_cases, load_fixture_set  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Benchmark search layer on fixture set")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=_REPO / "benchmarks" / "search" / "fixture_cases.json",
    )
    args = parser.parse_args(argv)

    cases = load_fixture_set(args.fixture)
    report = evaluate_cases(cases)
    print(json.dumps(report.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
