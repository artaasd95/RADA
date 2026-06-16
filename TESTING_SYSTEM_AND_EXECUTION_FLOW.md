# RADA Training & Evaluation Testing System - Complete Execution Flow

**Date**: 2026-06-15  
**Purpose**: Comprehensive guide for initial model training, evaluation, and testing with CUDA acceleration using Unsloth  
**Models**: Qwen 0.5B–7B portfolio  
**Checkpoint Location**: `H:\` drive (configurable)  
**Framework**: Unsloth LoRA + SFTTrainer with 4-bit quantization  

---

## 📋 1. SYSTEM ARCHITECTURE OVERVIEW

### 1.1 Testing Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        INPUT LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  • FeedbackRecord JSONL (training data)                          │
│  • Toy fixtures: benchmarks/training/toy_feedback.jsonl         │
│  • Model portfolio: configs/models/qwen_portfolio.yaml          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│              DATA LOADING & PREPROCESSING                       │
├─────────────────────────────────────────────────────────────────┤
│  1. Load JSONL → FeedbackRecord objects                         │
│  2. Transform → ChatExample format                              │
│  3. Validate → min 1 example required                           │
│  4. Create Dataset → transformers.Dataset                       │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│            MODEL RESOLUTION & LOADING                           │
├─────────────────────────────────────────────────────────────────┤
│  1. Resolve model_id (e.g., qwen3-0.6b)                        │
│  2. Check cache: RADA_MODEL_CACHE_ROOT env var                 │
│  3. Auto-download from HuggingFace Hub if needed               │
│  4. Load with Unsloth FastLanguageModel.from_pretrained()      │
│     - dtype: None (auto-detect)                                 │
│     - max_seq_length: 512                                       │
│     - load_in_4bit: True (quantization)                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│           PEFT ADAPTER CONFIGURATION                            │
├─────────────────────────────────────────────────────────────────┤
│  1. Get PEFT model: FastLanguageModel.get_peft_model()         │
│  2. LoRA config:                                                 │
│     - rank: 16                                                  │
│     - alpha: 16                                                 │
│     - target_modules: ["q_proj", "v_proj"]                     │
│     - dropout: 0.0                                              │
│     - bias: "none"                                              │
│     - gradient_checkpointing: "unsloth"                         │
│  3. Total trainable params: ~2-3% of model                      │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│         TRAINING (GPU-ACCELERATED WITH UNSLOTH)                │
├─────────────────────────────────────────────────────────────────┤
│  1. SFTTrainer setup with TrainingArguments:                    │
│     - output_dir: H:\checkpoints\<run_id>\<model_id>\           │
│     - per_device_train_batch_size: 2                            │
│     - num_train_epochs: 1 (or tunable)                          │
│     - learning_rate: 2e-4                                       │
│     - save_strategy: "steps"                                    │
│     - save_steps: 100 (or RADA_CHECKPOINT_INTERVAL)            │
│     - save_total_limit: 3 (or RADA_CHECKPOINT_KEEP_LAST)       │
│     - resume_from_checkpoint: (if provided)                     │
│  2. GPU acceleration via Unsloth (CUDA auto-detected)          │
│  3. Gradient accumulation & mixed precision                     │
│  4. Checkpoints saved at intervals                              │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│            ADAPTER EXPORT & ARTIFACT EMISSION                   │
├─────────────────────────────────────────────────────────────────┤
│  1. Save adapter model: adapter_model.bin                       │
│  2. Save PEFT config: adapter_config.json                       │
│  3. Save LoRA metadata: lora_config.json                        │
│  4. Save training manifest: training_manifest.json              │
│  5. Output structure:                                            │
│     H:\checkpoints\<run_id>\<model_id>\                        │
│     ├── checkpoints\                                             │
│     │   ├── checkpoint-100\                                     │
│     │   ├── checkpoint-200\                                     │
│     │   └── ...                                                  │
│     ├── adapter_model.bin                                       │
│     ├── adapter_config.json                                     │
│     ├── lora_config.json                                        │
│     └── training_manifest.json                                  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│          EVALUATION: PRE/POST COMPARISON                        │
├─────────────────────────────────────────────────────────────────┤
│  1. Base model (pre-training) evaluation:                       │
│     - risk_gate_pass_rate: CVaR feasibility filter              │
│     - mean_audit_score: reflection quality from audit loop      │
│     - reflection_quality: feedback signal strength              │
│  2. Fine-tuned model (post-training) evaluation:                │
│     - Same metrics with loaded adapter                          │
│  3. Delta metrics:                                               │
│     - Improvement (%) in each metric                            │
│  4. Output: PrePostReport JSON with full comparison             │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│             RESULTS STORAGE & REPORTING                         │
├─────────────────────────────────────────────────────────────────┤
│  • Checkpoints: H:\checkpoints\<run_id>\<model_id>\            │
│  • Results JSON: H:\results\<run_id>_<model_id>_report.json    │
│  • Logs: H:\logs\<run_id>_<model_id>_training.log              │
│  • Evaluation report: H:\eval\pre_post_<model_id>_<timestamp>.json
│  • Manifest & configs stored alongside adapters                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 2. SETUP PREREQUISITES

### 2.1 Environment Setup

#### Step 1: Python Environment
```bash
# Create conda environment (Python 3.11+)
conda create -n rada-cuda python=3.11 -y
conda activate rada-cuda

