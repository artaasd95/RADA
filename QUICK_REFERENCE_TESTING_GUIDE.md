# RADA Training & Testing - QUICK REFERENCE GUIDE

**Created**: 2026-06-15  
**For**: Initial model evaluation, training, and testing with CUDA + Unsloth  
**Status**: Ready for execution  

---

## 🎯 WHAT WILL HAPPEN (Complete Flow)

### Input → Process → Output

```
Training Data (JSONL)
    ↓
[Load → Transform → Validate]
    ↓
Unsloth Model Loading (CUDA auto-detected)
    ↓
[4-bit quantization → LoRA adapter setup → SFTTrainer]
    ↓
GPU Training (gradient checkpointing, mixed precision)
    ↓
[Checkpoint saving at intervals → Loss tracking]
    ↓
Adapter Artifacts Export
    ↓
[adapter_model.bin + configs → H:\adapters\]
    ↓
Pre/Post Evaluation
    ↓
[Base vs Fine-tuned comparison → Delta metrics]
    ↓
Results Ready
    ↓
[H:\ structure populated with checkpoints, reports, logs]
```

---

## 🚀 QUICK START (5 MINUTES)

### Step 1: Setup Environment
```bash
# Activate environment with CUDA
conda activate rada-cuda
set CUDA_VISIBLE_DEVICES=0
set RADA_ADAPTER_STORE_ROOT=H:\adapters
set RADA_MODEL_CACHE_ROOT=H:\models_cache
```

### Step 2: Run Smoke Test (No GPU Required)
```bash
python -m pytest tests/integration/test_unsloth_reflection_smoke.py::test_reflection_train_stub_produces_adapter -v
```

### Step 3: Run GPU Test (With CUDA)
```bash
python scripts/reflection_train.py \
  --backend unsloth \
  --model-id qwen3-0.6b \
  --data benchmarks/training/toy_feedback.jsonl \
  --epochs 1 \
  --output-run-id test-001
```

### Step 4: Run Evaluation
```bash
python scripts/compare_pre_post_train.py \
  --model-id qwen3-0.6b \
  --adapter-path H:\adapters\test-001\qwen3-0.6b \
  --data benchmarks/training/toy_feedback.jsonl
```

### Step 5: Check Results
```bash
dir H:\adapters\test-001\qwen3-0.6b
dir H:\eval\*.json
```

---

## 📊 TESTING SYSTEM IN 30 SECONDS

| Phase | Time | GPU? | Command | Result |
|-------|------|------|---------|--------|
| **Unit Tests** | <1 min | No | `pytest tests/unit/` | ✓ Components valid |
| **Smoke Tests** | 2 min | No | `pytest tests/integration/test_unsloth_reflection_smoke.py` | ✓ Artifacts created |
| **GPU Test** | 5-10 min | Yes | `python scripts/reflection_train.py --backend unsloth ...` | ✓ Adapter in H:\ |
| **Eval** | 3 min | Yes | `python scripts/compare_pre_post_train.py ...` | ✓ Report generated |
| **Portfolio** | 2-4 hrs | Yes | Multi-model script | ✓ All adapters ready |

---

## 🗂️ WHERE EVERYTHING GOES

### Input Files (Repository)
```
benchmarks/training/toy_feedback.jsonl ← Training data
configs/models/qwen_portfolio.yaml ← Model registry
src/rada/training/*.py ← Training code
tests/integration/test_unsloth_reflection_smoke.py ← Test code
```

### Output Files (H:\ drive)
```
H:\models_cache\          ← Downloaded base models
H:\adapters\              ← Fine-tuned adapters (PEFT)
H:\checkpoints\           ← Training checkpoints (optional)
H:\results\               ← Training summaries (JSON)
H:\eval\                  ← Evaluation reports (JSON)
H:\logs\                  ← Training logs (TXT)
```

---

## 🔧 KEY COMPONENTS & WHAT THEY DO

