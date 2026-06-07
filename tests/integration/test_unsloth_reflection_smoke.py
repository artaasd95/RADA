from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rada.backends import StubLLMBackend
from rada.core.decision_loop import DecisionLoop, HoldPolicy, NoOpReasoner, PassThroughRiskOptimizer
from rada.data.cards.feedback_record import FeedbackRecord
from rada.data.export_batch import export_decisions
from rada.data.storage import InMemoryDecisionStore
from rada.schemas import MarketEvent

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "benchmarks" / "training" / "toy_feedback.jsonl"


@pytest.mark.integration
def test_reflection_train_stub_produces_adapter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    adapter_root = tmp_path / "adapters"
    monkeypatch.setenv("RADA_ADAPTER_STORE_ROOT", str(adapter_root))

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "reflection_train.py"),
        "--backend",
        "stub",
        "--model-id",
        "qwen3-0.6b",
        "--data",
        str(FIXTURES),
        "--epochs",
        "1",
        "--output-run-id",
        "smoke-001",
    ]
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    assert result.returncode == 0, result.stderr

    summary = json.loads(result.stdout)
    adapter_dir = Path(summary["adapter_path"])
    assert adapter_dir.exists()
    assert (adapter_dir / "training_manifest.json").exists()
    assert (adapter_dir / "lora_config.json").exists()
    assert (adapter_dir / "adapter_config.json").exists()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_stub_backend_loads_adapter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    adapter_root = tmp_path / "adapters"
    monkeypatch.setenv("RADA_ADAPTER_STORE_ROOT", str(adapter_root))

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "reflection_train.py"),
        "--backend",
        "stub",
        "--model-id",
        "qwen3-0.6b",
        "--data",
        str(FIXTURES),
        "--output-run-id",
        "smoke-002",
    ]
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
    subprocess.run(cmd, check=True, capture_output=True, env=env)

    adapter_dir = adapter_root / "smoke-002" / "qwen3-0.6b"
    backend = StubLLMBackend(model_id="qwen3-0.6b").with_lora(adapter_dir)
    completion = await backend.complete("test prompt")
    assert completion.adapter_id is not None
    assert "qwen3-0.6b" in completion.text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_export_then_train_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    adapter_root = tmp_path / "adapters"
    monkeypatch.setenv("RADA_ADAPTER_STORE_ROOT", str(adapter_root))

    store = InMemoryDecisionStore()
    loop = DecisionLoop(
        reasoner=NoOpReasoner(),
        policy=HoldPolicy(),
        risk_optimizer=PassThroughRiskOptimizer(),
        data_store=store,
    )
    decisions = []
    for index in range(5):
        event = MarketEvent(
            symbol="BTCUSD",
            price=1000.0 + index,
            volume=1.0,
            timestamp=datetime(2026, 6, 1, 12, index, tzinfo=UTC),
        )
        decisions.append(await loop.process_one(event))

    export_dir = tmp_path / "export"
    paths = export_decisions(decisions, output_dir=export_dir, batch_id="pipe")
    feedback_path = Path(paths["feedback"])

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "reflection_train.py"),
        "--backend",
        "stub",
        "--model-id",
        "qwen3-0.6b",
        "--data",
        str(feedback_path),
        "--output-run-id",
        "pipe-001",
    ]
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    assert result.returncode == 0, result.stderr

    records = [
        FeedbackRecord.model_validate_json(line)
        for line in feedback_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(records) == 5
