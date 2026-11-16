"""Hardware telemetry and thermal-safety helpers for native inference."""
import shutil
import subprocess


def nvidia_gpu_metrics():
    """Return first NVIDIA GPU telemetry, or None if nvidia-smi is unavailable."""
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        result = subprocess.run(
            [exe, "--query-gpu=temperature.gpu,memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=5, check=True)
        row = result.stdout.strip().splitlines()[0].split(",")
        return {"temp_c": float(row[0].strip()), "memory_used_mb": float(row[1].strip()),
                "memory_total_mb": float(row[2].strip()), "gpu_util_pct": float(row[3].strip())}
    except Exception:
        return None
