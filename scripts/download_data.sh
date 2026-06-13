#!/usr/bin/env bash
# Download data from S3-compatible storage or HTTP sources
# Used for downloading training datasets before training starts on RunPod
#
# Environment variables:
#   PROVIDER      s3|http (required)
#   S3_ENDPOINT   S3 endpoint URL (for s3 provider)
#   S3_BUCKET     Bucket name (required for s3)
#   S3_PREFIX     Path prefix in bucket (optional, default: '')
#   S3_ACCESS_KEY AWS/S3 access key (required for s3)
#   S3_SECRET_KEY AWS/S3 secret key (required for s3)
#   HTTP_URL      Full HTTP URL to file (required for http)
#   DEST          Local destination directory (default: ./data)
#   RETRIES       Number of retry attempts (default: 3)

set -euo pipefail

usage() {
  cat <<EOF
Usage: $0

S3-compatible providers:
  PROVIDER=s3 S3_BUCKET=my-bucket S3_PREFIX=datasets \\
    S3_ENDPOINT=https://s3.amazonaws.com \\
    S3_ACCESS_KEY=xxx S3_SECRET_KEY=yyy \\
    DEST=./data bash scripts/download_data.sh

HTTP provider:
  PROVIDER=http HTTP_URL=https://example.com/file.tar.gz \\
    DEST=./data bash scripts/download_data.sh

EOF
}

PROVIDER=${PROVIDER:-}
S3_ENDPOINT=${S3_ENDPOINT:-}
S3_BUCKET=${S3_BUCKET:-}
S3_PREFIX=${S3_PREFIX:-}
S3_ACCESS_KEY=${S3_ACCESS_KEY:-}
S3_SECRET_KEY=${S3_SECRET_KEY:-}
HTTP_URL=${HTTP_URL:-}
DEST=${DEST:-./data}
RETRIES=${RETRIES:-3}

if [ -z "$PROVIDER" ]; then
  echo "ERROR: PROVIDER not set (s3 or http)"
  usage
  exit 1
fi

mkdir -p "$DEST"

cmd_exists() { command -v "$1" >/dev/null 2>&1; }

# Function to retry a command
retry() {
  local max_attempts=$1
  shift
  local attempt=1
  
  while [ $attempt -le $max_attempts ]; do
    if "$@"; then
      return 0
    fi
    
    if [ $attempt -lt $max_attempts ]; then
      echo "Attempt $attempt failed. Retrying in 5 seconds..."
      sleep 5
    fi
    
    ((attempt++))
  done
  
  echo "ERROR: Command failed after $max_attempts attempts"
  return 1
}

case "$PROVIDER" in
  s3)
    if [ -z "$S3_BUCKET" ] || [ -z "$S3_ENDPOINT" ] || [ -z "$S3_ACCESS_KEY" ] || [ -z "$S3_SECRET_KEY" ]; then
      echo "ERROR: S3 provider requires S3_BUCKET, S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY"
      exit 1
    fi
    
    if ! cmd_exists s3cmd; then
      echo "ERROR: s3cmd not found. Install it:"
      echo "  pip install s3cmd"
      echo "  or: apt-get install s3cmd"
      exit 2
    fi
    
    echo "Configuring s3cmd..."
    
    # Create temporary s3cmd config
    S3CMD_CONFIG=$(mktemp)
    cat > "$S3CMD_CONFIG" <<EOF
[default]
access_key = $S3_ACCESS_KEY
secret_key = $S3_SECRET_KEY
host_base = $(echo "$S3_ENDPOINT" | sed 's|https://||;s|http://||')
host_bucket = %(bucket)s.$(echo "$S3_ENDPOINT" | sed 's|https://||;s|http://||')
use_https = true
EOF
    
    S3_PATH="s3://$S3_BUCKET"
    if [ -n "$S3_PREFIX" ]; then
      S3_PATH="$S3_PATH/$S3_PREFIX"
    fi
    
    echo "Downloading from $S3_PATH to $DEST..."
    retry $RETRIES s3cmd -c "$S3CMD_CONFIG" sync "$S3_PATH" "$DEST/" --recursive
    
    rm -f "$S3CMD_CONFIG"
    ;;
    
  http)
    if [ -z "$HTTP_URL" ]; then
      echo "ERROR: HTTP provider requires HTTP_URL"
      exit 1
    fi
    
    echo "Downloading from $HTTP_URL"
    
    if cmd_exists aria2c; then
      echo "Using aria2c for parallel download..."
      retry $RETRIES aria2c -d "$DEST" -x 4 -s 4 "$HTTP_URL"
    elif cmd_exists wget; then
      echo "Using wget for download..."
      retry $RETRIES wget -P "$DEST" "$HTTP_URL"
    elif cmd_exists curl; then
      echo "Using curl for download..."
      retry $RETRIES curl -L "$HTTP_URL" -o "$DEST/$(basename "$HTTP_URL")"
    else
      echo "ERROR: No download tool found (aria2c, wget, or curl)"
      exit 2
    fi
    ;;
    
  *)
    echo "ERROR: Unsupported PROVIDER: $PROVIDER (use s3 or http)"
    usage
    exit 1
    ;;
esac

echo "✓ Download complete. Files in: $DEST"
du -sh "$DEST"
