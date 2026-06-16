#!/usr/bin/env python3
"""Smoke test with asyncpg mocking for offline testing."""

import sys
import json
from pathlib import Path

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(REPO_ROOT))  # Allow local asyncpg_mock import
sys.path.insert(0, str(SRC_ROOT))

# Inject asyncpg mock BEFORE any RADA imports
import asyncpg_mock
sys.modules['asyncpg'] = asyncpg_mock

print("=" * 80)
print("RADA SMOKE TEST - PHASE 1: STUB BACKEND TRAINING")
print("=" * 80)
print(f"Repository Root: {REPO_ROOT}")
print(f"Testing with Qwen3-0.6B (Lightest Model)")
print()

# Now try imports after mock is in place
try:
    from rada.training.config import TrainingConfig
    print("✓ TrainingConfig imported successfully")
except Exception as e:
    print(f"✗ Failed to import TrainingConfig: {e}")
    sys.exit(1)

try:
    from rada.training.dataset import load_training_dataset, ChatExample
    print("✓ load_training_dataset imported successfully")
except Exception as e:
    print(f"✗ Failed to import load_training_dataset: {e}")
    sys.exit(1)

try:
    from rada.training.unsloth_trainer import build_trainer
    print("✓ build_trainer imported successfully")
except Exception as e:
    print(f"✗ Failed to import build_trainer: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("VERIFYING TEST DATA")
print("=" * 80)

data_file = REPO_ROOT / "benchmarks" / "training" / "toy_feedback.jsonl"
if data_file.exists():
    file_size = data_file.stat().st_size
    print(f"✓ Test data exists: {data_file.name} ({file_size} bytes)")
    
    # Count lines
    with open(data_file) as f:
        lines = len(f.readlines())
    print(f"  - Contains {lines} records")
else:
    print(f"✗ Test data not found: {data_file}")
    sys.exit(1)

print("\n" + "=" * 80)
print("TEST SCENARIO 1: STUB BACKEND (NO GPU)")
print("=" * 80)

# Test configuration
config = TrainingConfig(
    model_id="qwen3-0.6b",
    backend="stub",
    data_path=data_file,
    output_run_id="smoke-test-001",
    epochs=1,
    batch_size=2,
)

print(f"Config created:")
print(f"  Model ID: {config.model_id}")
print(f"  Backend: {config.backend}")
print(f"  Epochs: {config.epochs}")
print(f"  Batch Size: {config.batch_size}")
print(f"  Output Run ID: {config.output_run_id}")
print(f"  LoRA Rank: {config.lora.rank}")

print("\nStep 1: Loading training dataset...")
try:
    examples = load_training_dataset(
        source="export",
        data_path=config.data_path,
    )
    print(f"✓ Loaded {len(examples)} training examples")
    if len(examples) > 0:
        print(f"  Example 0 keys: {examples[0].__dict__.keys() if hasattr(examples[0], '__dict__') else examples[0].keys() if isinstance(examples[0], dict) else 'Unknown'}")
except Exception as e:
    print(f"✗ Failed to load dataset: {e}")
    sys.exit(1)

print("\nStep 2: Building trainer (stub backend)...")
try:
    trainer = build_trainer(config)
    print(f"✓ Trainer built: {type(trainer).__name__}")
except Exception as e:
    print(f"✗ Failed to build trainer: {e}")
    sys.exit(1)

print("\nStep 3: Training...")
try:
    artifact = trainer.train(examples)
    print(f"✓ Training completed")
    print(f"  Adapter path: {artifact.adapter_path}")
    print(f"  Run ID: {artifact.run_id}")
    print(f"  Model ID: {artifact.model_id}")
except Exception as e:
    print(f"✗ Training failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\nStep 4: Verifying outputs...")
if artifact.adapter_path.exists():
    print(f"✓ Adapter directory exists: {artifact.adapter_path}")
    
    # Check for required files
    required_files = [
        "training_manifest.json",
        "lora_config.json",
        "adapter_config.json",
        "adapter_model.bin"
    ]
    
    missing = []
    for fname in required_files:
        fpath = artifact.adapter_path / fname
        if fpath.exists():
            size = fpath.stat().st_size
            print(f"  ✓ {fname} ({size} bytes)")
        else:
            print(f"  ✗ {fname} (missing)")
            missing.append(fname)
    
    if missing:
        print(f"\n✗ Missing files: {missing}")
        sys.exit(1)
else:
    print(f"✗ Adapter directory does not exist: {artifact.adapter_path}")
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ SMOKE TEST PASSED")
print("=" * 80)
print(f"\nTraining artifacts saved to:")
print(f"  {artifact.adapter_path}")
print(f"\nReady for next tests (GPU training, evaluation)")
