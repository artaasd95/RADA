"""Base vs post-train comparison on shared fixtures."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from rada.backends.stub import StubLLMBackend
from rada.core.decision_loop import DecisionLoop, HoldPolicy, PassThroughRiskOptimizer
from rada.core.reflection_loop import ReflectionLoop, StubAuditor
from rada.data.cards.feedback_record import FeedbackRecord
from rada.data.storage import InMemoryDecisionStore
from rada.schemas import ActionDirection, Decision, DecisionTrace, MarketEvent, ProposedAction
from rada.search.risk_selection import TailWarpStub, select_cvar_feasible_action
from rada.training.config import TrainingConfig
from rada.training.dataset import load_jsonl_records
from rada.training.unsloth_trainer import build_trainer

TrainingMethod = Literal["policy", "reflection"]


@dataclass(slots=True)
class EvalMetrics:
    risk_gate_pass_rate: float
    mean_audit_score: float
    reflection_quality: float
    cases: int = 0

    def to_dict(self) -> dict[str, float | int]:
        return {
            "risk_gate_pass_rate": round(self.risk_gate_pass_rate, 6),
            "mean_audit_score": round(self.mean_audit_score, 6),
            "reflection_quality": round(self.reflection_quality, 6),
            "cases": self.cases,
        }


@dataclass(slots=True)
class PrePostReport:
    model_id: str
    methods: list[str]
    pre: EvalMetrics
    post: EvalMetrics
    delta: dict[str, float] = field(default_factory=dict)
    adapter_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "methods": self.methods,
            "pre": self.pre.to_dict(),
            "post": self.post.to_dict(),
            "delta": {k: round(v, 6) for k, v in self.delta.items()},
            "adapter_path": self.adapter_path,
        }


class TraceReasoner:
    """Reasoner that injects backend completion into DecisionTrace."""

    def __init__(self, backend: StubLLMBackend, *, model_id: str) -> None:
        self._backend = backend
        self._model_id = model_id

    async def reason(self, event: MarketEvent) -> DecisionTrace:
        prompt = f"Analyze {event.symbol} at price {event.price}"
        completion = await self._backend.complete(prompt)
        return DecisionTrace(
            model_name=self._model_id,
            rationale=completion.text,
            faithfulness_score=0.7 if completion.adapter_id else 0.5,
        )


def _feedback_to_event(record: FeedbackRecord, index: int) -> MarketEvent:
    symbol = str(record.payload.get("symbol", "BTCUSD"))
    return MarketEvent(
        symbol=symbol,
        price=1000.0 + index,
        volume=1.0,
        timestamp=datetime(2026, 6, 1, 12, index % 60, tzinfo=UTC),
    )


def _risk_gate_pass_rate(records: list[FeedbackRecord]) -> float:
    if not records:
        return 0.0
    tailwarp = TailWarpStub(cvar_limit=0.05)
    passes = 0
    for index, record in enumerate(records):
        event = _feedback_to_event(record, index)
        candidates = [
            ProposedAction(direction=ActionDirection.BUY, size=1.0),
            ProposedAction(direction=ActionDirection.HOLD, size=0.0),
        ]
        chosen = select_cvar_feasible_action(candidates, price=event.price, tailwarp=tailwarp)
        if chosen is not None:
            passes += 1
    return passes / len(records)


async def _eval_with_backend(
    backend: StubLLMBackend,
    records: list[FeedbackRecord],
    *,
    model_id: str,
) -> EvalMetrics:
    if not records:
        return EvalMetrics(0.0, 0.0, 0.0, 0)

    store = InMemoryDecisionStore()
    reasoner = TraceReasoner(backend, model_id=model_id)
    loop = DecisionLoop(
        reasoner=reasoner,
        policy=HoldPolicy(),
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=store,
    )
    reflection = ReflectionLoop(auditor=StubAuditor())
    decisions: list[Decision] = []

    for index, record in enumerate(records):
        event = _feedback_to_event(record, index)
        decision = await loop.process_one(event)
        decisions.append(decision)
        reflection.enqueue(decision)

    await reflection.drain_all()

    audit_scores = reflection.audit_scores
    mean_audit = sum(audit_scores) / len(audit_scores) if audit_scores else 0.0
    reflection_quality = sum(r.labels.score for r in records) / len(records)
    risk_pass = _risk_gate_pass_rate(records)

    return EvalMetrics(
        risk_gate_pass_rate=risk_pass,
        mean_audit_score=mean_audit,
        reflection_quality=reflection_quality,
        cases=len(records),
    )


def _compute_delta(pre: EvalMetrics, post: EvalMetrics) -> dict[str, float]:
    return {
        "risk_gate_pass_rate": post.risk_gate_pass_rate - pre.risk_gate_pass_rate,
        "mean_audit_score": post.mean_audit_score - pre.mean_audit_score,
        "reflection_quality": post.reflection_quality - pre.reflection_quality,
    }


async def run_pre_post_compare(
    model_id: str,
    fixtures_path: Path,
    *,
    methods: list[TrainingMethod] | None = None,
    adapter_path: Path | None = None,
    output_run_id: str = "pre-post-smoke",
    train: bool = True,
) -> PrePostReport:
    """Run eval on base model, optionally train stub adapter, eval post-train."""
    methods = methods or ["reflection"]
    records = load_jsonl_records(fixtures_path)

    pre_backend = StubLLMBackend(model_id=model_id)
    pre_metrics = await _eval_with_backend(pre_backend, records, model_id=model_id)

    artifact_path = adapter_path
    if train and artifact_path is None:
        config = TrainingConfig(
            model_id=model_id,
            backend="stub",
            data_source="export",
            data_path=fixtures_path,
            output_run_id=output_run_id,
            method=methods[0],
        )
        trainer = build_trainer(config)
        from rada.training.dataset import load_training_dataset

        examples = load_training_dataset("export", data_path=fixtures_path)
        artifact = trainer.train(examples)
        artifact_path = artifact.adapter_path

    post_backend = pre_backend
    if artifact_path is not None:
        post_backend = StubLLMBackend(model_id=model_id).with_lora(artifact_path)

    post_metrics = await _eval_with_backend(post_backend, records, model_id=model_id)
    delta = _compute_delta(pre_metrics, post_metrics)

    return PrePostReport(
        model_id=model_id,
        methods=list(methods),
        pre=pre_metrics,
        post=post_metrics,
        delta=delta,
        adapter_path=str(artifact_path) if artifact_path else None,
    )


def write_report(report: PrePostReport, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
