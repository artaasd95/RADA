#!/usr/bin/env python3
"""Train reflection/policy LoRA adapters from exported or distilled feedback."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src"
if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))

from rada.training.config import TrainingConfig  # noqa: E402
from rada.training.dataset import load_training_dataset  # noqa: E402
from rada.training.unsloth_trainer import build_trainer  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train LoRA adapters for RADA reflection/policy.")
    parser.add_argument(
        "--backend",
        choices=["unsloth", "stub"],
        default="stub",
        help="Training backend (stub for CI, unsloth for GPU)",
    )
    parser.add_argument("--model-id", required=True, help="Registry model_id")
    parser.add_argument(
        "--data-source",
        choices=["export", "distilled"],
        default="export",
        help="Training data source",
    )
    parser.add_argument("--data", type=Path, default=None, help="Path to export JSONL")
    parser.add_argument("--distilled-name", default=None, help="Distilled corpus name under data/distilled/")
    parser.add_argument(
        "--distilled-root",
        type=Path,
        default=None,
        help="Override distilled corpora root (default: data/distilled or RADA_DISTILLED_ROOT)",
    )
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--output-run-id", default="default")
    parser.add_argument(
        "--method",
        choices=["policy", "reflection"],
        default="reflection",
    )
    parser.add_argument("--lora-rank", type=int, default=16)
    parser.add_argument("--resume-from", default=None, help="Checkpoint path for resume")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    resume_from = args.resume_from or os.environ.get("RADA_RESUME_FROM")
    config = TrainingConfig(
        model_id=args.model_id,
        backend=args.backend,
        data_source=args.data_source,
        data_path=args.data,
        distilled_name=args.distilled_name,
        method=args.method,
        epochs=args.epochs,
        batch_size=args.batch_size,
        output_run_id=args.output_run_id,
        resume_from=resume_from,
        checkpoint_interval=int(os.environ.get("RADA_CHECKPOINT_INTERVAL", "100")),
        checkpoint_keep_last=int(os.environ.get("RADA_CHECKPOINT_KEEP_LAST", "3")),
    )
    config.lora.rank = args.lora_rank

    distilled_root = args.distilled_root
    examples = load_training_dataset(
        config.data_source,
        data_path=config.data_path,
        distilled_name=config.distilled_name,
        distilled_root=distilled_root,
    )
    trainer = build_trainer(config)
    artifact = trainer.train(examples)

    summary = {
        "run_id": artifact.run_id,
        "model_id": artifact.model_id,
        "adapter_path": str(artifact.adapter_path),
        "manifest": str(artifact.manifest_path),
        "lora_config": str(artifact.lora_config_path),
        "rows": len(examples),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
