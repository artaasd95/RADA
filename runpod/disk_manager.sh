#!/usr/bin/env bash
# Disk space management for RADA on RunPod
# Handles periodic cleanup and manages storage constraints
# 
# Pod storage: ~40GB (use for active training)
# Network volume: ~95GB (use for backups)
#
# Usage:
#   python storage/disk_manager.py --check-threshold 80
#   python storage/disk_manager.py --cleanup-old-runs --keep 3
#   python storage/disk_manager.py --status

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
  echo -e "${BLUE}$1${NC}"
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

# Get disk usage percentage
get_disk_usage() {
  local path=$1
  df "$path" | awk 'NR==2 {print $5}' | sed 's/%//'
}

# Get disk space in MB
get_disk_space_mb() {
  local path=$1
  df "$path" | awk 'NR==2 {print int($4/1024)}'
}

# Show status
status() {
  print_header "Disk Space Status"
  
  echo ""
  echo "Pod storage (usually /tmp or root):"
  if mountpoint -q /workspace 2>/dev/null; then
    # /workspace is a separate volume
    USAGE=$(get_disk_usage "/")
    FREE=$(get_disk_space_mb "/")
    echo "  / : ${USAGE}% used (${FREE}MB free)"
  else
    USAGE=$(get_disk_usage "/")
    FREE=$(get_disk_space_mb "/")
    echo "  / : ${USAGE}% used (${FREE}MB free)"
  fi
  
  echo ""
  echo "Network volume (if mounted):"
  if mountpoint -q /workspace 2>/dev/null; then
    USAGE=$(get_disk_usage "/workspace")
    FREE=$(get_disk_space_mb "/workspace")
    echo "  /workspace : ${USAGE}% used (${FREE}MB free)"
  else
    echo "  /workspace : not mounted"
  fi
  
  echo ""
  echo "Directory sizes:"
  echo "  data/       : $(du -sh data 2>/dev/null | cut -f1)"
  echo "  runs/       : $(du -sh runs 2>/dev/null | cut -f1)"
  echo "  models/     : $(du -sh runs/*/models 2>/dev/null | cut -f1 || echo 'N/A')"
  echo "  storage/    : $(du -sh storage 2>/dev/null | cut -f1)"
}

# Clean old runs
cleanup_old_runs() {
  local keep=$1
  
  print_header "Cleaning Old Runs (keeping last $keep)"
  
  cd runs 2>/dev/null || return
  
  # Get all run directories sorted by date
  local runs=$(ls -d run_* 2>/dev/null | sort -r)
  local count=0
  local deleted_size=0
  
  for run in $runs; do
    ((count++))
    if [ $count -gt $keep ]; then
      local size=$(du -sh "$run" | cut -f1)
      print_warning "Removing: $run ($size)"
      rm -rf "$run"
      deleted_size=$((deleted_size + ${size%G*} * 1024))  # Rough conversion
    fi
  done
  
  if [ $count -le $keep ]; then
    print_success "No cleanup needed (only $count runs)"
  else
    print_success "Removed $((count - keep)) old runs"
  fi
  
  cd - > /dev/null
}

# Check threshold and warn/act
check_threshold() {
  local threshold=$1
  local path=${2:-.}
  
  local usage=$(get_disk_usage "$path")
  local free=$(get_disk_space_mb "$path")
  
  echo "Checking $path: ${usage}% used (${free}MB free)"
  
  if [ "$usage" -ge "$threshold" ]; then
    print_error "Threshold exceeded: ${usage}% >= ${threshold}%"
    return 1
  else
    print_success "Below threshold"
    return 0
  fi
}

# Compress old logs
compress_logs() {
  print_header "Compressing Old Logs"
  
  local count=0
  
  # Compress logs older than 7 days
  find runs -name "*.log" -type f -mtime +7 | while read -r log; do
    if [ ! -f "$log.gz" ]; then
      print_warning "Compressing: $log"
      gzip "$log"
      ((count++))
    fi
  done
  
  if [ $count -gt 0 ]; then
    print_success "Compressed $count log files"
  else
    print_success "No old logs to compress"
  fi
}

# Move to network volume
move_to_network() {
  local src=$1
  local dest=${2:-.}
  
  if [ ! -d "$src" ]; then
    print_error "Source not found: $src"
    return 1
  fi
  
  if ! mountpoint -q /workspace 2>/dev/null; then
    print_error "Network volume not mounted at /workspace"
    return 1
  fi
  
  print_header "Moving $src to /workspace"
  
  mkdir -p "/workspace/backups"
  mv "$src" "/workspace/backups/"
  
  print_success "Moved to /workspace/backups/$(basename $src)"
}

# Main
case "${1:-status}" in
  status)
    status
    ;;
  check)
    THRESHOLD=${2:-80}
    check_threshold $THRESHOLD
    ;;
  cleanup)
    KEEP=${2:-3}
    cleanup_old_runs $KEEP
    ;;
  compress)
    compress_logs
    ;;
  move)
    SRC=${2:?"Usage: $0 move <source>"}
    move_to_network "$SRC"
    ;;
  *)
    print_error "Unknown command: $1"
    echo ""
    echo "Usage: $0 [command] [args]"
    echo ""
    echo "Commands:"
    echo "  status              Show disk usage (default)"
    echo "  check [threshold]   Check if usage exceeds threshold (default 80%)"
    echo "  cleanup [keep]      Remove old runs, keeping last N (default 3)"
    echo "  compress            Gzip old logs (>7 days)"
    echo "  move <dir>          Move directory to network volume"
    echo ""
    exit 1
    ;;
esac
