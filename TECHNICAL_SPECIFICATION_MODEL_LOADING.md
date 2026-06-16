# RADA Model Loading & Training Specification

**Date**: 2026-06-15  
**Purpose**: Technical specification for Unsloth model loading and CUDA execution  
**Audience**: Developers, QA Engineers  

---

## 1. MODEL LOADING FLOW (WITH ACTUAL CODE PATHS)

### 1.1 Complete Model Loading Sequence

```
User Command:
  python scripts/reflection_train.py --backend unsloth --model-id qwen3-0.6b ...

↓

Parse Arguments in reflection_train.py:
  args.model_id = "qwen3-0.6b"
  args.backend = "unsloth"
  args.data = "path/to/feedback.jsonl"

↓

Create TrainingConfig (src/rada/training/config.py):
  config = TrainingConfig(
    model_id="qwen3-0.6b",
    backend="unsloth",
    data_source="export",
    epochs=1,
    batch_size=2,
    max_seq_length=512,
    output_run_id="training-001"
  )

↓

Load Training Dataset (src/rada/training/dataset.py):
  examples = load_training_dataset(
    data_source="export",
    data_path="path/to/feedback.jsonl"
  )
  → Returns: List[ChatExample]
  → Each ChatExample: {instruction, input, output, score, metadata}

↓

Build Trainer (src/rada/training/unsloth_trainer.py):
  trainer = build_trainer(config)
  → Returns: UnslothTrainer instance (GPU) or StubTrainer instance (CI)

↓

UNSLOTH MODEL LOADING (GPU Path):
  
  Step 1: Resolve Model Path
    from rada.models.resolver import resolve_model_path
    base_path = resolve_model_path("qwen3-0.6b")
    → Checks: RADA_MODEL_CACHE_ROOT (e.g., H:\models_cache\)
    → If cached: Returns path to local model
    → If not cached: Downloads from HuggingFace Hub
    → Returns: Path object to local model directory

  Step 2: Load Model with Unsloth
    from unsloth import FastLanguageModel
    
    model, tokenizer = FastLanguageModel.from_pretrained(
      model_name=str(base_path),           # e.g., "H:\models_cache\Qwen3-0.6B"
      max_seq_length=512,                  # Token limit
      dtype=None,                          # Auto-detect (float16/float32)
      load_in_4bit=True                    # ← CUDA QUANTIZATION
    )
    
    At this point:
    - Model loaded on GPU with 4-bit quantization
    - Tokenizer ready for encoding
    - Memory usage: ~2-3 GB for 0.6B model
    - CUDA kernels: Active

  Step 3: Configure PEFT Adapter
    model = FastLanguageModel.get_peft_model(
      model,
      r=16,                                # LoRA rank
      target_modules=["q_proj", "v_proj"], # Trainable modules
      lora_alpha=16,                       # LoRA scaling factor
      lora_dropout=0.0,                    # Dropout in LoRA layers
      bias="none",                         # No bias
      use_gradient_checkpointing="unsloth",# ← MEMORY OPTIMIZATION
      random_state=42                      # Reproducibility
    )
    
    Result:
    - Only 2-3% of model parameters trainable
    - Original model frozen
    - LoRA matrices added to Q and V projections
    - Gradient checkpointing reduces memory by ~50%

  Step 4: Prepare Dataset
    rows = examples_to_sft_rows(examples)
    dataset = Dataset.from_list(rows)
    
    Converts ChatExample → {text: concatenated format}
    Format: "<|im_start|>system\n{instruction}<|im_end|>\n<|im_start|>user\n{input}<|im_end|>\n<|im_start|>assistant\n{output}<|im_end|>"

  Step 5: Setup Training Arguments
    training_args = TrainingArguments(
      output_dir="H:\adapters\training-001\qwen3-0.6b\checkpoints",
      per_device_train_batch_size=2,
      num_train_epochs=1,
      learning_rate=2e-4,
      logging_steps=1,
      save_strategy="steps",
      save_steps=100,                      # Save checkpoint every 100 steps
      save_total_limit=3,                  # Keep last 3 checkpoints
      report_to="none"
    )

  Step 6: Initialize SFTTrainer
    from trl import SFTTrainer
    
    trainer = SFTTrainer(
      model=model,
      tokenizer=tokenizer,
      train_dataset=dataset,
      args=training_args,
      packing=False                        # Don't pack sequences (LoRA training)
    )

↓

TRAINING LOOP (GPU Accelerated):
  
  for epoch in range(1):                   # num_train_epochs=1
    for step, batch in enumerate(dataset):
      # Forward pass (GPU)
      outputs = model(
        input_ids=batch["input_ids"],
        attention_mask=batch["attention_mask"],
        labels=batch["labels"]
      )
      loss = outputs.loss
      
      # Backward pass (GPU, only LoRA gradients)
      loss.backward()
      
      # Gradient accumulation + optimizer step
      optimizer.step()
      optimizer.zero_grad()
      
      # Save checkpoint every 100 steps
      if (step + 1) % 100 == 0:
        trainer.save_model(f"checkpoint-{step+1}")
        # Saves:
        # - adapter_model.bin (LoRA weights)
        # - adapter_config.json (PEFT config)
        # - optimizer.pt (for resume)

↓

ADAPTER EXPORT:
  
  from rada.training.adapter_export import write_lora_config
  
  adapter_dir = Path("H:\adapters\training-001\qwen3-0.6b")
  adapter_dir.mkdir(parents=True, exist_ok=True)
  
  write_lora_config(
    adapter_dir=adapter_dir,
    config=config
  )
  
  Final Output Structure:
  H:\adapters\training-001\qwen3-0.6b\
  ├── adapter_model.bin           ← LoRA weights (trainable %)
  ├── adapter_config.json         ← PEFT metadata
  ├── lora_config.json           ← Training hyperparameters
  ├── training_manifest.json     ← Run summary
  └── checkpoints\
      ├── checkpoint-100\
      │   ├── adapter_model.bin
      │   ├── adapter_config.json
      │   └── optimizer.pt
      ├── checkpoint-200\
      └── checkpoint-300\

↓

SUCCESS: Training complete, adapters ready for inference
```

