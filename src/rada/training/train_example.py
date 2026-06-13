#!/usr/bin/env python
"""
RADA Training Integration Example
Shows how to integrate S3 download/upload into your training pipeline

This example demonstrates:
1. Downloading data from S3 before training
2. Saving checkpoints to monitored directory (auto-uploaded)
3. Uploading metrics in real-time
4. Proper cleanup and error handling
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class RADATrainer:
    """Example trainer with S3 integration."""
    
    def __init__(self, config_path: str, run_name: str = None):
        """Initialize trainer with config and run directory."""
        self.project_root = Path.cwd()
        self.config_path = Path(config_path)
        
        # Create run directory
        if run_name is None:
            run_name = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.run_dir = self.project_root / "runs" / run_name
        self.run_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories that are monitored by S3 uploader
        self.models_dir = self.run_dir / "models"
        self.metrics_dir = self.run_dir / "metrics"
        self.reports_dir = self.run_dir / "reports"
        self.logs_dir = self.run_dir / "logs"
        
        for d in [self.models_dir, self.metrics_dir, self.reports_dir, self.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Run directory: {self.run_dir}")
        
        # Load config
        with open(self.config_path) as f:
            self.config = json.load(f)
        
        logger.info(f"Loaded config: {self.config_path}")
    
    def _ensure_data_downloaded(self) -> Path:
        """Ensure training data is available.
        
        If data is in S3, download it first.
        Otherwise assume it's already in ./data/
        """
        data_dir = self.project_root / "data"
        
        if data_dir.exists() and any(data_dir.iterdir()):
            logger.info(f"Data already present: {data_dir}")
            return data_dir
        
        # Check if we should download from S3
        s3_enabled = os.getenv("S3_DOWNLOAD_ENABLED", "false").lower() == "true"
        
        if s3_enabled:
            logger.info("Downloading data from S3...")
            os.system("bash scripts/download_data.sh")
            
            if data_dir.exists() and any(data_dir.iterdir()):
                logger.info("Data download complete")
                return data_dir
            else:
                raise RuntimeError("Data download failed")
        else:
            logger.warning("Data not found and S3 download disabled")
            logger.warning("Set S3_DOWNLOAD_ENABLED=true to download from S3")
            raise RuntimeError(f"Data not found: {data_dir}")
    
    def train(self, num_epochs: int = 10):
        """Example training loop.
        
        In practice, replace this with your actual training code.
        Key points:
        - Save checkpoints to self.models_dir (auto-uploaded by daemon)
        - Save metrics to self.metrics_dir (auto-uploaded + gzipped)
        - Write logs to self.logs_dir (auto-uploaded + gzipped)
        """
        logger.info("Starting training...")
        
        # Ensure data is available
        data_dir = self._ensure_data_downloaded()
        logger.info(f"Using data from: {data_dir}")
        
        # Training loop
        for epoch in range(1, num_epochs + 1):
            logger.info(f"Epoch {epoch}/{num_epochs}")
            
            # Your actual training code here
            # For this example, we just create dummy outputs
            
            # Save checkpoint every epoch
            # This file will be automatically uploaded by S3 uploader daemon
            checkpoint_path = self.models_dir / f"checkpoint_epoch_{epoch:03d}.pt"
            self._save_checkpoint(checkpoint_path, epoch)
            logger.info(f"Saved checkpoint: {checkpoint_path.name}")
            
            # Save metrics after each epoch
            # These will be auto-gzipped if compression is enabled
            metrics = self._compute_metrics(epoch, num_epochs)
            metrics_path = self.metrics_dir / f"metrics_epoch_{epoch:03d}.json"
            with open(metrics_path, "w") as f:
                json.dump(metrics, f, indent=2)
            logger.info(f"Saved metrics: {metrics_path.name}")
            
            # Log epoch summary
            with open(self.logs_dir / "training.log", "a") as f:
                f.write(
                    f"[Epoch {epoch}] loss={metrics['loss']:.4f} "
                    f"acc={metrics['accuracy']:.4f}\n"
                )
        
        logger.info("Training complete")
        
        # Save final report
        report = self._generate_report(num_epochs)
        report_path = self.reports_dir / "training_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        logger.info(f"Saved report: {report_path.name}")
        
        return self.run_dir
    
    def _save_checkpoint(self, path: Path, epoch: int):
        """Save model checkpoint.
        
        In production, this would save your actual model.
        The S3 uploader daemon will detect this file and upload it.
        """
        # Simulate checkpoint (in real code, save model here)
        checkpoint_data = {
            "epoch": epoch,
            "model_state": "dummy_state_dict",
            "optimizer_state": "dummy_optimizer_state",
        }
        with open(path, "w") as f:
            json.dump(checkpoint_data, f)
    
    def _compute_metrics(self, epoch: int, total_epochs: int) -> dict[str, Any]:
        """Compute training metrics.
        
        In production, this would compute real metrics from training.
        """
        import random
        
        # Simulate metrics (loss should decrease)
        loss = 2.0 * (1.0 - epoch / total_epochs) + random.uniform(-0.1, 0.1)
        accuracy = 0.5 + 0.4 * (epoch / total_epochs) + random.uniform(-0.05, 0.05)
        
        return {
            "epoch": epoch,
            "loss": loss,
            "accuracy": accuracy,
            "learning_rate": 0.001,
            "batch_size": 32,
        }
    
    def _generate_report(self, num_epochs: int) -> dict[str, Any]:
        """Generate final training report."""
        return {
            "training_complete": True,
            "total_epochs": num_epochs,
            "run_dir": str(self.run_dir),
            "config": self.config,
            "checkpoints": len(list(self.models_dir.glob("*.pt"))),
            "metrics_files": len(list(self.metrics_dir.glob("*.json"))),
            "timestamp": datetime.now().isoformat(),
        }


def main():
    """Main entry point for training."""
    import sys
    
    # Parse arguments
    config_path = sys.argv[1] if len(sys.argv) > 1 else "configs/llm_single_gpu.yaml"
    num_epochs = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    try:
        # Create trainer
        trainer = RADATrainer(config_path)
        
        # Run training
        run_dir = trainer.train(num_epochs)
        
        logger.info(f"Training complete! Results in: {run_dir}")
        logger.info("S3 uploader daemon will automatically upload results")
        logger.info("Monitor: tail -f storage/logs/s3_uploader.log")
        
        return 0
    
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
