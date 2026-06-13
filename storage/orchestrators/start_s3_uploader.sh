#!/usr/bin/env bash
# Start S3 uploader daemon using tmux
# Allows continuous upload of training artifacts without blocking training process
#
# Environment variables (required):
#   S3_ENDPOINT        S3-compatible endpoint (e.g., https://s3.amazonaws.com)
#   S3_ACCESS_KEY      Access key
#   S3_SECRET_KEY      Secret key
#   S3_BUCKET          Bucket name
#
# Optional:
#   S3_PROJECT_PREFIX  Top-level folder in bucket (default: RADA)
#   S3_POLL_INTERVAL   Polling interval in seconds (default: 30)

set -euo pipefail

: "${S3_ENDPOINT:?Set S3_ENDPOINT first}"
: "${S3_ACCESS_KEY:?Set S3_ACCESS_KEY first}"
: "${S3_SECRET_KEY:?Set S3_SECRET_KEY first}"
: "${S3_BUCKET:?Set S3_BUCKET first}"

S3_PROJECT_PREFIX=${S3_PROJECT_PREFIX:-"RADA"}
S3_POLL_INTERVAL=${S3_POLL_INTERVAL:-"30"}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STORAGE_DIR="$ROOT_DIR/storage"
LOG_DIR="$STORAGE_DIR/logs"
mkdir -p "$LOG_DIR"

SESSION="s3-uploader"

# Check if tmux session already exists
if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "✓ Session $SESSION already running"
  echo "Attach with: tmux attach-session -t $SESSION"
  echo "View logs: tail -f $LOG_DIR/s3_uploader.log"
  exit 0
fi

# Build command
CMD="cd '$ROOT_DIR' && python storage/s3_uploader.py \
  --endpoint '$S3_ENDPOINT' \
  --access-key '$S3_ACCESS_KEY' \
  --secret-key '$S3_SECRET_KEY' \
  --bucket '$S3_BUCKET' \
  --project-prefix '$S3_PROJECT_PREFIX' \
  --poll-interval $S3_POLL_INTERVAL"

echo "Starting S3 uploader daemon..."
echo "Bucket: $S3_BUCKET/$S3_PROJECT_PREFIX"
echo "Endpoint: $S3_ENDPOINT"
echo "Poll interval: ${S3_POLL_INTERVAL}s"

# Create tmux session with output to log file
tmux new-session -d -s "$SESSION" \
  "bash -c \"$CMD 2>&1 | tee -a '$LOG_DIR/s3_uploader.log'\""

echo "✓ Daemon started"
echo ""
echo "Monitor logs:"
echo "  tail -f $LOG_DIR/s3_uploader.log"
echo ""
echo "Attach to session:"
echo "  tmux attach-session -t $SESSION"
echo ""
echo "Stop daemon:"
echo "  tmux kill-session -t $SESSION"
