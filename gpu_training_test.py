#!/usr/bin/env python3
"""GPU training test with Unsloth and Qwen3-0.6B."""

import sys
import json
from pathlib import Path

# Setup paths
REPO_ROOT = Path(__file__).resolve().parent
SRC_ROOT = REPO_ROOT / "src"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(SRC_ROOT))

# Inject asyncpg mock
import asyncpg_mock
sys.modules['asyncpg'] = asyncpg_mock

print("=" * 80)
print("RADA GPU TRAINING TEST - PHASE 2: UNSLOTH BACKEND WITH QWEN3-0.6B")
print("=" * 80)

# Check CUDA availability
import torch
cuda_available = torch.cuda.is_available()
print(f"\nEnvironment Check:")
print(f"  PyTorch version: {torch.__version__}")
print(f"  CUDA available: {cuda_available}")
if cuda_available:
    print(f"  GPU: {torch.cuda.get_device_name(0)}")
    print(f"  GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
else:
    print("  ⚠ CUDA not available - GPU training will use CPU (much slower)")

# Check Unsloth
try:
    from unsloth import FastLanguageModel
    print(f"  ✓ Unsloth available")
except ImportError as e:
    print(f"  ✗ Unsloth not available: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("PHASE 2A: MODEL LOADING TEST (QWEN3-0.6B)")
print("=" * 80)

# Check model cache
model_cache = Path("h:\models_cache")
if model_cache.exists():
    print(f"✓ Model cache exists: {model_cache}")
    qwen_cache = model_cache / "Qwen3-0.6B"
    if qwen_cache.exists():
        print(f"✓ Qwen3-0.6B cached: {qwen_cache}")
    else:
        print(f"✗ Qwen3-0.6B not in cache")
else:
    print(f"✗ Model cache not found: {model_cache}")

print("\n" + "=" * 80)
print("PHASE 2B: IMPORTING RADA MODULES")
print("=" * 80)

try:
    from rada.training.config import TrainingConfig
    from rada.training.dataset import load_training_dataset
    from rada.training.unsloth_trainer import build_trainer
    print("✓ All RADA training modules imported")
except Exception as e:
    print(f"✗ Failed to import modules: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("PHASE 2C: GPU TRAINING WITH UNSLOTH")
print("=" * 80)

# Create training config for GPU
config = TrainingConfig(
    model_id="qwen3-0.6b",
    backend="unsloth",
    data_path=REPO_ROOT / "benchmarks" / "training" / "toy_feedback.jsonl",
    output_run_id="gpu-test-001",
    epochs=1,  # Single epoch for smoke test
    batch_size=2,
)

print(f"Config:")
print(f"  Model: {config.model_id}")
print(f"  Backend: {config.backend}")
print(f"  Epochs: {config.epochs}")
print(f"  Batch Size: {config.batch_size}")
print(f"  LoRA Rank: {config.lora.rank}")

print(f"\nStep 1: Loading dataset...")
try:
    examples = load_training_dataset(
        source="export",
        data_path=config.data_path,
    )
    print(f"✓ Loaded {len(examples)} examples")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

print(f"\nStep 2: Building Unsloth trainer...")
try:
    trainer = build_trainer(config)
    print(f"✓ Trainer type: {type(trainer).__name__}")
except Exception as e:
    print(f"✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"\nStep 3: Starting training...")
print(f"  (This may take several minutes depending on GPU/CPU)")
try:
    artifact = trainer.train(examples)
    print(f"✓ Training completed")
except Exception as e:
    print(f"✗ Training failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print(f"\nStep 4: Verifying adapter artifacts...")
if artifact.adapter_path.exists():
    print(f"✓ Adapter path: {artifact.adapter_path}")
    
    files = {
        "training_manifest.json": artifact.adapter_path / "training_manifest.json",
        "lora_config.json": artifact.adapter_path / "lora_config.json",
        "adapter_config.json": artifact.adapter_path / "adapter_config.json",
        "adapter_model.bin": artifact.adapter_path / "adapter_model.bin",
    }
    
    all_exist = True
    for name, path in files.items():
        if path.exists():
            size = path.stat().st_size
            print(f"  ✓ {name}: {size} bytes")
        else:
            print(f"  ✗ {name}: missing")
            all_exist = False
    
    if not all_exist:
        sys.exit(1)
    
    # Read manifest
    with open(artifact.adapter_path / "training_manifest.json") as f:
        manifest = json.load(f)
    print(f"\nManifest:")
    print(f"  Run ID: {manifest.get('run_id')}")
    print(f"  Model: {manifest.get('model_id')}")
    print(f"  Backend: {manifest.get('backend')}")
    print(f"  Total steps: {manifest.get('total_steps')}")
    print(f"  Final loss: {manifest.get('final_loss', 'N/A')}")
    
else:
    print(f"✗ Adapter path does not exist")
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ GPU TRAINING TEST PASSED")
print("=" * 80)
print(f"\nTraining artifacts:")
print(f"  Location: {artifact.adapter_path}")
print(f"  Run ID: {artifact.run_id}")
print(f"\nNext steps:")
print(f"  - Run evaluation tests")
print(f"  - Compare pre/post metrics")
print(f"  - Test adapter loading and inference")
