"""Batch reflection export (off hot path)."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from rada.data.cards import DecisionExportRow, FeedbackRecord
from rada.data.pipeline import ExportPipelineRunner, load_pipeline_config
from rada.schemas import Decision

_DEFAULT_CONFIG_NAME = "export.yaml"


def export_decisions(
    decisions: list[Decision],
    *,
    output_dir: Path,
    batch_id: str | None = None,
    config_path: Path | None = None,
) -> dict[str, str]:
    batch_id = batch_id or str(uuid4())[:8]
    output_dir.mkdir(parents=True, exist_ok=True)

    reflection_path = output_dir / "exports" / "reflection" / f"{batch_id}.jsonl"
    feedback_path = output_dir / "feedback" / "outgoing" / f"{batch_id}.jsonl"
    reflection_path.parent.mkdir(parents=True, exist_ok=True)
    feedback_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path is None:
        repo_root = Path(__file__).resolve().parents[3]
        config_path = repo_root / "configs" / "data" / _DEFAULT_CONFIG_NAME

    config = load_pipeline_config(config_path)
    runner = ExportPipelineRunner(config)
    runner.run_batch(decisions)

    with reflection_path.open("w", encoding="utf-8") as reflection_file:
        for decision in decisions:
            row = DecisionExportRow.from_decision(decision, batch_id=batch_id)
            reflection_file.write(row.model_dump_json() + "\n")

    with feedback_path.open("w", encoding="utf-8") as feedback_file:
        for decision in decisions:
            record = FeedbackRecord.from_decision_stub(decision)
            feedback_file.write(record.model_dump_json() + "\n")

    return {
        "batch_id": batch_id,
        "reflection": str(reflection_path),
        "feedback": str(feedback_path),
    }
