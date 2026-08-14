from __future__ import annotations
import os, platform, shutil, subprocess
from dataclasses import dataclass

@dataclass
class Hardware:
    ram_gb: float
    gpu_name: str
    vram_gb: float
    free_gb: float
    os_name: str

def _nvidia():
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], text=True, stderr=subprocess.DEVNULL, timeout=4).strip().splitlines()
        if out:
            name, vram = [x.strip() for x in out[0].split(",", 1)]
            return name, float(vram) / 1024
    except Exception:
        pass
    return "No NVIDIA GPU detected", 0.0

def detect():
    ram = 0.0
    try:
        import psutil
        ram = psutil.virtual_memory().total / (1024**3)
    except Exception:
        pass
    gpu, vram = _nvidia()
    free = shutil.disk_usage(os.getcwd()).free / (1024**3)
    return Hardware(ram, gpu, vram, free, platform.platform())

def recommended_model(hw: Hardware):
    if hw.vram_gb >= 16 and hw.ram_gb >= 32 and hw.free_gb >= 25:
        return "qwen3:30b", 19.0, "High quality"
    if hw.vram_gb >= 10 and hw.ram_gb >= 24 and hw.free_gb >= 15:
        return "qwen3:14b", 9.3, "Recommended"
    if hw.ram_gb >= 16 and hw.free_gb >= 10:
        return "qwen3:8b", 5.2, "Recommended"
    return "qwen3:4b", 2.6, "Lightweight"

def model_options():
    return [("qwen3:4b", 2.6, "Lightweight"), ("qwen3:8b", 5.2, "Balanced"), ("qwen3:14b", 9.3, "High quality"), ("qwen3:30b", 19.0, "High quality MoE")]
