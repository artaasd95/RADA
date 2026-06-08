"""Async reflection loop — off the hot decision path (S3-03).

Completed decisions are enqueued without blocking ``DecisionLoop``. A background
consumer runs auditor scoring, sets outcome stubs, updates policy checkpoint,
and emits batch export rows.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from rada.data.export_batch import export_decisions
from rada.interfaces import BaseAuditor, BaseDataStore, BasePolicy
from rada.schemas import Decision, DecisionTrace
from rada.utils.metrics import record_reflection_processed


def stub_outcome(decision: Decision) -> dict[str, object]:
    """Reflection-path outcome stub for export filter compatibility."""
    return {
        "status": "simulated_fill",
        "pnl_stub": 0.0,
        "filled_at": datetime.now(tz=UTC).isoformat(),
        "decision_id": decision.decision_id,
    }


@dataclass(slots=True)
class PolicyCheckpoint:
    """Lightweight policy state updated from audit feedback."""

    version: int = 0
    audit_count: int = 0
    mean_faithfulness: float = 0.0
    last_rationale: str = ""
    policy_update_signals: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ReflectionSummary:
    """Audit report payload for reflection batch runs."""

    processed: int = 0
    exported_batch_id: str | None = None
    export_paths: dict[str, str] = field(default_factory=dict)
    checkpoint_version: int = 0


class StubAuditor(BaseAuditor):
    """Deterministic auditor for integration tests and local dev."""

    async def audit(self, decision: Decision) -> DecisionTrace:
        base = decision.trace.faithfulness_score
        score = 0.85 if base is None else min(max(base, 0.0), 1.0)
        return decision.trace.model_copy(
            update={
                "faithfulness_score": score,
                "rationale": f"stub-audit:{decision.decision_id[:8]}",
                "warnings": list(decision.trace.warnings),
            }
        )


class ReflectionPolicyUpdater:
    """Applies audit scores to an in-memory policy checkpoint (stub)."""

    def __init__(self, policy: BasePolicy | None = None) -> None:
        self._policy = policy
        self.checkpoint = PolicyCheckpoint()

    async def apply(self, decision: Decision, audit_trace: DecisionTrace) -> PolicyCheckpoint:
        score = audit_trace.faithfulness_score or 0.0
        n = self.checkpoint.audit_count
        self.checkpoint.mean_faithfulness = (self.checkpoint.mean_faithfulness * n + score) / (n + 1)
        self.checkpoint.audit_count += 1
        self.checkpoint.version += 1
        self.checkpoint.last_rationale = audit_trace.rationale
        self.checkpoint.policy_update_signals.append(f"policy_tune:{decision.decision_id[:8]}")
        _ = self._policy
        return self.checkpoint


class ReflectionLoop:
    """Consumes completed decisions asynchronously; does not block decision emit."""

    def __init__(
        self,
        *,
        auditor: BaseAuditor | None = None,
        policy_updater: ReflectionPolicyUpdater | None = None,
        data_store: BaseDataStore | None = None,
        export_dir: Path | None = None,
        queue_maxsize: int = 256,
    ) -> None:
        self._auditor = auditor or StubAuditor()
        self._policy_updater = policy_updater or ReflectionPolicyUpdater()
        self._data_store = data_store
        self._export_dir = export_dir or Path("exports/reflection_runtime")
        self._queue: asyncio.Queue[Decision | None] = asyncio.Queue(maxsize=queue_maxsize)
        self._consumer_task: asyncio.Task[None] | None = None
        self._audit_scores: list[float] = []
        self._processed_with_outcome: list[Decision] = []
        self._last_summary = ReflectionSummary()

    @property
    def policy_checkpoint(self) -> PolicyCheckpoint:
        return self._policy_updater.checkpoint

    @property
    def audit_scores(self) -> list[float]:
        return list(self._audit_scores)

    @property
    def last_summary(self) -> ReflectionSummary:
        return self._last_summary

    def enqueue(self, decision: Decision) -> None:
        """Fire-and-forget enqueue; safe from the hot decision path."""
        try:
            self._queue.put_nowait(decision)
        except asyncio.QueueFull:
            return

    async def drain_one(self) -> bool:
        """Process a single queued decision (for tests without background task)."""
        try:
            decision = self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return False
        if decision is None:
            return False
        await self._process(decision)
        return True

    async def drain_all(self) -> int:
        """Process all pending decisions; returns count processed."""
        count = 0
        while await self.drain_one():
            count += 1
        return count

    async def run_batch_from_store(self, *, limit: int | None = 100) -> ReflectionSummary:
        """Read action DB off hot path, audit, export, and update policy checkpoint."""
        if self._data_store is None:
            return ReflectionSummary()
        decisions = await self._data_store.list_decisions(limit=limit)
        for decision in decisions:
            await self._process(decision)
        return self._last_summary

    def start(self) -> None:
        if self._consumer_task is None or self._consumer_task.done():
            self._consumer_task = asyncio.create_task(self._consumer_loop())

    async def stop(self) -> None:
        if self._consumer_task is not None:
            await self._queue.put(None)
            await self._consumer_task
            self._consumer_task = None

    async def _consumer_loop(self) -> None:
        while True:
            decision = await self._queue.get()
            if decision is None:
                break
            await self._process(decision)

    async def _process(self, decision: Decision) -> None:
        audit_trace = await self._auditor.audit(decision)
        score = audit_trace.faithfulness_score or 0.0
        self._audit_scores.append(score)

        enriched = decision.model_copy(update={"outcome": stub_outcome(decision)})
        self._processed_with_outcome.append(enriched)

        checkpoint = await self._policy_updater.apply(enriched, audit_trace)
        record_reflection_processed(checkpoint.mean_faithfulness)

        if len(self._processed_with_outcome) >= 1:
            summary = export_decisions(
                self._processed_with_outcome,
                output_dir=self._export_dir,
                batch_id=f"reflection-{checkpoint.version}",
            )
            self._last_summary = ReflectionSummary(
                processed=len(self._processed_with_outcome),
                exported_batch_id=summary["batch_id"],
                export_paths=summary,
                checkpoint_version=checkpoint.version,
            )
            self._processed_with_outcome.clear()
