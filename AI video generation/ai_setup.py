"""Explicit first-run installer for the integrated LTX-Video runtime.

Run only after the user clicks Install AI engine in the local Studio. Hardware
scanning itself remains side-effect free. This script installs CUDA packages
and downloads model weights into the standard Hugging Face cache.
"""
from __future__ import annotations
import json, os, subprocess, sys, time, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STATE = ROOT / "logs" / "ai_setup.json"
LOG = ROOT / "logs" / "ai_setup.log"
MODEL_ID = os.environ.get("OFFLINE_STUDIO_LTX_MODEL", "Lightricks/LTX-Video")

def write(status, message, progress=0, error=None):
    STATE.parent.mkdir(exist_ok=True)
    payload = {"status": status, "message": message, "progress": progress,
               "updated_at": time.time(), "error": error}
    STATE.write_text(json.dumps(payload, indent=2), encoding="utf-8")

def run(args, label, progress):
    write("running", label, progress)
    with LOG.open("a", encoding="utf-8", errors="replace") as log:
        log.write("\n\n$ " + " ".join(args) + "\n")
        log.flush()
        result = subprocess.run(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"{label} failed (exit {result.returncode}). Open logs/ai_setup.log for details.")

def main():
    try:
        from hardware_scanner import scan_hardware
        inventory = scan_hardware(ROOT)
        gpu = inventory.get("primary_gpu") or {}
        vram = (gpu.get("vram_total_mb") or 0) / 1024
        ram = inventory.get("memory_gb") or 0
        disk = (inventory.get("disk") or {}).get("free_gb") or 0
        if vram < 10:
            raise RuntimeError(f"Detected {vram:.1f} GB dedicated VRAM. Integrated LTX needs at least 10 GB. No model was downloaded. This PC needs a different, low-VRAM model adapter before AI video generation can be enabled.")
        if ram < 32 or disk < 50:
            raise RuntimeError(f"LTX setup needs 32 GB system RAM and about 50 GB free disk. Detected RAM={ram} GB, free disk={disk} GB.")
        write("running", "Installing CUDA-enabled PyTorch (large download)…", 5)
        run([sys.executable, "-m", "pip", "install", "--upgrade", "torch", "torchvision",
             "--index-url", "https://download.pytorch.org/whl/cu126"], "PyTorch installation", 10)
        run([sys.executable, "-m", "pip", "install", "--upgrade", "diffusers", "transformers",
             "accelerate", "safetensors", "huggingface_hub"], "Diffusers runtime installation", 35)
        check = subprocess.run([sys.executable, "-c",
            "import torch; assert torch.cuda.is_available(), 'CUDA is not available'; print(torch.__version__, torch.cuda.get_device_name(0))"],
            cwd=ROOT, capture_output=True, text=True)
        if check.returncode:
            raise RuntimeError("CUDA PyTorch verification failed: " + (check.stderr.strip()[-1200:] or check.stdout.strip()))
        write("running", "Downloading LTX-Video model weights. This is a very large first-time download…", 55)
        code = ("from huggingface_hub import snapshot_download; "
                f"p=snapshot_download(repo_id={MODEL_ID!r}); print('Model cache:',p)")
        run([sys.executable, "-c", code], "LTX model download", 60)
        write("completed", "AI engine and LTX model weights are installed. Restart Studio, then run a short test generation.", 100)
    except Exception as exc:
        write("failed", str(exc), 0, str(exc))
        with LOG.open("a", encoding="utf-8", errors="replace") as log:
            traceback.print_exc(file=log)

if __name__ == "__main__":
    main()
