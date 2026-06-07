from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.integration
def test_reflection_train_distilled_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RADA_ADAPTER_STORE_ROOT", str(tmp_path / "adapters"))

    distilled_root = tmp_path / "distilled"
    corpus = distilled_root / "rada-v1"
    corpus.mkdir(parents=True)
    manifest = {
        "name": "rada-v1",
        "teacher_model_id": "qwen2.5-7b",
        "created_at": "2026-06-07",
        "row_count": 1,
        "schema_version": "feedback_record_v1",
        "source": "colab_distill_teacher",
    }
    (corpus / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    fixture = REPO_ROOT / "benchmarks" / "training" / "toy_feedback.jsonl"
    (corpus / "train.jsonl").write_text(
        fixture.read_text(encoding="utf-8").splitlines()[0] + "\n",
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "reflection_train.py"),
        "--backend",
        "stub",
        "--model-id",
        "qwen2.5-3b",
        "--data-source",
        "distilled",
        "--distilled-name",
        "rada-v1",
        "--distilled-root",
        str(distilled_root),
        "--output-run-id",
        "distill-smoke",
    ]
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
    monkeypatch.setenv("PYTHONPATH", str(REPO_ROOT / "src"))
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    assert result.returncode == 0, result.stderr + result.stdout
