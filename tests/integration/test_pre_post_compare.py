from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from rada.evaluation.pre_post_compare import run_pre_post_compare, write_report

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "benchmarks" / "training" / "toy_feedback.jsonl"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pre_post_compare_emits_delta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RADA_ADAPTER_STORE_ROOT", str(tmp_path / "adapters"))

    report = await run_pre_post_compare(
        "qwen3-0.6b",
        FIXTURES,
        output_run_id="compare-smoke",
    )

    assert report.pre.cases == 15
    assert report.post.cases == 15
    assert report.adapter_path is not None
    assert "mean_audit_score" in report.delta
    assert report.post.mean_audit_score >= report.pre.mean_audit_score

    out = tmp_path / "report.json"
    write_report(report, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["model_id"] == "qwen3-0.6b"
    assert "delta" in data


@pytest.mark.integration
def test_compare_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RADA_ADAPTER_STORE_ROOT", str(tmp_path / "adapters"))
    output = tmp_path / "cli_report.json"

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "compare_pre_post_train.py"),
        "--model-id",
        "qwen3-0.6b",
        "--fixtures",
        str(FIXTURES),
        "--output",
        str(output),
    ]
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")}
    result = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    assert result.returncode == 0, result.stderr
    assert output.exists()
    data = json.loads(output.read_text(encoding="utf-8"))
    assert "pre" in data and "post" in data and "delta" in data
