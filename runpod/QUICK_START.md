# RunPod Quick Reference

Complete guide for running RADA training on RunPod with S3 backup.

## Pre-Training Checklist

- [ ] Rented RunPod GPU instance (with network volume)
- [ ] Copied project to pod or cloned from git
- [ ] S3 bucket created (AWS, MinIO, or DigitalOcean Spaces)
- [ ] S3 credentials obtained

## Step-by-Step Setup

### 1. SSH into RunPod

```bash
ssh -i ~/.ssh/runpod_key root@<runpod-ip>
cd /workspace/RADA  # or wherever project is cloned
```

### 2. Install S3 Tools

```bash
bash runpod/setup_s3.sh
```

### 3. Configure S3 Credentials

```bash
cp .env.s3.example .env.s3
nano .env.s3
```

Fill in your S3 details:
```bash
S3_ENDPOINT=https://s3.amazonaws.com       # Your S3 endpoint
S3_ACCESS_KEY=AKIA...                     # Your AWS access key
S3_SECRET_KEY=...                          # Your AWS secret key
S3_BUCKET=my-rada-results                  # Your bucket name
S3_DOWNLOAD_ENABLED=false                  # Or true if downloading data
```

### 4. Test S3 Connection

```bash
source .env.s3
python storage/s3_uploader.py \
  --endpoint "$S3_ENDPOINT" \
  --access-key "$S3_ACCESS_KEY" \
  --secret-key "$S3_SECRET_KEY" \
  --bucket "$S3_BUCKET" \
  --dry-run \
  --run-once
```

Should show "DRY RUN" messages without errors.

### 5. Run Training

```bash
source .env.s3
bash runpod/orchestrate_training.sh llm_single_gpu --epochs 50
```

Or for distributed training:
```bash
bash runpod/orchestrate_training.sh llm_distributed --epochs 100
```

## Monitoring Training

### In another SSH terminal:

```bash
# Monitor uploader
tail -f /workspace/RADA/storage/logs/s3_uploader.log

# Check disk usage
bash /workspace/RADA/runpod/disk_manager.sh status

# Watch training progress
watch nvidia-smi  # GPU utilization
```

## During Training: Issues & Fixes

### GPU Out of Memory

```bash
# Reduce batch size
bash runpod/orchestrate_training.sh llm_single_gpu --batch-size 16
```

### Disk Space Critical

```bash
# Move old runs to network volume
bash runpod/disk_manager.sh move runs/run_old_date

# Or compress logs
bash runpod/disk_manager.sh compress
```

### Upload Failed

```bash
# Check S3 credentials
cat .env.s3

# Test connection again
python storage/s3_uploader.py \
  --endpoint "$S3_ENDPOINT" \
  --access-key "$S3_ACCESS_KEY" \
  --secret-key "$S3_SECRET_KEY" \
  --bucket "$S3_BUCKET" \
  --run-once

# Check state
cat storage/logs/s3_uploader_state.json
```

## After Training Complete

### Ensure All Files Are Uploaded

```bash
# Final manual upload
python storage/s3_uploader.py \
  --endpoint "$S3_ENDPOINT" \
  --access-key "$S3_ACCESS_KEY" \
  --secret-key "$S3_SECRET_KEY" \
  --bucket "$S3_BUCKET" \
  --run-once
```

### Download Results Locally

```bash
# From local machine (not on RunPod)
s3cmd get s3://my-rada-results/RADA/models/ ./models/ --recursive
```

### Cleanup Pod Storage

```bash
# Remove oldest runs (keep last 3)
bash runpod/disk_manager.sh cleanup 3
```

## Common Workflows

### Workflow 1: Single Quick Experiment

```bash
# 1. Setup (first time only)
bash runpod/setup_s3.sh
cp .env.s3.example .env.s3
# Edit .env.s3

# 2. Run experiment
source .env.s3
bash runpod/orchestrate_training.sh llm_single_gpu --epochs 10

# 3. Results automatically uploaded
```

### Workflow 2: Multiple Sequential Experiments

```bash
source .env.s3

# Experiment 1
bash runpod/orchestrate_training.sh llm_single_gpu --epochs 50

# Experiment 2 (while 1 uploads in background)
bash runpod/orchestrate_training.sh llm_distributed --epochs 100

# Experiment 3
bash runpod/orchestrate_training.sh llm_custom --epochs 75

# Monitor all uploads
tail -f storage/logs/s3_uploader.log
```

### Workflow 3: Download Data → Train → Upload

```bash
# If your training data is in S3
export S3_DOWNLOAD_ENABLED=true
export S3_DOWNLOAD_BUCKET=my-data-bucket
export S3_DOWNLOAD_PREFIX=datasets

source .env.s3
bash runpod/orchestrate_training.sh llm_single_gpu

# Automatically downloads, trains, uploads results
```

## Environment Variables Quick Reference

