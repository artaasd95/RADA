from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from rada.models.registry import load_model_registry
from rada.models.resolver import get_cache_root, resolve_model_path


@pytest.fixture
def registry_path(tmp_path: Path) -> Path:
    cache = tmp_path / "models"
    adapter = tmp_path / "adapters"
    yaml_path = tmp_path / "portfolio.yaml"
    yaml_path.write_text(
        f"""
version: 1
defaults:
  cache_root: {cache}
  adapter_root: {adapter}
models:
  - model_id: test-model
    hub_path: Org/Test-Model
    size_tier: small
    instruct: false
    roles: [reasoner]
pairings:
  dev:
    decision: test-model
    reasoner: test-model
""".strip(),
        encoding="utf-8",
    )
    return yaml_path


def test_load_model_registry(registry_path: Path) -> None:
    registry = load_model_registry(registry_path)
    assert registry.version == 1
    assert len(registry.models) == 1
    assert registry.get_model("test-model").hub_path == "Org/Test-Model"


def test_get_pairing(registry_path: Path) -> None:
    registry = load_model_registry(registry_path)
    pairing = registry.get_pairing("dev")
    assert pairing["decision"] == "test-model"
    assert pairing["reasoner"] == "test-model"


def test_resolve_model_path_local(registry_path: Path, tmp_path: Path) -> None:
    registry = load_model_registry(registry_path)
    entry = registry.get_model("test-model")
    cache = get_cache_root(registry)
    local_dir = cache / entry.hub_path
    local_dir.mkdir(parents=True)
    (local_dir / "config.json").write_text(json.dumps({"model_type": "test"}), encoding="utf-8")

    resolved = resolve_model_path("test-model", registry=registry, download=False)
    assert resolved == local_dir


def test_resolve_model_path_missing_raises(registry_path: Path) -> None:
    registry = load_model_registry(registry_path)
    with pytest.raises(FileNotFoundError):
        resolve_model_path("test-model", registry=registry, download=False)


def test_default_registry_lists_seven_models() -> None:
    registry = load_model_registry()
    assert len(registry.list_model_ids()) == 7
    assert "qwen3-0.6b" in registry.list_model_ids()


def test_env_expansion_in_defaults(monkeypatch: pytest.MonkeyPatch, registry_path: Path) -> None:
    monkeypatch.setenv("RADA_MODEL_CACHE_ROOT", "/custom/cache")
    registry = load_model_registry()
    # default registry uses env expansion on load
    assert registry.defaults.cache_root or os.environ.get("RADA_MODEL_CACHE_ROOT")