---

## 2. CUDA EXECUTION DETAILS

### 2.1 CUDA Auto-Detection Chain

```
1. User runs: python scripts/reflection_train.py --backend unsloth ...

2. Import chain:
   reflection_train.py
   → TrainingConfig (pydantic)
   → UnslothTrainer
   → from unsloth import FastLanguageModel
   → unsloth library imports torch

3. Torch CUDA Detection:
   import torch
   torch.cuda.is_available()
   → Checks: NVIDIA drivers, CUDA toolkit, GPU hardware
   → Returns: True if all present

4. Unsloth detects and uses CUDA:
   FastLanguageModel.from_pretrained(..., load_in_4bit=True)
   → Uses CUDA kernels for quantization
   → Allocates GPU memory
   → Offloads model to VRAM

5. Training loop runs on GPU:
   trainer.train()
   → Forward/backward passes on GPU
   → Mixed precision (float16) via Unsloth
   → Gradient accumulation on GPU
   → Checkpoint saving (CPU-side)
```

### 2.2 CUDA Configuration Variables

```bash
# Required
CUDA_VISIBLE_DEVICES=0          # Which GPU to use (0-indexed)

# Optional
CUDA_DEVICE_ORDER=PCI_BUS_ID   # GPU ordering (PCI vs CPU)
CUDA_LAUNCH_BLOCKING=1         # Synchronous (slower, better debugging)
TORCH_CUDA_ARCH_LIST=8.0       # GPU compute capability

# GPU Memory
torch.cuda.empty_cache()        # Clear unused memory (in code)
TORCH_CUDA_MAX_SPLIT_SIZE_MB=512  # Max split size for allocation
```

### 2.3 GPU Memory Profile (Example: Qwen3-0.6B)