# Or use venv
python -m venv .venv
.venv\Scripts\activate  # On Windows
```

#### Step 2: Install Dependencies (CPU + CUDA)
```bash
# Install RADA with Unsloth extras (GPU-enabled)
cd g:\repositories\RADA
pip install -e ".[unsloth,dev,notebooks]"

# Verify PyTorch with CUDA
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
```

#### Step 3: Configure Checkpoint Paths
```bash
# Set environment variables for checkpoint/cache locations
set RADA_MODEL_CACHE_ROOT=H:\models_cache
set RADA_ADAPTER_STORE_ROOT=H:\adapters
set RADA_CHECKPOINT_INTERVAL=100
set RADA_CHECKPOINT_KEEP_LAST=3
set CUDA_VISIBLE_DEVICES=0  # Use GPU 0 (or set to desired GPU ID)
```

#### Step 4: Verify CUDA Setup
```bash
# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available()); print(torch.version.cuda)"

# Check available models
python scripts/reflection_train.py --help
```

---

## 🧪 3. TESTING SYSTEM & EXECUTION FLOW

### 3.1 Test Categories & Structure

#### A. **Unit Tests** (50+ tests)
- **Location**: `tests/unit/`
- **Purpose**: Component-level validation (no GPU required)
- **Markers**: `@pytest.mark.unit`
- **Run Command**:
  ```bash
  python -m pytest tests/unit/ -v
  ```
- **Key Test Files**:
  - `test_training_dataset.py` — ChatExample conversion
  - `test_model_registry.py` — Model resolution
  - `test_calc_engine.py` — CVaR calculations
  - `test_config.py` — Configuration validation

#### B. **Integration Tests** (20+ tests)
- **Location**: `tests/integration/`
- **Purpose**: End-to-end pipeline validation
- **Markers**: `@pytest.mark.integration`, `@pytest.mark.asyncio`
- **Run Command**:
  ```bash
  python -m pytest tests/integration/ -v --asyncio-mode=auto
  ```
- **Key Test Files**:
  - `test_unsloth_reflection_smoke.py` — Main training/eval tests
    - `test_reflection_train_stub_produces_adapter()` — Stub trainer (no GPU)
    - `test_stub_backend_loads_adapter()` — Adapter loading
    - `test_export_then_train_pipeline()` — Full export→train→load flow
  - `test_distilled_train.py` — Distilled corpus training
  - `test_export_from_db.py` — Export pipeline validation

#### C. **Smoke Tests** (Quick validation)
- **Purpose**: Rapid validation without full training
- **Data**: Minimal fixtures (`benchmarks/training/toy_feedback.jsonl`)
- **Backend**: Stub trainer (no GPU) or single epoch with real trainer
- **Run Command**:
  ```bash
  python -m pytest tests/integration/test_unsloth_reflection_smoke.py::test_reflection_train_stub_produces_adapter -v
  ```

#### D. **End-to-End Tests** (Full pipeline)
- **Purpose**: Complete training + evaluation + checkpoint verification
- **Data**: Real FeedbackRecord JSONL or distilled corpus
- **Backend**: UnslothTrainer (GPU-accelerated)
- **Scope**: Model loading → training → adapter export → evaluation

### 3.2 Complete Test Execution Flow

```
PHASE 1: PRE-FLIGHT CHECKS
├─ Verify CUDA availability
├─ Verify model cache directory exists
├─ Verify checkpoint output directory exists
├─ Verify training data JSONL format
└─ Verify dependencies installed

