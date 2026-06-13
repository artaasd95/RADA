#!/usr/bin/env bash
# RADA Training Orchestration Script
# Handles: data download → training → background result upload
#
# Usage:
#   bash runpod/orchestrate_training.sh [config_name] [optional_extra_args]
#
# Examples:
#   bash runpod/orchestrate_training.sh llm_single_gpu
#   bash runpod/orchestrate_training.sh llm_distributed --epochs 100
#   SKIP_DOWNLOAD=true bash runpod/orchestrate_training.sh llm_single_gpu

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
  echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
  echo -e "${BLUE}  $1${NC}"
  echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
}

print_success() {
  echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
  echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
  echo -e "${RED}✗ $1${NC}"
}

# Parse arguments
CONFIG=${1:-}
EXTRA_ARGS=${@:2}
SKIP_DOWNLOAD=${SKIP_DOWNLOAD:-false}
SKIP_UPLOAD=${SKIP_UPLOAD:-false}

if [ -z "$CONFIG" ]; then
  print_error "Usage: $0 <config_name> [optional_args]"
  echo ""
  echo "Available configs:"
  ls -1 configs/llm_*.yaml 2>/dev/null | xargs -n1 basename | sed 's/llm_//' | sed 's/.yaml//' | sed 's/^/  - /'
  exit 1
fi

# Check if config exists
CONFIG_FILE="configs/llm_${CONFIG}.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
  CONFIG_FILE="configs/${CONFIG}.yaml"
fi

if [ ! -f "$CONFIG_FILE" ]; then
  print_error "Config file not found: $CONFIG_FILE"
  exit 1
fi

print_header "RADA Training Orchestration"

# Load S3 configuration if available
if [ -f ".env.s3" ]; then
  source .env.s3
  print_success "Loaded S3 configuration"
else
  print_warning "No .env.s3 found - S3 upload will be disabled"
  SKIP_UPLOAD=true
fi

# Check storage
print_header "Storage Check"
df -h | grep -E "Filesystem|/dev|/workspace" || true
echo ""

ROOT_DIR="$(pwd)"
RUNS_DIR="$ROOT_DIR/runs"
DATA_DIR="$ROOT_DIR/data"

# ─────────────────────────────────────────────────────────────────
# STEP 1: Download data if configured
# ─────────────────────────────────────────────────────────────────
if [ "$SKIP_DOWNLOAD" = "false" ] && [ "${S3_DOWNLOAD_ENABLED:-false}" = "true" ]; then
  print_header "Step 1: Downloading Data"
  
  if [ -d "$DATA_DIR" ] && [ "$(ls -A $DATA_DIR)" ]; then
    print_warning "Data directory already has files. Skipping download."
    print_warning "To force: rm -rf $DATA_DIR && bash runpod/orchestrate_training.sh $CONFIG"
  else
    print_success "Downloading from S3..."
    
    export PROVIDER=s3
    export S3_ENDPOINT="${S3_DOWNLOAD_ENDPOINT}"
    export S3_BUCKET="${S3_DOWNLOAD_BUCKET}"
    export S3_PREFIX="${S3_DOWNLOAD_PREFIX}"
    export S3_ACCESS_KEY="${S3_DOWNLOAD_ACCESS_KEY:-}"
    export S3_SECRET_KEY="${S3_DOWNLOAD_SECRET_KEY:-}"
    export DEST="$DATA_DIR"
    
    if ! bash scripts/download_data.sh; then
      print_error "Data download failed"
      exit 1
    fi
    
    print_success "Data downloaded"
  fi
else
  if [ "$SKIP_DOWNLOAD" = "true" ]; then
    print_warning "Download skipped (SKIP_DOWNLOAD=true)"
  else
    print_warning "Download disabled (S3_DOWNLOAD_ENABLED=false)"
  fi
fi

echo ""

# ─────────────────────────────────────────────────────────────────
# STEP 2: Create run directory
# ─────────────────────────────────────────────────────────────────
print_header "Step 2: Preparing Run Directory"