```
Without 4-bit quantization:
- Model parameters: ~600M × 4 bytes = 2.4 GB
- Optimizer states (Adam): 2.4 × 2 = 4.8 GB (momentum + variance)
- Activations (batch_size=2): ~1 GB
- Gradients: ~2.4 GB
TOTAL: ~11 GB ← Requires high-end GPU

With Unsloth 4-bit Quantization + Gradient Checkpointing:
- Model parameters: 600M × 0.5 bytes = 300 MB (4-bit)
- LoRA only: ~16 × 2 matrices × 600M / 2000 = ~10 MB
- Optimizer states: ~20 MB
- Activations (recomputed): ~200 MB
TOTAL: ~600 MB ← Fits on consumer GPUs (RTX 3060, 4060)
```

### 2.4 Actual CUDA Function Calls (In Code)

**File**: `src/rada/training/unsloth_trainer.py` (Lines ~60-90)

```python
# Step 1: Model loading (Unsloth handles CUDA)
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=str(base_path),
    max_seq_length=self.config.max_seq_length,
    dtype=None,
    load_in_4bit=True,  # ← CUDA: torch.cuda.is_available() checked here
)
# Internally calls:
#   → quantize_4bit() on CUDA tensors
#   → model.cuda() or model.to(device)

# Step 2: PEFT model (Still on GPU)
model = FastLanguageModel.get_peft_model(
    model,
    r=self.config.lora.rank,
    target_modules=self.config.lora.target_modules,
    lora_alpha=self.config.lora.alpha,
    lora_dropout=self.config.lora.dropout,
    bias="none",
    use_gradient_checkpointing="unsloth",  # ← CUDA memory optimization
    random_state=42,
)
# Internally calls:
#   → get_peft_model() from peft library
#   → torch.nn.init on GPU
#   → Sets up backward hooks

# Step 3: Training (All on GPU)
trainer.train()
# Internally calls:
#   → Forward pass: model(input_ids.cuda(), attention_mask.cuda(), labels.cuda())
#   → loss.backward() with GPU gradients
#   → Optimizer step on GPU
#   → torch.cuda.synchronize() after each batch
```

---

## 3. ACTUAL CODE PATHS FOR MODELS

### 3.1 Model Resolution (From Registry)

**File**: `src/rada/models/resolver.py`

```python
def resolve_model_path(model_id: str) -> Path:
    """Resolve model_id to local path or download."""
    
    # Step 1: Check registry
    registry = ModelRegistry.from_yaml(PORTFOLIO_CONFIG)
    model_entry = registry.get_model(model_id)  # e.g., "qwen3-0.6b"
    
    # Step 2: Resolve cache root (env override)
    cache_root = Path(
        os.environ.get("RADA_MODEL_CACHE_ROOT", "~/.cache/rada/models")
    ).expanduser()
    
    # Step 3: Check local cache
    local_path = cache_root / model_entry.cache_dir_name
    if local_path.exists():
        return local_path  # Cache hit
    
    # Step 4: Download if not cached
    from huggingface_hub import snapshot_download
    local_path = snapshot_download(
        repo_id=model_entry.hub_path,  # e.g., "Qwen/Qwen3-0.6B"
        cache_dir=str(cache_root)
    )
    return Path(local_path)
```

**File**: `configs/models/qwen_portfolio.yaml`

```yaml
models:
  - id: "qwen3-0.6b"
    hub_path: "Qwen/Qwen3-0.6B"
    cache_dir_name: "Qwen3-0.6B"
    size_gb: 2.4
    quantization: "fp16"
    context_length: 512
    
  - id: "qwen2.5-3b"
    hub_path: "Qwen/Qwen2.5-3B"
    cache_dir_name: "Qwen2.5-3B"
    size_gb: 6.0
    quantization: "fp16"
    context_length: 1024
```

### 3.2 Dataset Loading (JSONL → Training Format)

**File**: `src/rada/training/dataset.py`

