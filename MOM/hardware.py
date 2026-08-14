import os, shutil, subprocess, psutil

MODELS = {
    "qwen3:4b": {"min_ram": 8, "min_vram": 0, "size": "~2.6 GB", "tier": "CPU / entry GPU"},
    "qwen3:8b": {"min_ram": 16, "min_vram": 6, "size": "~5.2 GB", "tier": "balanced"},
    "qwen3:14b": {"min_ram": 24, "min_vram": 10, "size": "~9.3 GB", "tier": "high quality"},
    "qwen3:30b": {"min_ram": 48, "min_vram": 20, "size": "~19 GB", "tier": "high-end"},
}

def nvidia_info():
    if not shutil.which("nvidia-smi"):
        return {"available": False, "name": "No NVIDIA GPU detected", "vram_gb": 0.0}
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], text=True, timeout=5)
        name, vram = out.strip().splitlines()[0].split(",")
        return {"available": True, "name": name.strip(), "vram_gb": round(float(vram.strip()) / 1024, 1)}
    except Exception:
        return {"available": False, "name": "NVIDIA GPU (details unavailable)", "vram_gb": 0.0}

def detect():
    gpu = nvidia_info()
    ram = round(psutil.virtual_memory().total / (1024**3), 1)
    disk = round(psutil.disk_usage(os.getcwd()).free / (1024**3), 1)
    return {"ram_gb": ram, "free_disk_gb": disk, "gpu": gpu}

def recommended_model(hw=None):
    hw = hw or detect(); ram = hw["ram_gb"]; vram = hw["gpu"]["vram_gb"]
    if vram >= 20 and ram >= 48: return "qwen3:30b"
    if vram >= 10 and ram >= 24: return "qwen3:14b"
    if vram >= 6 and ram >= 16: return "qwen3:8b"
    if ram >= 16: return "qwen3:8b"
    return "qwen3:4b"

def ollama_installed():
    return shutil.which("ollama") is not None

def installed_models():
    if not ollama_installed(): return []
    try:
        out = subprocess.check_output(["ollama", "list"], text=True, timeout=10)
        lines = out.splitlines()[1:]
        return [line.split()[0] for line in lines if line.strip()]
    except Exception:
        return []

def pull_model(model):
    if not ollama_installed(): raise RuntimeError("Ollama is not installed. Install Ollama first.")
    subprocess.run(["ollama", "pull", model], check=True)
    return model