### 1. **UnslothTrainer** (GPU Training)
- **File**: `src/rada/training/unsloth_trainer.py`
- **Does**: Wraps Unsloth + SFTTrainer for LoRA training
- **CUDA**: Auto-enabled via Unsloth
- **4-bit Quantization**: Built-in
- **Output**: Adapter artifacts in `H:\`

### 2. **Model Registry** (Model Management)
- **File**: `configs/models/qwen_portfolio.yaml`
- **Does**: Registers 7 Qwen models (0.5B–7B)
- **Auto-Download**: From HuggingFace Hub
- **Cache**: Configurable via `RADA_MODEL_CACHE_ROOT`

### 3. **Training Dataset** (Data Pipeline)
- **File**: `src/rada/training/dataset.py`
- **Input**: FeedbackRecord JSONL
- **Output**: ChatExample format for training
- **Schema**: `{instruction, input, output, score, metadata}`

### 4. **Evaluation Engine** (Pre/Post Comparison)
- **File**: `src/rada/evaluation/pre_post_compare.py`
- **Metrics**: 
  - `risk_gate_pass_rate` — CVaR feasibility (%)
  - `mean_audit_score` — Reflection quality
  - `reflection_quality` — Feedback signal strength
- **Output**: Delta report (improvement %)

### 5. **CLI Entry Points** (User Interface)
- **Training**: `scripts/reflection_train.py`
- **Evaluation**: `scripts/compare_pre_post_train.py`
- **Both**: Support all backends (unsloth, stub)

---

## 💾 CHECKPOINT STORAGE EXPLAINED

### Adapter Structure (Final Output)
```
H:\adapters\<run_id>\<model_id>\
├── adapter_model.bin           ← Trained LoRA weights (~5-50 MB)
├── adapter_config.json         ← PEFT configuration (1 KB)
├── lora_config.json           ← Training metadata (2 KB)
├── training_manifest.json     ← Run summary (2 KB)
└── checkpoints\
    ├── checkpoint-100\        ← Intermediate checkpoint
    ├── checkpoint-200\        ← Intermediate checkpoint
    └── checkpoint-final\      ← Final model
```

### What Gets Saved (Per Checkpoint)
```
checkpoint-XXX\
├── adapter_model.bin          ← LoRA weights at step XXX
├── adapter_config.json        ← PEFT config
├── optimizer.pt               ← Optimizer state (for resume)
├── rng_state.pth             ← RNG state (for reproducibility)
└── trainer_state.json        ← Training progress state
```

### Resume Training Flow
```
Original training:    steps 0-100  → checkpoint-100
Resume from 100:      steps 100-200 → checkpoint-200 (can build on checkpoint-100)
Final adapter:        Use latest checkpoint or merge all
```

---

## 🧪 ALL TESTS AT A GLANCE

### Unit Tests (50+)
```bash
pytest tests/unit/ -v
# Validates: config, dataset, registry, calculations, schemas
# GPU Required: NO
# Time: <1 min
```

### Integration Tests (20+)
```bash
pytest tests/integration/ -v
# Validates: CLI, training pipeline, adapter loading, evaluation
# GPU Required: Some (stub backend can run without)
# Time: 5-30 min depending on backend
```

### Key Test Files
```
tests/integration/test_unsloth_reflection_smoke.py
├── test_reflection_train_stub_produces_adapter()     ← No GPU
├── test_stub_backend_loads_adapter()                ← No GPU
└── test_export_then_train_pipeline()                ← No GPU (but tests full flow)

tests/integration/test_distilled_train.py
└── Tests distilled corpus training

tests/integration/test_export_from_db.py
└── Tests FeedbackRecord export pipeline
```

---

## ⚡ CUDA & GPU CONFIGURATION

### Auto-Detection
```python
# Unsloth automatically detects CUDA
import torch
print(torch.cuda.is_available())  # True if CUDA available
print(torch.cuda.get_device_name(0))  # GPU name
```

### Manual Configuration
```bash
# Before running training
set CUDA_VISIBLE_DEVICES=0           # Use GPU 0
set TORCH_CUDA_ARCH_LIST=8.0         # CUDA compute capability
set CUDA_DEVICE_ORDER=PCI_BUS_ID    # Order by PCI ID
```

### If GPU Memory Error (OOM)
```bash
# Reduce batch size
python scripts/reflection_train.py --batch-size 1 ...

# Use smaller model
python scripts/reflection_train.py --model-id qwen2.5-0.5b ...

# Check memory before training
python -c "import torch; print(torch.cuda.get_device_properties(0).total_memory / 1e9, 'GB')"
```

---

## 📈 EVALUATION METRICS EXPLAINED

### `risk_gate_pass_rate` (0-1 or %)
- **What**: % of decisions passing CVaR feasibility filter
- **Meaning**: Higher = better risk-aware decisions
- **Target**: 0.75+ (75% pass rate)
- **Improvement**: Pre=0.65, Post=0.78 → +13% delta

### `mean_audit_score` (0-1)
- **What**: Average reflection quality score from audit loop
- **Meaning**: Higher = better decision rationale quality
- **Target**: 0.80+
- **Improvement**: Pre=0.72, Post=0.85 → +13% delta

### `reflection_quality` (0-1)
- **What**: Feedback signal strength for training
- **Meaning**: Higher = stronger training signal
- **Target**: 0.75+
- **Improvement**: Pre=0.68, Post=0.81 → +13% delta

### Delta (Post - Pre)
- **Target**: >5-10% improvement per metric
- **Success**: All three metrics increase
- **Interpretation**: Training improved model behavior

---

## ✅ EXECUTION CHECKLIST

```
BEFORE RUNNING:
☐ Conda environment activated
☐ CUDA available: python -c "import torch; print(torch.cuda.is_available())"
☐ Dependencies installed: pip list | grep unsloth
☐ H:\ drive accessible and has space (50+ GB recommended)
☐ Training data exists: benchmarks/training/toy_feedback.jsonl
☐ Model cache directory created: H:\models_cache\