RUN_NAME="run_$(date +%Y%m%d_%H%M%S)"
RUN_DIR="$RUNS_DIR/$RUN_NAME"

mkdir -p "$RUN_DIR"/{models,metrics,reports,logs}

print_success "Run directory: $RUN_DIR"

# Copy config to run directory for reference
cp "$CONFIG_FILE" "$RUN_DIR/config.yaml"

echo ""

# ─────────────────────────────────────────────────────────────────
# STEP 3: Start S3 uploader daemon (if enabled)
# ─────────────────────────────────────────────────────────────────
if [ "$SKIP_UPLOAD" = "false" ] && [ -n "${S3_BUCKET:-}" ]; then
  print_header "Step 3: Starting Background Uploader"
  
  export S3_ENDPOINT
  export S3_ACCESS_KEY
  export S3_SECRET_KEY
  export S3_BUCKET
  export S3_PROJECT_PREFIX
  export S3_POLL_INTERVAL
  
  if bash storage/orchestrators/start_s3_uploader.sh; then
    print_success "S3 uploader daemon started"
    print_success "Monitor: tail -f storage/logs/s3_uploader.log"
  else
    print_warning "Failed to start uploader - will continue anyway"
  fi
else
  if [ "$SKIP_UPLOAD" = "true" ]; then
    print_warning "Upload skipped (SKIP_UPLOAD=true)"
  else
    print_warning "Upload disabled (S3_BUCKET not set)"
  fi
fi

echo ""

# ─────────────────────────────────────────────────────────────────
# STEP 4: Run training
# ─────────────────────────────────────────────────────────────────
print_header "Step 4: Starting Training"

print_success "Config: $CONFIG"
print_success "Run directory: $RUN_DIR"
print_success "Extra arguments: $EXTRA_ARGS"

echo ""
echo "Command:"
echo "  python -m rada.training.train \\"
echo "    --config $CONFIG_FILE \\"
echo "    --output-dir $RUN_DIR \\"
echo "    --data-dir $DATA_DIR \\"
echo "    $EXTRA_ARGS"
echo ""

# Run training
if python -m rada.training.train \
  --config "$CONFIG_FILE" \
  --output-dir "$RUN_DIR" \
  --data-dir "$DATA_DIR" \
  $EXTRA_ARGS; then
  
  print_success "Training completed successfully"
else
  TRAIN_EXIT_CODE=$?
  print_error "Training failed with exit code $TRAIN_EXIT_CODE"
  exit $TRAIN_EXIT_CODE
fi

echo ""

# ─────────────────────────────────────────────────────────────────
# STEP 5: Final upload (optional)
# ─────────────────────────────────────────────────────────────────
if [ "$SKIP_UPLOAD" = "false" ] && [ -n "${S3_BUCKET:-}" ]; then
  print_header "Step 5: Final Upload Pass"
  
  print_success "Running final upload pass to ensure all files are synced..."
  
  if python storage/s3_uploader.py \
    --endpoint "$S3_ENDPOINT" \
    --access-key "$S3_ACCESS_KEY" \
    --secret-key "$S3_SECRET_KEY" \
    --bucket "$S3_BUCKET" \
    --project-prefix "${S3_PROJECT_PREFIX}" \
    --run-once; then
    
    print_success "Final upload complete"
  else
    print_warning "Final upload had some failures - check logs"
  fi
  
  echo ""
fi

# ─────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────
print_header "Training Complete"

echo ""
echo "Results location:"
echo "  Local: $RUN_DIR"
echo ""
echo "Files:"
ls -lh "$RUN_DIR"/models/ 2>/dev/null | tail -5 || echo "  (no model files)"
echo ""

if [ "$SKIP_UPLOAD" = "false" ] && [ -n "${S3_BUCKET:-}" ]; then
  echo "Remote location:"
  echo "  S3: s3://$S3_BUCKET/$S3_PROJECT_PREFIX/"
  echo ""
  echo "Monitor upload:"
  echo "  tail -f storage/logs/s3_uploader.log"
  echo ""
fi

print_success "Run: $RUN_NAME"
