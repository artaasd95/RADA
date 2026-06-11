"""Manifest-driven artifact layout for adapters, eval exports, and training runs."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def adapter_store_root() -> Path:
    """Canonical root: RADA_ADAPTER_STORE_ROOT or experiments/adapters."""
    env = os.environ.get("RADA_ADAPTER_STORE_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return Path("experiments/adapters").resolve()


def eval_export_root() -> Path:
    return adapter_store_root().parent / "eval_exports"


@dataclass
class ArtifactManifest:
    """Structured record for train/eval artifact bundles."""

    run_id: str
    project: str = "rada"
    model_id: str = ""
    adapter_path: str = ""
    eval_export_path: str = ""
    commit_sha: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metrics: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)

    def write(self, root: Path | None = None) -> Path:
        root = root or adapter_store_root()
        root.mkdir(parents=True, exist_ok=True)
        out = root / self.run_id / "manifest.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        return out

    @classmethod
    def load(cls, path: Path) -> ArtifactManifest:
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(**data)


def log_train_eval_manifest(
    *,
    run_id: str,
    model_id: str,
    metrics: dict[str, Any] | None = None,
    adapter_path: str | Path | None = None,
    eval_export_path: str | Path | None = None,
) -> Path:
    """Emit structured manifest next to runtime observability exports."""
    manifest = ArtifactManifest(
        run_id=run_id,
        model_id=model_id,
        adapter_path=str(adapter_path) if adapter_path else "",
        eval_export_path=str(eval_export_path) if eval_export_path else "",
        commit_sha=os.environ.get("GIT_COMMIT_SHA", ""),
        metrics=metrics or {},
    )
    return manifest.write()
