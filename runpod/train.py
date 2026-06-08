#!/usr/bin/env python3
"""RunPod-safe reflection training wrapper for RADA."""

from __future__ import annotations

import argparse
import glob
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
STORAGE_DIR = REPO_ROOT / "storage"
DEFAULT_CONFIG = REPO_ROOT / "runpod" / "config.yaml"


class _Tee:
    def __init__(self, *streams):
        self._streams = streams

    def write(self, data: str) -> None:
        for stream in self._streams:
            stream.write(data)
            stream.flush()

    def flush(self) -> None:
        for stream in self._streams:
            stream.flush()


def _find_latest_checkpoint(root: Path) -> Path | None:
    patterns = [str(root / "checkpoints" / "checkpoint-*"), str(root / "**" / "checkpoint-*")]
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(Path(p) for p in glob.glob(pattern, recursive=True))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _disk_sync_loop(stop: threading.Event, interval_sec: int = 300) -> None:
    sys.path.insert(0, str(STORAGE_DIR))
    from disk_monitor import exceeds_threshold  # noqa: WPS433

    while not stop.wait(interval_sec):
        if exceeds_threshold(REPO_ROOT, 80.0):
            subprocess.run(
                [sys.executable, str(STORAGE_DIR / "ftp_sync.py"), "--check-threshold", "80"],
                cwd=REPO_ROOT,
                check=False,
            )


def _load_config(path: Path) -> dict:
    import yaml

    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def main() -> int:
    parser = argparse.ArgumentParser(description="RunPod reflection training wrapper")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--resume", default="auto")
    args = parser.parse_args()

    cfg = _load_config(Path(args.config))
    run_id = cfg.get("output_run_id", "runpod")
    log_dir = REPO_ROOT / "experiments" / "adapters" / run_id
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "train.log"

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "reflection_train.py"),
        "--backend",
        cfg.get("backend", "unsloth"),
        "--model-id",
        cfg["model_id"],
        "--data-source",
        cfg.get("data_source", "distilled"),
        "--epochs",
        str(cfg.get("epochs", 1)),
        "--batch-size",
        str(cfg.get("batch_size", 2)),
        "--output-run-id",
        run_id,
        "--method",
        cfg.get("method", "reflection"),
    ]
    if cfg.get("distilled_name"):
        cmd.extend(["--distilled-name", cfg["distilled_name"]])

    env = {**os.environ}
    if args.resume == "auto":
        latest = _find_latest_checkpoint(log_dir)
        if latest is not None:
            env["RADA_RESUME_FROM"] = str(latest)
            print(f"[runpod] auto-resume from {latest}")

    stop_event = threading.Event()
    monitor = threading.Thread(target=_disk_sync_loop, args=(stop_event,), daemon=True)
    monitor.start()

    proc: subprocess.Popen[str] | None = None

    def _handle_signal(signum: int, _frame: object) -> None:
        if proc is not None and proc.poll() is None:
            proc.send_signal(signum)

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    with log_path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"\n--- runpod start {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} ---\n")
        tee = _Tee(sys.stdout, log_file)
        proc = subprocess.Popen(
            cmd,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            tee.write(line)
        rc = proc.wait()

    stop_event.set()
    monitor.join(timeout=1)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