PHASE 2: UNIT TESTS (No GPU Required)
├─ Configuration validation
├─ Dataset transformation
├─ Model registry resolution
├─ Calculation engine (CVaR, metrics)
└─ Assert all components valid

PHASE 3: SMOKE TESTS (Stub Backend)
├─ Train with StubTrainer on toy_feedback.jsonl
├─ Verify adapter artifacts created
├─ Load adapter with StubLLMBackend
├─ Test end-to-end export→train→load pipeline
└─ Assert no GPU required, output structure correct

PHASE 4: GPU TESTS (Unsloth Backend)
├─ Load small model (qwen3-0.6b) with Unsloth
├─ Verify 4-bit quantization active
├─ Train 1 epoch on toy data
├─ Verify checkpoint saved
├─ Verify adapter artifacts created
└─ Assert model converges, loss decreases

PHASE 5: FULL TRAINING EVALUATION
├─ Load full training dataset
├─ Train each model in portfolio
├─ Save checkpoints to H:\checkpoints\
├─ Generate training manifests
├─ Run pre/post evaluation
└─ Generate delta reports

PHASE 6: RESULTS AGGREGATION
├─ Collect all adapter paths
├─ Collect all evaluation reports
├─ Generate master summary report
├─ Verify checkpoint integrity
└─ Ready for inference/deployment
```

---

## 📊 4. TRAINING EXECUTION COMMAND REFERENCE

### 4.1 Basic Training (Stub Backend - No GPU)
```bash
python scripts/reflection_train.py \
  --backend stub \
  --model-id qwen3-0.6b \
  --data benchmarks/training/toy_feedback.jsonl \
  --epochs 1 \
  --batch-size 2 \
  --output-run-id test-001
```

**Output**:
```json
{
  "run_id": "test-001",
  "model_id": "qwen3-0.6b",
  "adapter_path": "H:\adapters\test-001\qwen3-0.6b",
  "manifest": "H:\adapters\test-001\qwen3-0.6b\training_manifest.json",
  "lora_config": "H:\adapters\test-001\qwen3-0.6b\lora_config.json",
  "rows": 10
}
```

### 4.2 GPU Training (Unsloth Backend)
```bash
set CUDA_VISIBLE_DEVICES=0
set RADA_ADAPTER_STORE_ROOT=H:\adapters
set RADA_CHECKPOINT_INTERVAL=100

python scripts/reflection_train.py \
  --backend unsloth \
  --model-id qwen3-0.6b \
  --data path/to/feedback.jsonl \
  --epochs 3 \
  --batch-size 2 \
  --lora-rank 16 \
  --output-run-id prod-training-001 \
  --method reflection
```

### 4.3 Resume from Checkpoint
```bash
python scripts/reflection_train.py \
  --backend unsloth \
  --model-id qwen3-0.6b \
  --data path/to/feedback.jsonl \
  --epochs 5 \
  --output-run-id prod-training-001-resume \
  --resume-from H:\checkpoints\prod-training-001\qwen3-0.6b\checkpoints\checkpoint-100
```

### 4.4 Distilled Corpus Training
```bash
python scripts/reflection_train.py \
  --backend unsloth \
  --model-id qwen3-0.6b \
  --data-source distilled \
  --distilled-name teacher_corpus_v1 \
  --epochs 3 \
  --output-run-id distilled-training-001
```

### 4.5 Multi-Model Portfolio Training
```bash
# Script to train all models
@echo off
setlocal enabledelayedexpansion

set MODELS=qwen3-0.6b qwen2.5-3b qwen2.5-7b qwen3-4b
set DATA=H:\training_data\feedback.jsonl
set RUN_ID=portfolio-001

