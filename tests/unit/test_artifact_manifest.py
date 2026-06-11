from __future__ import annotations

from pathlib import Path

from rada.utils.artifact_manifest import ArtifactManifest, log_train_eval_manifest


def test_manifest_roundtrip(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RADA_ADAPTER_STORE_ROOT", str(tmp_path))
    path = log_train_eval_manifest(run_id="run-1", model_id="Qwen/Qwen3-0.6B", metrics={"loss": 0.1})
    loaded = ArtifactManifest.load(path)
    assert loaded.run_id == "run-1"
    assert loaded.model_id == "Qwen/Qwen3-0.6B"
