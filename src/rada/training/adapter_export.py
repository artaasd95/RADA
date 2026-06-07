"""PEFT adapter export and RayServe lora_config emission."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rada.backends.base import LoRAConfig
from rada.models.resolver import get_adapter_root
from rada.training.config import TrainingConfig


@dataclass(slots=True)
class AdapterArtifact:
    run_id: str
    model_id: str
    adapter_path: Path
    manifest_path: Path
    lora_config_path: Path


def adapter_output_dir(config: TrainingConfig, *, adapter_root: Path | None = None) -> Path:
    root = adapter_root or get_adapter_root()
    return root / config.output_run_id / config.model_id


def write_training_manifest(
    adapter_dir: Path,
    *,
    config: TrainingConfig,
    adapter_id: str,
    row_count: int,
    extra: dict[str, Any] | None = None,
) -> Path:
    adapter_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "adapter_id": adapter_id,
        "model_id": config.model_id,
        "run_id": config.output_run_id,
        "backend": config.backend,
        "data_source": config.data_source,
        "distilled_name": config.distilled_name,
        "method": config.method,
        "epochs": config.epochs,
        "row_count": row_count,
        "schema_version": "feedback_record_v1",
        "created_at": datetime.now(tz=UTC).isoformat(),
    }
    if extra:
        manifest.update(extra)
    path = adapter_dir / "training_manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def write_lora_config(adapter_dir: Path, *, config: TrainingConfig) -> Path:
    adapter_dir.mkdir(parents=True, exist_ok=True)
    lora = LoRAConfig(
        base_model_id=config.model_id,
        adapter_path=str(adapter_dir),
        rank=config.lora.rank,
        alpha=config.lora.alpha,
        target_modules=list(config.lora.target_modules),
    )
    path = adapter_dir / "lora_config.json"
    path.write_text(lora.model_dump_json(indent=2), encoding="utf-8")
    return path


def write_stub_adapter_files(
    adapter_dir: Path,
    *,
    config: TrainingConfig,
    row_count: int,
) -> AdapterArtifact:
    """Write stub PEFT-compatible artifacts for CI without GPU."""
    adapter_dir.mkdir(parents=True, exist_ok=True)
    adapter_id = f"{config.model_id}-{config.output_run_id}"

    peft_config = {
        "peft_type": "LORA",
        "r": config.lora.rank,
        "lora_alpha": config.lora.alpha,
        "target_modules": config.lora.target_modules,
        "base_model_name_or_path": config.model_id,
    }
    (adapter_dir / "adapter_config.json").write_text(
        json.dumps(peft_config, indent=2),
        encoding="utf-8",
    )
    (adapter_dir / "adapter_model.bin").write_bytes(b"stub")

    manifest_path = write_training_manifest(
        adapter_dir,
        config=config,
        adapter_id=adapter_id,
        row_count=row_count,
    )
    lora_config_path = write_lora_config(adapter_dir, config=config)

    return AdapterArtifact(
        run_id=config.output_run_id,
        model_id=config.model_id,
        adapter_path=adapter_dir,
        manifest_path=manifest_path,
        lora_config_path=lora_config_path,
    )