```bash
# Data download (optional)
S3_DOWNLOAD_ENABLED=true|false
S3_DOWNLOAD_ENDPOINT=https://s3.amazonaws.com
S3_DOWNLOAD_BUCKET=my-data
S3_DOWNLOAD_PREFIX=datasets

# Results upload (required)
S3_ENDPOINT=https://s3.amazonaws.com
S3_ACCESS_KEY=AKIA...
S3_SECRET_KEY=...
S3_BUCKET=my-results

# Behavior
S3_POLL_INTERVAL=30                    # seconds
S3_COMPRESS_TEXT=true|false            # gzip compression
S3_PROJECT_PREFIX=RADA                 # S3 folder name

# Advanced
S3_DRY_RUN=true|false                  # test mode
SKIP_DOWNLOAD=true|false               # skip data download
SKIP_UPLOAD=true|false                 # skip results upload
```

## Storage Info

```
RunPod Pod Storage Layout:
/workspace/RADA/
├── data/                          # Training datasets
├── runs/
│   ├── run_20250601_120000/      # Run directory
│   │   ├── models/               # Model checkpoints
│   │   ├── metrics/              # Eval results
│   │   ├── reports/              # Analysis reports
│   │   └── logs/                 # Training logs
│   ├── run_20250601_140000/
│   └── ablations/                # Ablation studies
└── storage/
    ├── logs/
    │   ├── s3_uploader.log       # Upload log
    │   ├── s3_uploader_state.json # Upload state
    │   └── .tmp_compress/        # Temp compressed files
    └── s3_uploader.py            # Upload script
```

## S3 Bucket Structure

```
s3://my-rada-results/
├── RADA/                          # S3_PROJECT_PREFIX
│   ├── models/
│   │   ├── run_20250601_120000/  # Model checkpoints
│   │   └── run_20250601_140000/
│   ├── metrics/
│   │   ├── run_20250601_120000/  # Eval metrics
│   │   └── run_20250601_140000/
│   ├── reports/                  # Reports
│   ├── logs/
│   │   ├── run_20250601_120000/  # Training logs (gzipped)
│   │   ├── run_20250601_140000/
│   │   └── orchestrator/         # Daemon logs
│   └── ablations/                # Ablation results (gzipped)
```

## Performance Expectations

### Training Speed
- Single GPU (A100): ~200 samples/sec
- Dual GPU (A100): ~400 samples/sec
- 8x GPU (A100): ~3000 samples/sec

### Upload Speed
- Local → S3: ~50-100 MB/s
- Compression ratio: 80-95% for text (logs, metrics)
- Typical checkpoint size: 1-5 GB (not compressed)

### Storage Usage
- Per run (100 epochs): ~10-50 GB
- Pod storage (40GB): ~3-4 runs before cleanup
- Network volume (95GB): ~10-20 runs
- S3 bucket: Unlimited

## Tips & Tricks

### Speed Up Training Startup
```bash
# Pre-download data before starting training
bash scripts/download_data.sh
bash runpod/orchestrate_training.sh llm_single_gpu  # Data already local
```

### Save Pod Storage
```bash
# Enable compression for small text files
export S3_COMPRESS_TEXT=true
bash runpod/orchestrate_training.sh llm_single_gpu
# Saves 80-95% for logs, only minimal space for binary checkpoints
```

### Monitor Multiple Runs
```bash
# Terminal 1: Training
bash runpod/orchestrate_training.sh llm_single_gpu

# Terminal 2: Upload progress
watch -n5 'tail -20 storage/logs/s3_uploader.log'

# Terminal 3: Disk usage
watch 'bash runpod/disk_manager.sh status'
```

### Resume Failed Training
```bash
# If training was interrupted, just re-run
bash runpod/orchestrate_training.sh llm_single_gpu

# State tracking will skip re-uploading unchanged files
# Training script should support resume from checkpoint
```

## Troubleshooting Commands

```bash
# Is uploader running?
tmux list-sessions

# Check upload status
cat storage/logs/s3_uploader_state.json | jq '.' | head

# Check recent uploads
tail -20 storage/logs/s3_uploader.log

# Disk usage
df -h /workspace /
du -sh runs/ data/ storage/

# S3 connection test
s3cmd ls s3://my-bucket/ | head

# GPU status
nvidia-smi
watch nvidia-smi

# Network connectivity
ping s3.amazonaws.com
```

## Estimated Costs (AWS)

| Component | Usage | Cost/Month |
|-----------|-------|-----------|
| GPU (A100) | 100 hours | ~$150 |
| Storage (S3) | 100 GB | $2.30 |
| Data transfer | 50 GB | $5.00 |
| **Total** | - | **~$157** |

## Support

For issues:
1. Check logs: `tail -f storage/logs/s3_uploader.log`
2. Test S3: `python storage/s3_uploader.py --endpoint ... --bucket ... --run-once`
3. Check disk: `bash runpod/disk_manager.sh status`
4. View docs: `cat storage/README_S3.md`

---

**Next:** Run `bash runpod/setup_s3.sh` to get started!