```python
def load_training_dataset(
    data_source: str = "export",
    data_path: Path | None = None,
    distilled_name: str | None = None
) -> list[ChatExample]:
    """Load training examples from JSONL or distilled corpus."""
    
    if data_source == "export":
        # Load from JSONL
        records = load_jsonl_records(data_path)
        # records: List[FeedbackRecord]
        
        examples = []
        for record in records:
            example = ChatExample(
                instruction=f"Given {record.payload['symbol']}, produce rationale",
                input=json.dumps({
                    "symbol": record.payload["symbol"],
                    "label_schema": record.label_schema,
                    "source": record.source
                }),
                output=json.dumps(record.labels.actual),
                score=record.labels.score,
                metadata={"feedback_id": record.feedback_id}
            )
            examples.append(example)
        return examples
    
    elif data_source == "distilled":
        # Load from distilled corpus
        manifest_path = resolve_distilled_manifest(distilled_name)
        data_file = manifest_path.parent / "train.jsonl"
        return [ChatExample(**row) for row in load_jsonl_records(data_file)]
```

### 3.3 Adapter Export (Final Output)

**File**: `src/rada/training/adapter_export.py`

```python
def write_lora_config(adapter_dir: Path, config: TrainingConfig) -> None:
    """Write LoRA configuration to adapter directory."""
    
    lora_config = {
        "base_model_id": config.model_id,
        "adapter_rank": config.lora.rank,
        "adapter_alpha": config.lora.alpha,
        "target_modules": config.lora.target_modules,
        "lora_dropout": config.lora.dropout,
        "quantization": "4bit",
        "max_seq_length": config.max_seq_length,
        "training_method": config.method,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    with open(adapter_dir / "lora_config.json", "w") as f:
        json.dump(lora_config, f, indent=2)


def write_training_manifest(
    adapter_dir: Path,
    config: TrainingConfig,
    trainer: SFTTrainer
) -> None:
    """Write training run summary."""
    
    manifest = {
        "run_id": config.output_run_id,
        "model_id": config.model_id,
        "adapter_path": str(adapter_dir),
        "backend": config.backend,
        "rows_trained": len(trainer.train_dataset),
        "epochs": config.epochs,
        "batch_size": config.batch_size,
        "learning_rate": config.learning_rate,
        "final_loss": trainer.state.log_history[-1]["loss"],
        "training_duration_seconds": trainer.state.total_flos,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    with open(adapter_dir / "training_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
```

---

## 4. TESTING FLOW WITH ACTUAL CODE

### 4.1 Stub Trainer (CI Tests - No GPU)

**File**: `src/rada/training/unsloth_trainer.py` (Lines ~20-35)

```python
class StubTrainer:
    """CI-friendly trainer that emits adapter artifacts without GPU deps."""
    
    def __init__(self, config: TrainingConfig) -> None:
        self.config = config
    
    def train(self, examples: list[ChatExample]) -> AdapterArtifact:
        # No GPU used, no actual training
        adapter_dir = adapter_output_dir(self.config)
        
        # Create dummy artifacts with correct structure
        return write_stub_adapter_files(
            adapter_dir,
            config=self.config,
            row_count=len(examples),
        )
        # Returns: AdapterArtifact with paths to created files
```

**Use Case**: CI/CD pipelines, local development without GPU

### 4.2 Smoke Test Execution

**File**: `tests/integration/test_unsloth_reflection_smoke.py` (Lines ~17-50)

```python
@pytest.mark.integration
def test_reflection_train_stub_produces_adapter(tmp_path: Path) -> None:
    """Test: JSONL → Stub trainer → adapter artifacts"""
    
    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "reflection_train.py"),
        "--backend", "stub",
        "--model-id", "qwen3-0.6b",
        "--data", str(FIXTURES),
        "--epochs", "1",
        "--output-run-id", "smoke-001",
    ]
    
    # Execute CLI as subprocess (validates full flow)
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    # Parse JSON output
    summary = json.loads(result.stdout)
    
    # Verify adapter artifacts exist
    adapter_dir = Path(summary["adapter_path"])
    assert adapter_dir.exists()
    assert (adapter_dir / "training_manifest.json").exists()
    assert (adapter_dir / "lora_config.json").exists()
    assert (adapter_dir / "adapter_config.json").exists()
    
    # ✓ Test passes if files present and valid JSON
```

