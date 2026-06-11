from __future__ import annotations

from pathlib import Path

import pytest

from rada.llm_integration.factory import create_llm_provider


@pytest.mark.asyncio
async def test_factory_mock_yaml(tmp_path: Path) -> None:
    cfg = tmp_path / "llm.yaml"
    cfg.write_text("provider: mock\nmodel_id: test\n", encoding="utf-8")
    provider = create_llm_provider(cfg)
    out = await provider.complete("ping", "test")
    assert out.model_id == "test"


def test_factory_missing_file() -> None:
    with pytest.raises(FileNotFoundError):
        create_llm_provider("missing.yaml")


def test_factory_unknown_provider(tmp_path: Path) -> None:
    cfg = tmp_path / "bad.yaml"
    cfg.write_text("provider: unknown\nmodel_id: x\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        create_llm_provider(cfg)
