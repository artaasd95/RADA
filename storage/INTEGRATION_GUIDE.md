# RADA S3 Storage System - Complete Integration Guide

Complete guide to using the S3 download/upload system for RADA on RunPod.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        RunPod GPU Pod                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Pod Storage (~40GB)              Network Volume (~95GB)        │
│  ┌──────────────────┐            ┌──────────────────┐           │
│  │ Active Training  │            │ Persistent       │           │
│  │ • Current models │            │ Backups          │           │
│  │ • Data (fast I/O)│            │ • Old runs       │           │
│  │ • Temp files     │            │ • Archives       │           │
│  └──────────────────┘            └──────────────────┘           │
│           ▲                                △                     │
│           │                                │                     │
│           └────────────┬───────────────────┘                     │
│                        │                                          │
│            ┌───────────▼──────────┐                              │
│            │   S3 Uploader Daemon │  (background)              │
│            │  - Monitors run_*/   │  (tmux session)            │
│            │  - Detects changes   │  (every 30s)               │
│            │  - Compresses text   │                             │
│            │  - Uploads to S3     │                             │
│            └───────────┬──────────┘                              │
│                        │                                          │
└────────────────────────┼──────────────────────────────────────────┘
                         │
                         ▼
            ┌─────────────────────────┐
            │   S3 Bucket             │ (Unlimited)
            │  • models/              │
            │  • metrics/             │
            │  • reports/             │
            │  • logs/                │
            │  • ablations/           │
            └─────────────────────────┘
```

## Complete Workflow

### Phase 1: Preparation (First Time)

```bash
# 1a. SSH into RunPod
ssh -i ~/.ssh/runpod_key root@<pod-ip>
cd /workspace/RADA

# 1b. Install S3 tools (one-time)
bash runpod/setup_s3.sh

# 1c. Configure S3 credentials
cp .env.s3.example .env.s3
nano .env.s3
# Fill in S3 endpoint, bucket, credentials

# 1d. Test S3 connection
source .env.s3
python storage/s3_uploader.py \
  --endpoint "$S3_ENDPOINT" \
  --access-key "$S3_ACCESS_KEY" \
  --secret-key "$S3_SECRET_KEY" \
  --bucket "$S3_BUCKET" \
  --dry-run --run-once
```

### Phase 2: Training Run

```bash
# 2a. Load environment
source .env.s3

# 2b. Start orchestration (handles everything)
bash runpod/orchestrate_training.sh llm_single_gpu --epochs 50
```

**What happens automatically:**
1. Creates `runs/run_YYYYMMDD_HHMMSS/` directory
2. Starts S3 uploader daemon (background tmux session)
3. Downloads data from S3 (if configured)
4. Runs training
5. Training saves outputs:
   - `models/` → checkpoints
   - `metrics/` → eval results
   - `reports/` → reports
   - `logs/` → training logs
6. Uploader daemon detects files every 30s and uploads new/changed ones
7. Text files are auto-gzipped (80-95% compression)
8. After training, runs final upload pass

### Phase 3: Monitoring (In Separate Terminals)

```bash
# Terminal 1: Training progress
# (already running, check output)

# Terminal 2: Monitor upload daemon
tail -f storage/logs/s3_uploader.log

# Terminal 3: Check disk usage
watch bash runpod/disk_manager.sh status

# Terminal 4: GPU utilization
watch nvidia-smi
```

### Phase 4: Results Collection (After Training)

```bash
# All files are automatically uploaded during training
# Download to local machine:

# On local machine (not on RunPod):
mkdir -p /tmp/rada-results
cd /tmp/rada-results

# List what's in S3
s3cmd ls s3://my-rada-results/RADA/

# Download models
s3cmd get s3://my-rada-results/RADA/models/ ./ --recursive