**Execution**:
```bash
pytest tests/integration/test_unsloth_reflection_smoke.py::test_reflection_train_stub_produces_adapter -v
```

### 4.3 GPU Test Execution (With Unsloth)

```bash
python scripts/reflection_train.py \
  --backend unsloth \
  --model-id qwen3-0.6b \
  --data benchmarks/training/toy_feedback.jsonl \
  --epochs 1 \
  --batch-size 2 \
  --output-run-id smoke-gpu-001
```

**Expected Output**:
```json
{
  "run_id": "smoke-gpu-001",
  "model_id": "qwen3-0.6b",
  "adapter_path": "H:\\adapters\\smoke-gpu-001\\qwen3-0.6b",
  "manifest": "H:\\adapters\\smoke-gpu-001\\qwen3-0.6b\\training_manifest.json",
  "lora_config": "H:\\adapters\\smoke-gpu-001\\qwen3-0.6b\\lora_config.json",
  "rows": 10
}
```

### 4.4 Evaluation Test

```python
# Pre-training metrics (base model)
pre_metrics = evaluate_model(base_model, dataset)
# {risk_gate_pass_rate: 0.65, mean_audit_score: 0.72, reflection_quality: 0.68}

# Post-training metrics (with adapter)
post_metrics = evaluate_model(base_model.with_lora(adapter_path), dataset)
# {risk_gate_pass_rate: 0.78, mean_audit_score: 0.85, reflection_quality: 0.81}

# Delta calculation
delta = {
    "risk_gate_pass_rate": (0.78 - 0.65) / 0.65 * 100,  # +20%
    "mean_audit_score": (0.85 - 0.72) / 0.72 * 100,      # +18%
    "reflection_quality": (0.81 - 0.68) / 0.68 * 100     # +19%
}
```

---

## 5. CHECKPOINT RESUMPTION FLOW

### 5.1 Resume Training Command

```bash
python scripts/reflection_train.py \
  --backend unsloth \
  --model-id qwen3-0.6b \
  --data benchmarks/training/toy_feedback.jsonl \
  --epochs 3 \
  --output-run-id training-001-resume \
  --resume-from H:\adapters\training-001\qwen3-0.6b\checkpoints\checkpoint-100
```

### 5.2 Resume Flow (In Code)

**File**: `src/rada/training/unsloth_trainer.py`

```python
training_args = TrainingArguments(
    output_dir=str(adapter_dir / "checkpoints"),
    resume_from_checkpoint=self.config.resume_from,  # ← Checkpoint path
    ...
)

trainer = SFTTrainer(..., args=training_args)
trainer.train()  # Internally:
                 # 1. Loads checkpoint-100/adapter_model.bin
                 # 2. Loads checkpoint-100/optimizer.pt
                 # 3. Loads checkpoint-100/trainer_state.json
                 # 4. Resumes from step 100
                 # 5. Continues to step 300 (if 3 epochs)
```

### 5.3 Output After Resume

```
H:\adapters\training-001-resume\qwen3-0.6b\
├── checkpoints\
│   ├── checkpoint-100\        ← Loaded from original
│   ├── checkpoint-200\        ← Generated in resume session
│   ├── checkpoint-300\        ← Generated in resume session
│   └── checkpoint-final\      ← Final merged adapter
├── adapter_model.bin          ← Latest weights
├── adapter_config.json
├── lora_config.json
└── training_manifest.json     ← Shows total_steps=300, resumed=true
```

---

## 6. MODEL REGISTRY & AUTO-DOWNLOAD

### 6.1 First-Time Model Download

```
User runs:
  python scripts/reflection_train.py --model-id qwen3-0.6b ...

UnslothTrainer.train() calls:
  base_path = resolve_model_path("qwen3-0.6b")

resolve_model_path() executes:
  1. Check registry: qwen3-0.6b → Qwen/Qwen3-0.6B
  2. Check cache: H:\models_cache\Qwen3-0.6B\
     → If exists: return path (cache hit, 0s)
     → If not: download (first-time, 2-5 min for 0.6B model)
  3. snapshot_download() from huggingface_hub:
     - Downloads: config.json, model.safetensors, tokenizer.json, etc.
     - Saves to: H:\models_cache\Qwen3-0.6B\
     - Size: ~1.5 GB for 0.6B model

FastLanguageModel.from_pretrained() loads:
  model = FastLanguageModel.from_pretrained(
    model_name="H:\models_cache\Qwen3-0.6B",
    load_in_4bit=True
  )
  → Quantizes model to 4-bit on GPU
  → Ready for LoRA training
```