DURING TESTING:
☐ Unit tests pass: pytest tests/unit/ -v
☐ Smoke tests pass: pytest tests/integration/test_unsloth_reflection_smoke.py -v
☐ GPU training runs: python scripts/reflection_train.py --backend unsloth ...
☐ Adapters created: ls H:\adapters\*\*\adapter_model.bin
☐ Evaluation runs: python scripts/compare_pre_post_train.py ...
☐ Reports generated: ls H:\eval\*.json

AFTER TESTING:
☐ All adapters in H:\adapters\
☐ All reports in H:\eval\
☐ All logs in H:\logs\
☐ Master summary created
☐ No model files modified (only checkpoints)
☐ Ready for inference/deployment
```

---

## 🚨 COMMON ISSUES & FIXES

| Problem | Solution |
|---------|----------|
| CUDA not found | Install PyTorch with CUDA support: `pip install torch --index-url https://download.pytorch.org/whl/cu118` |
| OOM (Out of Memory) | Reduce batch_size to 1, or use smaller model (0.5B instead of 7B) |
| Adapter not created | Check H:\ permissions, disk space, and output dir setting |
| Tests fail on import | Run from repo root: `cd g:\repositories\RADA` then run tests |
| Model download fails | Check internet connection and HF Hub access; models auto-cache |
| Resume checkpoint invalid | Verify path exists: `dir H:\adapters\<run_id>\<model_id>\checkpoints\checkpoint-XXX` |

---

## 📝 EXECUTION COMMANDS SUMMARY

### 1. Setup (One-Time)
```bash
cd g:\repositories\RADA
conda activate rada-cuda
pip install -e ".[unsloth,dev,notebooks]"
set RADA_ADAPTER_STORE_ROOT=H:\adapters
set CUDA_VISIBLE_DEVICES=0
```

### 2. Unit Tests
```bash
python -m pytest tests/unit/ -v
```

### 3. Smoke Tests (No GPU)
```bash
python -m pytest tests/integration/test_unsloth_reflection_smoke.py -v
```

### 4. GPU Training (Single Model)
```bash
python scripts/reflection_train.py ^
  --backend unsloth ^
  --model-id qwen3-0.6b ^
  --data benchmarks/training/toy_feedback.jsonl ^
  --epochs 3 ^
  --batch-size 2 ^
  --output-run-id training-001
```

### 5. Evaluation
```bash
python scripts/compare_pre_post_train.py ^
  --model-id qwen3-0.6b ^
  --adapter-path H:\adapters\training-001\qwen3-0.6b ^
  --data benchmarks/training/toy_feedback.jsonl
```

### 6. Portfolio Training (All Models)
```bash
for %%M in (qwen3-0.6b qwen2.5-3b qwen2.5-7b) do (
  python scripts/reflection_train.py ^
    --backend unsloth ^
    --model-id %%M ^
    --data benchmarks/training/toy_feedback.jsonl ^
    --epochs 3 ^
    --output-run-id portfolio-001-%%M
)
```

### 7. Verify Results
```bash
dir H:\adapters\
dir H:\eval\
type H:\eval\*.json
```

---

## 📚 ADDITIONAL RESOURCES

- **Full Testing Guide**: See `TESTING_SYSTEM_AND_EXECUTION_FLOW.md`
- **Code Repository**: `g:\repositories\RADA`
- **Training Code**: `src/rada/training/unsloth_trainer.py`
- **Test Suite**: `tests/integration/test_unsloth_reflection_smoke.py`
- **Configuration**: `configs/models/qwen_portfolio.yaml`
- **Model Portfolio**: 7 Qwen models (0.5B–7B)

---

## 🎯 SUCCESS DEFINITION

Your testing is **complete and successful** when:

✅ All unit tests pass  
✅ All integration tests pass (or stub equivalents)  
✅ GPU training creates adapters in `H:\adapters\`  
✅ All adapter files present (adapter_model.bin, configs, manifest)  
✅ Evaluation reports show >5-10% improvement delta  
✅ Training logs show decreasing loss  
✅ Checkpoints saved at specified intervals  
✅ Full results organized in `H:\` drive  
✅ No base models modified (only checkpoints)  
✅ Ready for inference and deployment  

---

**NEXT STEP**: Open `TESTING_SYSTEM_AND_EXECUTION_FLOW.md` for detailed execution guide.