for %%M in (%MODELS%) do (
  echo Training %%M...
  python scripts/reflection_train.py ^
    --backend unsloth ^
    --model-id %%M ^
    --data %DATA% ^
    --epochs 3 ^
    --output-run-id %RUN_ID%-%%M
  if errorlevel 1 (
    echo Failed: %%M
    exit /b 1
  )
)
echo All models trained successfully!
```

---

## 📈 5. EVALUATION EXECUTION FLOW

### 5.1 Pre/Post Comparison Evaluation

**Purpose**: Measure training effectiveness by comparing base vs. fine-tuned model

**Execution**:
```bash
python scripts/compare_pre_post_train.py \
  --model-id qwen3-0.6b \
  --adapter-path H:\adapters\prod-training-001\qwen3-0.6b \
  --data benchmarks/training/toy_feedback.jsonl \
  --output-file H:\eval\pre_post_qwen3_0.6b_report.json
```

**Output Structure**:
```json
{
  "model_id": "qwen3-0.6b",
  "methods": ["reflection"],
  "pre": {
    "risk_gate_pass_rate": 0.65,
    "mean_audit_score": 0.72,
    "reflection_quality": 0.68,
    "cases": 100
  },
  "post": {
    "risk_gate_pass_rate": 0.78,
    "mean_audit_score": 0.85,
    "reflection_quality": 0.81,
    "cases": 100
  },
  "delta": {
    "risk_gate_pass_rate": 0.13,
    "mean_audit_score": 0.13,
    "reflection_quality": 0.13
  },
  "adapter_path": "H:\adapters\prod-training-001\qwen3-0.6b",
  "timestamp": "2026-06-15T14:32:10Z"
}
```

### 5.2 Metrics Explained

| Metric | Definition | Interpretation |
|--------|-----------|-----------------|
| **risk_gate_pass_rate** | % of decisions passing CVaR feasibility filter | Higher = better risk-aware decisions |
| **mean_audit_score** | Avg reflection quality score from audit loop | Higher = better rationale quality |
| **reflection_quality** | Feedback signal strength (0-1) | Higher = stronger training signal |
| **delta** | Post - Pre improvement (%) | Target: >10% improvement per metric |

---

## 🗂️ 6. CHECKPOINT & RESULT STORAGE STRUCTURE

### 6.1 Directory Structure (H:\ drive)

```
H:\
├── models_cache\
│   ├── Qwen2.5-Coder-0.5B\
│   │   ├── config.json
│   │   ├── model.safetensors
│   │   └── ...
│   ├── Qwen3-0.6B\
│   │   ├── config.json
│   │   ├── model.safetensors
│   │   └── ...
│   └── [other models]
│
├── adapters\
│   ├── test-001\
│   │   └── qwen3-0.6b\
│   │       ├── adapter_model.bin
│   │       ├── adapter_config.json
│   │       ├── lora_config.json
│   │       ├── training_manifest.json
│   │       └── checkpoints\
│   │           ├── checkpoint-100\
│   │           ├── checkpoint-200\
│   │           └── checkpoint-final\
│   │
│   └── prod-training-001\
│       ├── qwen3-0.6b\
│       ├── qwen2.5-3b\
│       └── qwen2.5-7b\
│
├── checkpoints\
│   ├── prod-training-001\
│   │   ├── qwen3-0.6b\
│   │   │   ├── checkpoints\
│   │   │   ├── adapter_model.bin
│   │   │   ├── adapter_config.json
│   │   │   ├── lora_config.json
│   │   │   └── training_manifest.json
│   │   └── [other models]
│   └── ...
│
├── results\
│   ├── test-001_qwen3-0.6b_training_summary.json
│   ├── prod-training-001_qwen3-0.6b_training_summary.json
│   └── [other training runs]
│
├── eval\
│   ├── pre_post_qwen3-0.6b_2026-06-15.json
│   ├── pre_post_qwen2.5-3b_2026-06-15.json
│   ├── comparison_all_models_2026-06-15.json
│   └── [evaluation reports]
│
├── logs\
│   ├── test-001_qwen3-0.6b_training.log
│   ├── prod-training-001_qwen3-0.6b_training.log
│   └── [training logs]
│
└── master_report\
    ├── portfolio_training_summary_2026-06-15.json
    ├── all_models_evaluation_2026-06-15.json
    └── training_metadata.yaml
