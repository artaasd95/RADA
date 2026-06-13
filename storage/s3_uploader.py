"""
S3-compatible uploader for RADA training results and model checkpoints.

Periodically uploads new/modified files from:
- runs/*/models/       (model checkpoints)
- runs/*/metrics/      (metrics/eval results)
- runs/*/reports/      (reports)
- runs/*/logs/         (training logs)
- ablations/           (ablation study results)

Features:
- Smart change detection (mtime + size) to avoid re-uploading unchanged files
- Automatic gzip compression for text-like files (.json, .log, .csv)
- Background daemon mode with configurable poll intervals
- State tracking in JSON to enable reliable resume
- Graceful retries and error handling
- Respects storage constraints (40GB pod storage, 95GB network volume)
"""

import argparse
import gzip
import json
import logging
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Extensions that should be gzip-compressed to save storage
COMPRESSIBLE_EXTENSIONS = {".json", ".log", ".md", ".txt", ".csv", ".yaml", ".yml"}

# Max file size to compress (avoid compressing large binaries)
MAX_COMPRESS_SIZE = 500 * 1024 * 1024  # 500 MB


class S3Uploader:
    """Upload RADA training artifacts to S3-compatible storage."""
    
    def __init__(
        self,
        project_root: Path,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        project_prefix: str = "RADA",
        poll_interval_seconds: int = 30,
        compress_text_like: bool = True,
        dry_run: bool = False,
    ) -> None:
        """
        Initialize S3 uploader.
        
        Args:
            project_root: Root directory of RADA project
            endpoint: S3-compatible endpoint (e.g., https://s3.amazonaws.com)
            access_key: AWS/S3 access key
            secret_key: AWS/S3 secret key
            bucket: Bucket name
            project_prefix: Top-level folder in bucket
            poll_interval_seconds: How often to check for new files
            compress_text_like: Whether to gzip text files
            dry_run: If True, don't actually upload (for testing)
        """
        self.project_root = project_root.resolve()
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.project_prefix = project_prefix
        self.poll_interval_seconds = poll_interval_seconds
        self.compress_text_like = compress_text_like
        self.dry_run = dry_run
        
        # Unique remote name for this uploader instance
        self.remote_name = f"rada-{uuid.uuid4().hex[:8]}"
        self.s3cmd_config_path: Optional[Path] = None
        
        # State file to track uploaded files
        logs_dir = self.project_root / "storage" / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = logs_dir / "s3_uploader_state.json"
        self.state: Dict[str, Dict[str, float]] = self._load_state()
        
        # Setup logging
        log_file = logs_dir / "s3_uploader.log"
        handler = logging.FileHandler(log_file)
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    def _load_state(self) -> Dict[str, Dict[str, float]]:
        """Load upload state from file."""
        if self.state_file.exists():
            try:
                return json.loads(self.state_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Failed to load state file: {e}")
                return {}
        return {}
    
    def _save_state(self) -> None:
        """Save upload state to file."""
        try:
            self.state_file.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save state file: {e}")
    
    def _run_s3cmd(self, args: List[str]) -> None:
        """Execute s3cmd command."""
        if not shutil.which("s3cmd"):
            raise RuntimeError("s3cmd is not installed. Install: pip install s3cmd")
        
        command = ["s3cmd", "-c", str(self.s3cmd_config_path)] + args
        result = subprocess.run(command, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"s3cmd failed: {result.stderr}")
    
    def setup_s3cmd(self) -> None:
        """Configure s3cmd with credentials."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".s3cmd", delete=False, encoding="utf-8") as tmp:
            self.s3cmd_config_path = Path(tmp.name)
            
            host_base = self.endpoint.replace("https://", "").replace("http://", "")
            
            tmp.write(f"""[default]
access_key = {self.access_key}
secret_key = {self.secret_key}
host_base = {host_base}
host_bucket = %(bucket)s.{host_base}
use_https = true
signature_v2 = false
""")
        
        logger.info(f"s3cmd configured: {self.s3cmd_config_path}")
    
    def teardown_s3cmd(self) -> None:
        """Clean up s3cmd config file."""
        if self.s3cmd_config_path and self.s3cmd_config_path.exists():
            try:
                self.s3cmd_config_path.unlink()
                logger.info("s3cmd config cleaned up")
            except Exception as e:
                logger.warning(f"Failed to cleanup s3cmd config: {e}")
    
    def _iter_files_to_upload(self) -> Iterable[Path]:
        """Find all files that should be uploaded."""
        runs_dir = self.project_root / "runs"
        storage_dir = self.project_root / "storage"
        
        # Model checkpoint directories
        if runs_dir.exists():
            for run_dir in runs_dir.glob("run_*"):
                if not run_dir.is_dir():
                    continue
                
                for section in ["models", "metrics", "reports", "logs"]:
                    section_dir = run_dir / section
                    if not section_dir.exists():
                        continue
                    
                    for p in section_dir.rglob("*"):
                        if p.is_file():
                            yield p
        
        # Ablation results
        ablations_dir = runs_dir / "ablations" if runs_dir.exists() else None
        if ablations_dir and ablations_dir.exists():
            for p in ablations_dir.glob("*.json"):
                if p.is_file():
                    yield p
        
        # Storage logs (daemon logs)
        if storage_dir.exists():
            for p in storage_dir.glob("logs/*.log"):
                if p.is_file():
                    yield p
    
    def _file_signature(self, path: Path) -> Tuple[float, int]:
        """Get file mtime and size for change detection."""
        try:
            stat = path.stat()
            return (stat.st_mtime, stat.st_size)
        except OSError:
            return (0, 0)
    
    def _needs_upload(self, path: Path) -> bool:
        """Check if file has changed since last upload."""
        key = str(path.resolve())
        mtime, size = self._file_signature(path)
        
        prev = self.state.get(key)
        if not prev:
            logger.debug(f"New file: {path.name}")
            return True
        
        if prev.get("mtime") != mtime or prev.get("size") != size:
            logger.debug(f"Modified file: {path.name}")
            return True
        
        return False
    
    def _remember_uploaded(self, path: Path) -> None:
        """Record file as uploaded."""
        key = str(path.resolve())
        mtime, size = self._file_signature(path)
        self.state[key] = {
            "mtime": mtime,
            "size": size,
            "uploaded_at": time.time(),
        }
    
    def _should_compress(self, path: Path) -> bool:
        """Determine if file should be compressed."""
        if not self.compress_text_like:
            return False
        
        if path.suffix.lower() not in COMPRESSIBLE_EXTENSIONS:
            return False
        
        try:
            if path.stat().st_size > MAX_COMPRESS_SIZE:
                return False
        except OSError:
            return False
        
        return True
    
    def _compress_file(self, source: Path) -> Tuple[Path, bool]:
        """Compress file with gzip if appropriate."""
        if not self._should_compress(source):
            return source, False
        
        tmp_dir = self.project_root / "storage" / "logs" / ".tmp_compress"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        gz_path = tmp_dir / f"{source.name}.gz"
        
        try:
            with source.open("rb") as fin, gzip.open(gz_path, "wb") as fout:
                shutil.copyfileobj(fin, fout)
            
            # Only keep gz if it's actually smaller
            orig_size = source.stat().st_size
            gz_size = gz_path.stat().st_size
            
            if gz_size < orig_size:
                logger.debug(f"Compressed {source.name}: {orig_size} → {gz_size}")
                return gz_path, True
            else:
                gz_path.unlink()
                return source, False
        except Exception as e:
            logger.warning(f"Compression failed for {source.name}: {e}")
            if gz_path.exists():
                gz_path.unlink()
            return source, False
    
    def _remote_path_for(self, local_path: Path, was_compressed: bool) -> str:
        """Build S3 key for file."""
        runs_dir = self.project_root / "runs"
        storage_dir = self.project_root / "storage"
        
        # Ablation results
        if local_path.parent.name == "ablations":
            remote_rel = Path("ablations") / local_path.name
        # Storage logs
        elif str(local_path).startswith(str(storage_dir)):
            remote_rel = Path("logs") / "orchestrator" / local_path.name
        # Run directories
        else:
            try:
                rel = local_path.relative_to(runs_dir)
                run_name = rel.parts[0]
                section = rel.parts[1] if len(rel.parts) > 1 else "misc"
                tail = Path(*rel.parts[2:]) if len(rel.parts) > 2 else Path(local_path.name)
                
                remote_rel = Path(section) / run_name / tail
            except ValueError:
                # Fallback
                remote_rel = Path("misc") / local_path.name
        
        if was_compressed:
            remote_rel = Path(str(remote_rel) + ".gz")
        
        return f"s3://{self.bucket}/{self.project_prefix}/{str(remote_rel).replace(os.sep, '/')}"
    
    def upload_once(self) -> Dict[str, int]:
        """Single upload pass - upload all new/changed files."""
        if not self.s3cmd_config_path:
            raise RuntimeError("s3cmd not configured. Call setup_s3cmd() first.")
        
        uploaded = 0
        failed = 0
        skipped = 0
        total_size = 0
        
        for path in self._iter_files_to_upload():
            if not self._needs_upload(path):
                skipped += 1
                continue
            
            temp_path: Optional[Path] = None
            try:
                upload_source, was_compressed = self._compress_file(path)
                if was_compressed:
                    temp_path = upload_source
                
                remote = self._remote_path_for(path, was_compressed)
                
                if self.dry_run:
                    logger.info(f"[DRY RUN] Would upload: {path.name} → {remote}")
                else:
                    logger.info(f"Uploading: {path.name}")
                    try:
                        self._run_s3cmd(["put", str(upload_source), remote])
                        file_size = upload_source.stat().st_size
                        total_size += file_size
                        self._remember_uploaded(path)
                        uploaded += 1
                    except Exception as e:
                        logger.error(f"Failed to upload {path.name}: {e}")
                        failed += 1
            except Exception as e:
                logger.error(f"Error processing {path.name}: {e}")
                failed += 1
            finally:
                if temp_path and temp_path.exists():
                    try:
                        temp_path.unlink()
                    except Exception:
                        pass
        
        self._save_state()
        return {
            "uploaded": uploaded,
            "failed": failed,
            "skipped": skipped,
            "total_bytes": total_size,
        }
    
    def run_daemon(self) -> None:
        """Run uploader in background daemon mode."""
        logger.info("=" * 70)
        logger.info("RADA S3 Uploader Daemon Started")
        logger.info(f"Project root: {self.project_root}")
        logger.info(f"Remote: s3://{self.bucket}/{self.project_prefix}")
        logger.info(f"Poll interval: {self.poll_interval_seconds}s")
        logger.info(f"Compression: {'enabled' if self.compress_text_like else 'disabled'}")
        logger.info("=" * 70)
        
        try:
            while True:
                try:
                    stats = self.upload_once()
                    if stats["uploaded"] > 0 or stats["failed"] > 0:
                        size_mb = stats["total_bytes"] / (1024 * 1024)
                        logger.info(
                            f"Pass: ↑{stats['uploaded']} ✗{stats['failed']} "
                            f"⊘{stats['skipped']} ({size_mb:.1f}MB)"
                        )
                except Exception as e:
                    logger.error(f"Upload pass failed: {e}")
                
                time.sleep(self.poll_interval_seconds)
        except KeyboardInterrupt:
            logger.info("Daemon stopped by user")
        except Exception as e:
            logger.critical(f"Fatal error: {e}")
            raise


def build_arg_parser() -> argparse.ArgumentParser:
    """Build command-line argument parser."""
    parser = argparse.ArgumentParser(
        description="Upload RADA training artifacts to S3-compatible storage"
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Root directory of RADA project (default: current directory)",
    )
    parser.add_argument("--endpoint", required=True, help="S3-compatible endpoint URL")
    parser.add_argument("--access-key", required=True, help="Access key")
    parser.add_argument("--secret-key", required=True, help="Secret key")
    parser.add_argument("--bucket", required=True, help="Bucket name")
    parser.add_argument(
        "--project-prefix",
        default="RADA",
        help="Top-level folder in bucket (default: RADA)",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=30,
        help="Polling interval in seconds (default: 30)",
    )
    parser.add_argument(
        "--no-compress",
        action="store_true",
        help="Disable gzip compression for text-like files",
    )
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run one upload pass and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Don't actually upload, just show what would be uploaded",
    )
    return parser


def main() -> int:
    """Main entry point."""
    parser = build_arg_parser()
    args = parser.parse_args()
    
    uploader = S3Uploader(
        project_root=Path(args.project_root),
        endpoint=args.endpoint,
        access_key=args.access_key,
        secret_key=args.secret_key,
        bucket=args.bucket,
        project_prefix=args.project_prefix,
        poll_interval_seconds=args.poll_interval,
        compress_text_like=not args.no_compress,
        dry_run=args.dry_run,
    )
    
    try:
        uploader.setup_s3cmd()
        
        if args.run_once:
            logger.info("Running single upload pass...")
            stats = uploader.upload_once()
            logger.info(f"Complete: ↑{stats['uploaded']} ✗{stats['failed']} ⊘{stats['skipped']}")
            return 0 if stats["failed"] == 0 else 1
        else:
            uploader.run_daemon()
            return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1
    finally:
        uploader.teardown_s3cmd()


if __name__ == "__main__":
    raise SystemExit(main())
