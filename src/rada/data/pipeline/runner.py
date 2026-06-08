"""Usage and export pipeline runners — no hot-path latency change."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rada.data.pipeline.config import PipelineConfig
from rada.schemas import Decision, MarketEvent


@dataclass(slots=True)
class StageResult:
    stage: str
    records_in: int
    records_out: int
    metadata: dict[str, Any] = field(default_factory=dict)


class UsagePipelineRunner:
    """Runs usage-mode stages: normalize → lineage (stub hooks)."""

    def __init__(self, config: PipelineConfig) -> None:
        if config.mode != "usage":
            raise ValueError(f"expected usage config, got mode={config.mode!r}")
        self.config = config

    def run_batch(self, events: list[MarketEvent]) -> list[StageResult]:
        results: list[StageResult] = []
        normalized = list(events)
        results.append(
            StageResult(
                stage="normalize",
                records_in=len(events),
                records_out=len(normalized),
                metadata={"contract": "MarketEvent"},
            )
        )
        results.append(
            StageResult(
                stage="lineage",
                records_in=len(normalized),
                records_out=len(normalized),
                metadata={"via": "quality_hooks"},
            )
        )
        return results


class ExportPipelineRunner:
    """Runs export-mode stages off the hot path."""

    def __init__(self, config: PipelineConfig) -> None:
        if config.mode != "export":
            raise ValueError(f"expected export config, got mode={config.mode!r}")
        self.config = config

    def run_batch(self, decisions: list[Decision]) -> tuple[list[StageResult], list[Decision]]:
        results: list[StageResult] = []
        rows = list(decisions)
        rows_in = len(rows)
        for stage_def in self.config.preprocessing.stages:
            stage_name = next(iter(stage_def.keys()), "unknown")
            rows_out = rows_in
            if stage_name == "filter":
                require_outcome = stage_def.get("filter", {}).get("require_outcome", False)
                if require_outcome:
                    rows = [d for d in rows if d.outcome is not None]
                    rows_out = len(rows)
            results.append(
                StageResult(
                    stage=stage_name,
                    records_in=rows_in,
                    records_out=rows_out,
                    metadata=dict(stage_def.get(stage_name, {})),
                )
            )
            rows_in = rows_out
        return results, rows

    def filter_decisions(self, decisions: list[Decision]) -> list[Decision]:
        """Apply export preprocessing and return filtered decisions."""
        _, filtered = self.run_batch(decisions)
        return filtered
