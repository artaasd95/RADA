"""Load FeedbackRecord / distilled JSONL into chat training examples."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from rada.data.cards.feedback_record import FeedbackRecord

DataSource = Literal["export", "distilled"]


class DistilledManifest(BaseModel):
    name: str
    teacher_model_id: str
    created_at: str
    row_count: int
    schema_version: str = "feedback_record_v1"
    source: str = "colab_distill_teacher"


@dataclass(slots=True)
class ChatExample:
    instruction: str
    input: str
    output: str
    score: float
    metadata: dict[str, Any]


def _record_to_chat(record: FeedbackRecord) -> ChatExample:
    symbol = record.payload.get("symbol", "UNKNOWN")
    actual = record.labels.actual
    if isinstance(actual, dict):
        actual_str = json.dumps(actual)
    else:
        actual_str = str(actual or "")
    instruction = (
        f"Given market context for {symbol}, produce a reflection-aligned decision rationale."
    )
    user_input = json.dumps(
        {
            "symbol": symbol,
            "label_schema": record.label_schema,
            "source": record.source,
        }
    )
    return ChatExample(
        instruction=instruction,
        input=user_input,
        output=actual_str,
        score=record.labels.score,
        metadata={"feedback_id": record.feedback_id},
    )


def load_jsonl_records(path: Path) -> list[FeedbackRecord]:
    records: list[FeedbackRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(FeedbackRecord.model_validate_json(line))
    return records


def load_distilled_manifest(distilled_root: Path, name: str) -> DistilledManifest:
    manifest_path = distilled_root / name / "manifest.json"
    if not manifest_path.exists():
        msg = f"distilled manifest not found: {manifest_path}"
        raise FileNotFoundError(msg)
    return DistilledManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))


def resolve_distilled_path(distilled_root: Path, name: str) -> Path:
    corpus_dir = distilled_root / name
    for candidate in (corpus_dir / "train.jsonl", corpus_dir / "data.jsonl"):
        if candidate.exists():
            return candidate
    msg = f"no distilled JSONL found under {corpus_dir}"
    raise FileNotFoundError(msg)


def default_distilled_root() -> Path:
    import os

    env_root = os.environ.get("RADA_DISTILLED_ROOT")
    if env_root:
        return Path(env_root)
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "data" / "distilled"


def load_training_dataset(
    source: DataSource,
    *,
    data_path: Path | None = None,
    distilled_name: str | None = None,
    distilled_root: Path | None = None,
) -> list[ChatExample]:
    """Load training examples from export or distilled JSONL."""
    if source == "export":
        if data_path is None:
            msg = "data_path required for export data_source"
            raise ValueError(msg)
        records = load_jsonl_records(data_path)
    else:
        if distilled_name is None:
            msg = "distilled_name required for distilled data_source"
            raise ValueError(msg)
        root = distilled_root or default_distilled_root()
        _ = load_distilled_manifest(root, distilled_name)
        path = resolve_distilled_path(root, distilled_name)
        records = load_jsonl_records(path)

    return [_record_to_chat(record) for record in records]


def examples_to_sft_rows(examples: list[ChatExample]) -> list[dict[str, str]]:
    """Format chat examples for TRL/Unsloth SFT."""
    rows: list[dict[str, str]] = []
    for ex in examples:
        text = (
            f"### Instruction:\n{ex.instruction}\n\n"
            f"### Input:\n{ex.input}\n\n"
            f"### Response:\n{ex.output}"
        )
        rows.append({"text": text})
    return rows
