# RunPod execution — RADA

Tmux-safe reflection LoRA training with auto-resume and FTP storage sync.

## Quick start

```bash
tmux new -s train
bash runpod/setup.sh
python runpod/train.py
```

Wraps `scripts/reflection_train.py` with RunPod config overrides.