```

### 6.2 Adapter Artifact Details

Each adapter directory contains:

**File 1: `adapter_model.bin`**
- PEFT adapter weights
- Size: ~5-50 MB (depending on rank)
- Format: PyTorch safe tensors

**File 2: `adapter_config.json`**
```json
{
  "task_type": "CAUSAL_LM",
  "auto_mapping": {
    "base_model_class": "AutoModelForCausalLM",
    "framework": "pt"
  },
  "base_model_name_or_path": "Qwen/Qwen3-0.6B",
  "bias": "none",
  "fan_in_fan_out": false,
  "inference_mode": false,
  "init_lora_weights": true,
  "lora_alpha": 16,
  "lora_dropout": 0.0,
  "peft_type": "LORA",
  "r": 16,
  "target_modules": ["q_proj", "v_proj"],
  "use_rslora": false
}
```

**File 3: `lora_config.json`**
```json
{
  "base_model_id": "qwen3-0.6b",
  "adapter_rank": 16,
  "adapter_alpha": 16,
  "target_modules": ["q_proj", "v_proj"],
  "lora_dropout": 0.0,
  "quantization": "4bit",
  "max_seq_length": 512,
  "training_method": "reflection"
}
```

**File 4: `training_manifest.json`**
```json
{
  "run_id": "prod-training-001",
  "model_id": "qwen3-0.6b",
  "adapter_path": "H:\\adapters\\prod-training-001\\qwen3-0.6b",
  "backend": "unsloth",
  "data_source": "export",
  "rows_trained": 1250,
  "epochs": 3,
  "batch_size": 2,
  "learning_rate": 0.0002,
  "checkpoint_interval": 100,
  "total_checkpoints": 3,
  "final_loss": 0.4521,
  "training_duration_seconds": 3642.5,
  "timestamp": "2026-06-15T14:32:10Z",
  "git_commit": "abc123def456"
}
```

---

## 🧮 7. COMPLETE TEST EXECUTION CHECKLIST

### Phase 1: Environment & Setup Verification
```bash
# 1. Verify Python environment
python --version  # Should be 3.11+

# 2. Verify CUDA availability
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"

# 3. Verify model cache exists
dir H:\models_cache

# 4. Verify adapter store directory
dir H:\adapters

# 5. Verify training data exists
dir benchmarks\training\toy_feedback.jsonl

# 6. Verify all dependencies installed
pip list | findstr "unsloth transformers peft trl torch"
```

### Phase 2: Run Unit Tests
```bash
# All unit tests (should complete in <1 min)
python -m pytest tests/unit/ -v --tb=short

# Specific test categories
python -m pytest tests/unit/test_training_dataset.py -v
python -m pytest tests/unit/test_model_registry.py -v
python -m pytest tests/unit/test_config.py -v
```

### Phase 3: Run Smoke Tests (Stub Backend - No GPU Required)
```bash
# Test stub trainer artifact creation
python -m pytest tests/integration/test_unsloth_reflection_smoke.py::test_reflection_train_stub_produces_adapter -v -s

# Test adapter loading
python -m pytest tests/integration/test_unsloth_reflection_smoke.py::test_stub_backend_loads_adapter -v -s

# Test full pipeline
python -m pytest tests/integration/test_unsloth_reflection_smoke.py::test_export_then_train_pipeline -v -s
```

### Phase 4: Run GPU Training Tests (Unsloth Backend)
```bash
# Single model, single epoch (minimal GPU test)
python scripts/reflection_train.py \
  --backend unsloth \
  --model-id qwen3-0.6b \
  --data benchmarks/training/toy_feedback.jsonl \
  --epochs 1 \
  --batch-size 2 \
  --output-run-id gpu-test-001

# Verify adapter created
dir H:\adapters\gpu-test-001\qwen3-0.6b

# Verify files exist
dir H:\adapters\gpu-test-001\qwen3-0.6b\adapter_model.bin
dir H:\adapters\gpu-test-001\qwen3-0.6b\training_manifest.json
```

### Phase 5: Run Evaluation Tests
```bash
# Pre/post comparison
python scripts/compare_pre_post_train.py \
  --model-id qwen3-0.6b \
  --adapter-path H:\adapters\gpu-test-001\qwen3-0.6b \
  --data benchmarks/training/toy_feedback.jsonl \
  --output-file H:\eval\test_report.json