# Download metrics
s3cmd get s3://my-rada-results/RADA/metrics/ ./ --recursive
```

## File Structure & Paths

### Local Structure (RunPod Pod Storage)

```
/workspace/RADA/
├── data/
│   ├── [Downloaded datasets - optional]
│   └── └─ large_dataset.tar.gz (~20-30GB)
│
├── runs/                                    # Monitored by uploader
│   ├── run_20250601_120000/                # Auto-created
│   │   ├── models/                        # Checkpoints (~1-5GB)
│   │   │   ├── checkpoint_epoch_001.pt
│   │   │   ├── checkpoint_epoch_010.pt
│   │   │   └── model_final.pt
│   │   ├── metrics/                       # Eval results (~100MB)
│   │   │   ├── metrics_epoch_001.json.gz # Auto-compressed
│   │   │   ├── metrics_epoch_010.json.gz
│   │   │   └── final_metrics.json.gz
│   │   ├── reports/                       # Reports (~10MB)
│   │   │   └── summary.json
│   │   ├── logs/                          # Training logs (~100MB)
│   │   │   ├── training.log.gz            # Auto-compressed
│   │   │   └── debug.log.gz               # Auto-compressed
│   │   └── config.yaml                    # Config reference
│   │
│   ├── run_20250601_140000/
│   │   └── [Same structure]
│   │
│   └── ablations/
│       ├── ablation_01.json.gz
│       └── ablation_02.json.gz
│
├── storage/
│   ├── logs/
│   │   ├── s3_uploader.log               # Daemon logs
│   │   ├── s3_uploader_state.json        # State tracking
│   │   └── .tmp_compress/                # Temporary files
│   ├── s3_uploader.py                    # Upload script
│   ├── requirements.txt
│   ├── README_S3.md
│   ├── orchestrators/
│   │   └── start_s3_uploader.sh
│   └── ...
│
├── scripts/
│   └── download_data.sh                  # Data downloader
│
├── runpod/
│   ├── setup_s3.sh                       # S3 setup
│   ├── orchestrate_training.sh           # Main orchestration
│   ├── disk_manager.sh                   # Disk cleanup
│   ├── QUICK_START.md
│   └── ...
│
├── src/
│   └── rada/
│       ├── training/
│       │   ├── train.py                  # Your training script
│       │   └── train_example.py          # Integration example
│       └── ...
│
├── .env.s3.example                       # Template
└── .env.s3                               # Your credentials (created)
```

### S3 Bucket Structure

```
s3://my-rada-results/
└── RADA/                                 # S3_PROJECT_PREFIX
    ├── models/
    │   ├── run_20250601_120000/
    │   │   ├── checkpoint_epoch_001.pt
    │   │   ├── checkpoint_epoch_010.pt
    │   │   └── model_final.pt
    │   └── run_20250601_140000/
    │       └── [similar structure]
    │
    ├── metrics/
    │   ├── run_20250601_120000/
    │   │   ├── metrics_epoch_001.json.gz
    │   │   ├── metrics_epoch_010.json.gz
    │   │   └── final_metrics.json.gz
    │   └── run_20250601_140000/
    │       └── [similar structure]
    │
    ├── reports/
    │   ├── run_20250601_120000/
    │   │   └── summary.json
    │   └── run_20250601_140000/
    │       └── summary.json
    │
    ├── logs/
    │   ├── run_20250601_120000/
    │   │   ├── training.log.gz
    │   │   └── debug.log.gz
    │   ├── run_20250601_140000/
    │   │   └── [similar]
    │   └── orchestrator/
    │       ├── s3_uploader.log
    │       └── s3_uploader.log.2025-06-01
    │
    └── ablations/
        ├── ablation_01.json.gz
        └── ablation_02.json.gz
```

## Command Reference

### Setup & Configuration

```bash
# One-time setup
bash runpod/setup_s3.sh

# Configure credentials
cp .env.s3.example .env.s3
nano .env.s3