### 6.2 Model Registry File

**File**: `configs/models/qwen_portfolio.yaml`

```yaml
models:
  - id: qwen3-0.6b
    hub_path: Qwen/Qwen3-0.6B
    cache_dir_name: Qwen3-0.6B
    description: Small, fast reasoner model
    
  - id: qwen2.5-3b
    hub_path: Qwen/Qwen2.5-3B
    cache_dir_name: Qwen2.5-3B
    description: Medium decision model
    
  - id: qwen2.5-7b
    hub_path: Qwen/Qwen2.5-7B
    cache_dir_name: Qwen2.5-7B
    description: Large teacher model
```

---

## 7. COMPLETE EXECUTION TRACE EXAMPLE

### 7.1 Step-by-Step Trace: Training qwen3-0.6b

```
[1] User input:
    python scripts/reflection_train.py --backend unsloth --model-id qwen3-0.6b \
      --data benchmarks/training/toy_feedback.jsonl --epochs 1 --output-run-id test-001

[2] Parse arguments (reflection_train.py):
    args.model_id = "qwen3-0.6b"
    args.backend = "unsloth"
    args.data = "benchmarks/training/toy_feedback.jsonl"
    args.epochs = 1
    args.output_run_id = "test-001"

[3] Create config (training/config.py):
    config.model_id = "qwen3-0.6b"
    config.backend = "unsloth"
    config.epochs = 1
    config.batch_size = 2
    config.max_seq_length = 512

[4] Load training data (training/dataset.py):
    Load benchmarks/training/toy_feedback.jsonl (10 FeedbackRecords)
    Convert to ChatExample format (10 examples)

[5] Build trainer (unsloth_trainer.py):
    Since backend == "unsloth":
      → Create UnslothTrainer instance

[6] Training phase:
    
    6a. Resolve model path (models/resolver.py):
        registry.get_model("qwen3-0.6b")
        → hub_path = "Qwen/Qwen3-0.6B"
        cache_path = H:\models_cache\Qwen3-0.6B\
        if cache_path exists: return cache_path (cache hit)
        else: download from Qwen/Qwen3-0.6B (~1.5 GB, 2-3 min)
    
    6b. Load model with Unsloth:
        FastLanguageModel.from_pretrained(
          model_name="H:\models_cache\Qwen3-0.6B",
          load_in_4bit=True,  # ← CUDA 4-bit quantization
          max_seq_length=512
        )
        GPU Memory: 0.3 GB (quantized)
    
    6c. Get PEFT model:
        FastLanguageModel.get_peft_model(
          r=16, target_modules=["q_proj", "v_proj"],
          lora_alpha=16, use_gradient_checkpointing="unsloth"
        )
        GPU Memory: +0.01 GB (LoRA parameters)
        Total: ~0.3 GB
    
    6d. Prepare dataset:
        rows = examples_to_sft_rows(10 ChatExamples)
        dataset = Dataset.from_list(rows)
    
    6e. Setup training:
        TrainingArguments(
          output_dir="H:\adapters\test-001\qwen3-0.6b\checkpoints",
          per_device_train_batch_size=2,
          num_train_epochs=1,
          learning_rate=2e-4,
          save_steps=100,
          logging_steps=1
        )
    
    6f. Create SFTTrainer:
        trainer = SFTTrainer(
          model=model,
          tokenizer=tokenizer,
          train_dataset=dataset,
          args=training_args
        )
    
    6g. Training loop (GPU):
        Epoch 0:
          Step 1: loss=2.341 (GPU)
          Step 2: loss=2.102 (GPU)
          ...
          Step 10: loss=0.832 (GPU)
        
        After epoch:
          Save checkpoint: H:\adapters\test-001\qwen3-0.6b\checkpoints\checkpoint-final\

[7] Export adapters (adapter_export.py):
    write_lora_config()
    write_training_manifest()
    Final structure:
      H:\adapters\test-001\qwen3-0.6b\
      ├── adapter_model.bin
      ├── adapter_config.json
      ├── lora_config.json
      ├── training_manifest.json
      └── checkpoints\
          └── checkpoint-final\

[8] Return result (reflection_train.py):
    print(json.dumps({
      "run_id": "test-001",
      "model_id": "qwen3-0.6b",
      "adapter_path": "H:\\adapters\\test-001\\qwen3-0.6b",
      "manifest": "H:\\adapters\\test-001\\qwen3-0.6b\\training_manifest.json",
      "lora_config": "H:\\adapters\\test-001\\qwen3-0.6b\\lora_config.json",
      "rows": 10
    }))

[9] Verification:
    ✓ H:\adapters\test-001\qwen3-0.6b\ exists
    ✓ adapter_model.bin exists (~10 MB)
    ✓ adapter_config.json exists
    ✓ lora_config.json exists
    ✓ training_manifest.json exists
    ✓ Training complete, ready for inference
```