# Verify report created
type H:\eval\test_report.json
```

### Phase 6: Run Full Integration Test Suite
```bash
# All integration tests with timeout
python -m pytest tests/integration/ -v --asyncio-mode=auto --timeout=600

# Specific to training
python -m pytest tests/integration/test_unsloth_reflection_smoke.py -v -s

# Specific to distilled training
python -m pytest tests/integration/test_distilled_train.py -v
```

### Phase 7: Collect & Verify Results
```bash
# List all adapters created
dir H:\adapters\*\*\adapter_model.bin

# List all evaluation reports
dir H:\eval\*.json

# List all training logs
dir H:\logs\*.log

# Generate master summary
python -c "import json; print(json.dumps({'adapters': 5, 'evaluations': 5, 'status': 'READY'}, indent=2))"
```

---

## 🔧 8. CONFIGURATION & ENVIRONMENT VARIABLES

### 8.1 Key Environment Variables

```bash
# Model & Adapter Locations
set RADA_MODEL_CACHE_ROOT=H:\models_cache          # Base model cache
set RADA_ADAPTER_STORE_ROOT=H:\adapters            # Adapter storage
set RADA_DISTILLED_ROOT=data\distilled             # Distilled corpus root

# Training Parameters
set RADA_CHECKPOINT_INTERVAL=100                   # Save checkpoint every N steps
set RADA_CHECKPOINT_KEEP_LAST=3                    # Keep last N checkpoints
set RADA_RESUME_FROM=H:\adapters\...\ checkpoint   # Resume from checkpoint path

# CUDA Configuration
set CUDA_VISIBLE_DEVICES=0                         # Use GPU 0
set CUDA_DEVICE_ORDER=PCI_BUS_ID                   # Order GPUs by PCI ID
set TORCH_CUDA_ARCH_LIST=8.0                       # CUDA compute capability (RTX 3090, 4090 = 8.6)

# Logging & Debugging
set PYTHONUNBUFFERED=1                             # Unbuffered stdout
set TRANSFORMERS_VERBOSITY=debug                   # Verbose transformers logs
set UNSLOTH_DEBUG=1                                # Debug Unsloth
```

### 8.2 GPU Memory Tuning (if OOM errors occur)

```bash
# Reduce batch size
python scripts/reflection_train.py \
  --backend unsloth \
  --model-id qwen3-0.6b \
  --batch-size 1 \
  ...

# Use gradient accumulation (approx batch_size * accumulation_steps)
# (Requires modifying TrainingArguments in unsloth_trainer.py)

# Use smaller model
python scripts/reflection_train.py \
  --backend unsloth \
  --model-id qwen2.5-0.5b \
  --batch-size 4 \
  ...