# Test S3 connection
source .env.s3
python storage/s3_uploader.py --endpoint ... --bucket ... --dry-run --run-once
```

### Training & Upload

```bash
# Full orchestration (recommended)
source .env.s3
bash runpod/orchestrate_training.sh llm_single_gpu --epochs 50

# Or use individual commands:

# Download data
bash scripts/download_data.sh

# Start uploader daemon
bash storage/orchestrators/start_s3_uploader.sh

# Run training (your custom script)
python src/rada/training/train.py --config configs/llm_single_gpu.yaml

# Manual upload pass
python storage/s3_uploader.py \
  --endpoint "$S3_ENDPOINT" \
  --access-key "$S3_ACCESS_KEY" \
  --secret-key "$S3_SECRET_KEY" \
  --bucket "$S3_BUCKET" \
  --run-once
```

### Monitoring

```bash
# Upload logs
tail -f storage/logs/s3_uploader.log

# Disk usage
bash runpod/disk_manager.sh status

# GPU status
nvidia-smi
watch nvidia-smi

# Uploader tmux session
tmux attach-session -t s3-uploader
```

### Disk Management

```bash
# Check disk usage
bash runpod/disk_manager.sh status

# Check if usage exceeds threshold
bash runpod/disk_manager.sh check 80

# Clean old runs (keep last 3)
bash runpod/disk_manager.sh cleanup 3

# Compress old logs
bash runpod/disk_manager.sh compress

# Move directory to network volume
bash runpod/disk_manager.sh move runs/run_old_date
```

## Integration with Training Code

### Option 1: Use Orchestration Script (Recommended)

```bash
bash runpod/orchestrate_training.sh llm_single_gpu
```

The orchestration script handles:
- Environment loading
- Data download
- Uploader daemon startup
- Training execution
- Final upload pass

### Option 2: Manual Integration

In your training script:

```python
import json
from pathlib import Path
from datetime import datetime

# Create run directory
run_name = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
run_dir = Path("runs") / run_name
run_dir.mkdir(parents=True, exist_ok=True)

models_dir = run_dir / "models"
metrics_dir = run_dir / "metrics"
logs_dir = run_dir / "logs"

for d in [models_dir, metrics_dir, logs_dir]:
    d.mkdir(parents=True, exist_ok=True)

# Training loop
for epoch in range(num_epochs):
    # ... your training code ...
    
    # Save checkpoint (auto-uploaded by daemon)
    checkpoint = models_dir / f"checkpoint_epoch_{epoch:03d}.pt"
    torch.save(model.state_dict(), checkpoint)
    
    # Save metrics (auto-compressed + uploaded)
    metrics = {"epoch": epoch, "loss": loss, "accuracy": accuracy}
    metrics_file = metrics_dir / f"metrics_epoch_{epoch:03d}.json"
    with open(metrics_file, "w") as f:
        json.dump(metrics, f, indent=2)
    
    # Log to file (auto-compressed + uploaded)
    with open(logs_dir / "training.log", "a") as f:
        f.write(f"[Epoch {epoch}] loss={loss:.4f} acc={accuracy:.4f}\n")
```

See `src/rada/training/train_example.py` for complete example.

## Storage Considerations

### Pod Storage (40GB)

**Keep for:** Active training, temp files, current checkpoints

**Reserve:** 5-10GB for OS and system

**Typical usage:**
- Training script: ~2GB
- Current run: ~10-20GB
- Reserve: ~5GB
- **Total: ~17-27GB → leaves ~15GB free**

**When to cleanup:**
- When reaching 35% usage → compress logs
- When reaching 80% usage → move runs to network volume
- When reaching 95% usage → stop training

### Network Volume (95GB)

**Keep for:** Backup runs, archives, failed runs

**Typical usage:**
- Historical runs: ~30-50GB
- Backup of current: ~20GB
- Reserve: ~10GB
- **Total: ~60-80GB → leaves ~15GB free**

### S3 Bucket (Unlimited)

**Keep for:** Final archive, sharing with team, long-term storage

**Cost:** ~$0.023/GB/month

## Performance Tuning

### Maximize Throughput

```bash
# 1. Increase poll interval (reduce overhead)
export S3_POLL_INTERVAL=60

