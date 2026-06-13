from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rada.data.cards.feedback_record import FeedbackLabels, FeedbackProvenance, FeedbackRecord
from rada.training.dataset import load_training_dataset


def _write_feedback(path: Path) -> None:
    record = FeedbackRecord(
        source="auditor",
        target_project="rada",
        target_card="PreferencePair",
        label_schema="outcome_match",
        payload={"symbol": "BTCUSD"},
        provenance=FeedbackProvenance(decision_id="dec-001"),
        labels=FeedbackLabels(score=0.9, actual="HOLD"),
        timestamp=datetime(2026, 6, 1, 12, 0, tzinfo=UTC),
    )
    path.write_text(record.model_dump_json() + "\n", encoding="utf-8")


def test_load_export_dataset(tmp_path: Path) -> None:
    data_path = tmp_path / "feedback.jsonl"
    _write_feedback(data_path)
    examples = load_training_dataset("export", data_path=data_path)
    assert len(examples) == 1
    assert "BTCUSD" in examples[0].instruction


def test_load_distilled_dataset(tmp_path: Path) -> None:
    corpus = tmp_path / "rada-v1"
    corpus.mkdir()
    manifest = {
        "name": "rada-v1",
        "teacher_model_id": "qwen2.5-7b",
        "created_at": "2026-06-07",
        "row_count": 1,
        "schema_version": "feedback_record_v1",
        "source": "colab_distill_teacher",
    }
    (corpus / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _write_feedback(corpus / "train.jsonl")

    examples = load_training_dataset(
        "distilled",
        distilled_name="rada-v1",
        distilled_root=tmp_path,
    )
    assert len(examples) == 1


def test_load_distilled_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_training_dataset("distilled", distilled_name="missing", distilled_root=tmp_path)
