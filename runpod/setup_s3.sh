#!/usr/bin/env bash
# Setup S3 tools on RunPod GPU pod
# Installs s3cmd and prepares environment for data download/upload
#
# Run once after starting a new RunPod pod:
#   bash runpod/setup_s3.sh

set -euo pipefail

echo "🔧 RADA RunPod S3 Setup"
echo "======================="

# Check Python
if ! command -v python &> /dev/null; then
  echo "ERROR: Python not found in PATH"
  exit 1
fi

echo "✓ Python: $(python --version)"

# Install s3cmd
echo ""
echo "Installing s3cmd..."
pip install --quiet s3cmd

if command -v s3cmd &> /dev/null; then
  echo "✓ s3cmd: $(s3cmd --version)"
else
  echo "✗ s3cmd installation failed"
  exit 1
fi

# Install additional tools
echo ""
echo "Installing additional tools..."
pip install --quiet \
  pyyaml \
  python-dotenv

echo "✓ Additional tools installed"

# Create necessary directories
echo ""
echo "Creating directory structure..."
mkdir -p runs/models
mkdir -p runs/metrics
mkdir -p runs/reports
mkdir -p runs/logs
mkdir -p runs/ablations
mkdir -p storage/logs
mkdir -p storage/logs/.tmp_compress
mkdir -p data

echo "✓ Directories created"

# Create .env template if not exists
if [ ! -f ".env.s3" ]; then
  echo ""
  echo "Creating .env.s3 template..."
  cat > .env.s3.template <<'EOF'
# S3-compatible storage configuration
# Copy to .env.s3 and fill in your credentials

# Download settings (optional)
S3_DOWNLOAD_ENABLED=false
S3_DOWNLOAD_ENDPOINT=https://s3.amazonaws.com
S3_DOWNLOAD_BUCKET=your-data-bucket
S3_DOWNLOAD_PREFIX=datasets
S3_DOWNLOAD_RETRIES=3

# Upload settings
S3_ENDPOINT=https://s3.amazonaws.com
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_BUCKET=your-results-bucket
S3_PROJECT_PREFIX=RADA
S3_POLL_INTERVAL=30

# Uploader behavior
S3_COMPRESS_TEXT=true
S3_DRY_RUN=false
EOF
  echo "✓ Template created: .env.s3.template"
fi

# Storage info
echo ""
echo "📊 Storage Information"
echo "======================="
df -h | grep -E "Filesystem|/dev|/workspace|/mnt" || true

echo ""
echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Create .env.s3 from template: cp .env.s3.template .env.s3"
echo "2. Edit .env.s3 with your S3 credentials"
echo "3. Test download: source .env.s3 && bash scripts/download_data.sh"
echo "4. Start uploader: bash storage/orchestrators/start_s3_uploader.sh"