# 2. Use faster storage for training data
# Keep data on fast pod storage (not network volume)

# 3. Enable compression (save upload bandwidth)
export S3_COMPRESS_TEXT=true

# 4. Parallel uploads not needed (S3 fast enough)
```

### Minimize Latency

```bash
# 1. Keep frequent checkpoints on pod storage
# 2. Upload infrequently to S3 (every 60s)
# 3. Copy to network volume periodically (not every file)

# Typical pattern:
# Every epoch: checkpoint to pod storage
# Every 10 epochs: copy to network volume + mark for upload
# Every 30s: upload to S3
```

## Troubleshooting

### Problem: Files not uploading

**Check:**
```bash
# 1. Is daemon running?
tmux list-sessions | grep s3-uploader

# 2. Check logs
tail -20 storage/logs/s3_uploader.log

# 3. Verify state file
cat storage/logs/s3_uploader_state.json

# 4. Test S3 connection
s3cmd ls s3://your-bucket/

# 5. Force re-upload
rm storage/logs/s3_uploader_state.json
# Next daemon pass will re-upload all files
```

### Problem: Disk full

**Quick fix:**
```bash
# 1. Check usage
bash runpod/disk_manager.sh status

# 2. Compress old logs
bash runpod/disk_manager.sh compress

# 3. Clean old runs
bash runpod/disk_manager.sh cleanup 3

# 4. Move to network volume
bash runpod/disk_manager.sh move runs/run_old_date
```

### Problem: S3 connection error

**Checklist:**
```bash
# 1. Verify credentials
cat .env.s3

# 2. Test connection manually
s3cmd ls s3://your-bucket/

# 3. Check network
ping s3.amazonaws.com

# 4. Try with explicit endpoint
python storage/s3_uploader.py \
  --endpoint https://s3.amazonaws.com \
  --access-key AKIA... \
  --secret-key ... \
  --bucket my-bucket \
  --run-once
```

## Advanced Topics

### Custom S3 Endpoints

```bash
# AWS S3 (different region)
S3_ENDPOINT=https://s3.us-west-2.amazonaws.com

# MinIO (self-hosted)
S3_ENDPOINT=http://minio.local:9000

# DigitalOcean Spaces
S3_ENDPOINT=https://nyc3.digitaloceanspaces.com

# Custom S3-compatible service
S3_ENDPOINT=https://s3.mycompany.com
```

### Selective Upload

Edit `storage/s3_uploader.py` method `_iter_files_to_upload()` to customize which files are uploaded.

### Scheduled Operations

Add to crontab:
```bash
# Clean old runs daily at 2 AM
0 2 * * * bash /workspace/RADA/runpod/disk_manager.sh cleanup 3

# Check disk space hourly
0 * * * * bash /workspace/RADA/runpod/disk_manager.sh check 80
```

### Integration with CI/CD

See `.github/workflows/` for GitHub Actions examples.

## Summary

| Step | Command | Purpose |
|------|---------|---------|
| 1. Setup | `bash runpod/setup_s3.sh` | Install tools |
| 2. Configure | `cp .env.s3.example .env.s3 && nano .env.s3` | Set S3 credentials |
| 3. Test | `python storage/s3_uploader.py --dry-run --run-once` | Verify S3 connection |
| 4. Train | `bash runpod/orchestrate_training.sh llm_single_gpu` | Run training with auto-upload |
| 5. Monitor | `tail -f storage/logs/s3_uploader.log` | Watch upload progress |
| 6. Cleanup | `bash runpod/disk_manager.sh status` | Check disk usage |

---

**Ready to start?** Run `bash runpod/setup_s3.sh` in your RunPod pod!