---

## 8. DEPENDENCIES & INSTALLATION

### 8.1 Required Packages (pyproject.toml)

```toml
[project.optional-dependencies]
unsloth = [
  "unsloth",
  "torch>=2.2.0",              # PyTorch with CUDA support
  "transformers>=4.40.0",      # Model definitions
  "peft>=0.10.0",              # PEFT adapter framework
  "trl>=0.8.0",                # Trainer library (SFTTrainer)
  "datasets>=2.18.0",          # Dataset utilities
  "accelerate>=0.28.0",        # Distributed training (multi-GPU)
  "huggingface_hub>=0.22.0"    # Model downloading
]
```

### 8.2 Installation with CUDA

```bash
# 1. Install PyTorch with CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 2. Install RADA with Unsloth
pip install -e ".[unsloth,dev]"

# 3. Verify CUDA
python -c "import torch; print(torch.cuda.is_available())"  # Should print: True
```

---

## 9. ERROR HANDLING & RECOVERY

### 9.1 Common Errors & Fixes

| Error | Line | Cause | Fix |
|-------|------|-------|-----|
| `ImportError: No module named 'unsloth'` | unsloth_trainer.py:48 | Unsloth not installed | `pip install -e ".[unsloth]"` |
| `torch.cuda.OutOfMemoryError` | Training loop | VRAM insufficient | `--batch-size 1` or smaller model |
| `FileNotFoundError: model path` | resolver.py:25 | Model not cached or downloaded | Check internet, retry download |
| `AssertionError: adapter_dir.exists()` | test line:45 | Output dir not created | Check disk permissions, `H:\` access |
| `ValueError: training requires at least one example` | unsloth_trainer.py:55 | No data loaded | Verify JSONL path and format |

### 9.2 Recovery Procedures

**Case 1: Out of Memory (OOM)**
```bash
# Option A: Reduce batch size
python scripts/reflection_train.py --batch-size 1 ...

# Option B: Use smaller model
python scripts/reflection_train.py --model-id qwen2.5-0.5b ...

# Option C: Clear GPU cache (in Python)
import torch
torch.cuda.empty_cache()
```

**Case 2: Resume from checkpoint after crash**
```bash
# Find last successful checkpoint
dir H:\adapters\training-001\qwen3-0.6b\checkpoints

# Resume from that checkpoint
python scripts/reflection_train.py \
  --resume-from H:\adapters\training-001\qwen3-0.6b\checkpoints\checkpoint-100 \
  --epochs 5
```

**Case 3: Model download timeout**
```bash
# Manually download via huggingface-cli
huggingface-cli download Qwen/Qwen3-0.6B --cache-dir H:\models_cache

# Then run training (will use cached model)
python scripts/reflection_train.py --model-id qwen3-0.6b ...
```

---

**END OF TECHNICAL SPECIFICATION**