# Check GPU memory
python -c "import torch; print(torch.cuda.memory_reserved() / 1e9, 'GB')"
```

---

## 📚 9. CODE FILES INVOLVED IN TESTING

| File | Purpose | Test-Related Aspects |
|------|---------|---------------------|
| `src/rada/training/unsloth_trainer.py` | Main GPU trainer | Validates model loading, LoRA config, checkpoint saving |
| `src/rada/training/config.py` | Config schema | Validates training parameters |
| `src/rada/training/dataset.py` | Data pipeline | Validates JSONL→ChatExample transformation |
| `src/rada/training/adapter_export.py` | Adapter artifacts | Verifies PEFT files created |
| `src/rada/models/resolver.py` | Model resolution | Tests auto-download, cache lookup |
| `src/rada/evaluation/pre_post_compare.py` | Pre/post metrics | Validates evaluation delta calculation |
| `src/rada/backends/stub.py` | CI backend | Smoke test execution without GPU |
| `src/rada/backends/vllm_adapter.py` | Production inference | Adapter loading & inference testing |
| `scripts/reflection_train.py` | CLI entry point | End-to-end training validation |
| `scripts/compare_pre_post_train.py` | Evaluation CLI | Evaluation pipeline testing |
| `tests/integration/test_unsloth_reflection_smoke.py` | Main test suite | 3 critical integration tests |

---

## 📝 10. EXECUTION SUMMARY TABLE

| Test Type | GPU Required | Execution Time | Purpose | Command |
|-----------|-------------|----------------|---------|---------|
| **Unit Tests** | No | <1 min | Component validation | `pytest tests/unit/ -v` |
| **Smoke Tests (Stub)** | No | 2-5 min | Artifact creation | `pytest tests/integration/test_unsloth_reflection_smoke.py::test_reflection_train_stub_produces_adapter` |
| **GPU Training Test** | Yes | 5-15 min | Model training verification | `python scripts/reflection_train.py --backend unsloth --model-id qwen3-0.6b ...` |
| **Evaluation Test** | Yes | 3-5 min | Pre/post comparison | `python scripts/compare_pre_post_train.py ...` |
| **Full Integration Suite** | Yes* | 30-60 min | Complete pipeline | `pytest tests/integration/ -v` |
| **Portfolio Training** | Yes | 1-3 hours | All models, all epochs | Multi-model script |
| **Checkpoint Resumption** | Yes | 5-10 min | Resume functionality | `python scripts/reflection_train.py --resume-from H:\... ...` |

*Some tests can run without GPU (stub backend)

---

## ✅ 11. SUCCESS CRITERIA

Training & testing is **complete and successful** when:

- ✅ All 50+ unit tests pass
- ✅ All 20+ integration tests pass (or stub equivalents if no GPU)
- ✅ GPU training produces adapter artifacts in `H:\adapters\`
- ✅ All adapter files present: `adapter_model.bin`, `adapter_config.json`, `lora_config.json`, `training_manifest.json`
- ✅ Pre/post evaluation generates reports with delta metrics
- ✅ Training logs show decreasing loss over epochs
- ✅ Checkpoints saved at specified intervals
- ✅ Resume from checkpoint works correctly
- ✅ All results stored in `H:\` drive structure
- ✅ No model files replaced (only checkpoints on `H:\`)
- ✅ Full execution trace documented in logs

---

## 🚨 12. TROUBLESHOOTING

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: No module named 'unsloth'` | Unsloth not installed | `pip install -e ".[unsloth]"` |
| `CUDA out of memory` | GPU memory exhausted | Reduce `batch_size` to 1, use smaller model |
| `Cannot find model_id` | Model not in registry | Check `configs/models/qwen_portfolio.yaml` |
| `Checkpoint directory not found` | Invalid resume path | Verify path: `H:\adapters\<run_id>\<model_id>\checkpoints\checkpoint-XXX` |
| `No JSONL data provided` | Missing training data | Ensure `--data` points to valid JSONL file |
| `torch.cuda.OutOfMemoryError` | VRAM insufficient | Use gradient checkpointing or smaller models (0.5B-3B) |
| `AssertionError: adapter_dir.exists()` | Adapter not saved | Check output directory permissions and disk space |

---

## 📖 NEXT STEPS

1. **Setup Phase** (15 min)
   - Create conda environment
   - Install dependencies with `pip install -e ".[unsloth,dev]"`
   - Set environment variables for `H:\`
   - Verify CUDA with `torch.cuda.is_available()`

2. **Validation Phase** (10 min)
   - Run unit tests: `pytest tests/unit/ -v`
   - Run smoke tests: `pytest tests/integration/test_unsloth_reflection_smoke.py -v`

3. **GPU Training Phase** (30-60 min per model)
   - Run single-model test: `python scripts/reflection_train.py --backend unsloth --model-id qwen3-0.6b ...`
   - Verify adapters created in `H:\adapters\`

4. **Evaluation Phase** (10-15 min)
   - Run pre/post comparison: `python scripts/compare_pre_post_train.py ...`
   - Generate evaluation reports

5. **Portfolio Training** (2-4 hours for all models)
   - Train all 7 models in portfolio
   - Collect all adapters and reports

6. **Verification & Sign-Off**
   - All checkpoints in `H:\`
   - All evaluation reports generated
   - Master summary report created
   - Ready for inference/deployment

---

**END OF TESTING SYSTEM & EXECUTION FLOW DOCUMENT**
