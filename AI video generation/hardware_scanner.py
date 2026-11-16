#!/usr/bin/env python3
"""Cross-platform, dependency-light hardware scanner for Offline Studio.

NVIDIA details are read from nvidia-smi when available. RAM and disk data use
Python/OS APIs. PyTorch is optional and is only used to report CUDA runtime
availability; scanning never installs packages or downloads model weights.
"""
from __future__ import annotations

import argparse
import csv
import ctypes
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _system_memory() -> dict[str, int | None]:
    total = available = None
    if os.name == "nt":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        try:
            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                total, available = int(status.ullTotalPhys), int(status.ullAvailPhys)
        except (AttributeError, OSError):
            pass
    elif hasattr(os, "sysconf"):
        try:
            total = int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES"))
            available = int(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_AVPHYS_PAGES"))
        except (ValueError, OSError, AttributeError):
            pass
    return {"total_bytes": total, "available_bytes": available}


def _nvidia_gpus() -> tuple[list[dict[str, Any]], str | None]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return [], "nvidia-smi was not found; NVIDIA GPU details are unavailable."
    query = (
        "index,name,memory.total,memory.free,memory.used,compute_cap,driver_version,"
        "temperature.gpu,utilization.gpu"
    )
    try:
        result = subprocess.run(
            [exe, f"--query-gpu={query}", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=8, check=True,
        )
        rows = []
        for row in csv.reader(line for line in result.stdout.splitlines() if line.strip()):
            if len(row) < 9:
                continue
            def number(value: str) -> float | None:
                value = value.strip()
                if not value or value.upper() in {"N/A", "[N/A]", "NOT SUPPORTED"}:
                    return None
                try:
                    return float(value)
                except ValueError:
                    return None
            total_mb, free_mb, used_mb = number(row[2]), number(row[3]), number(row[4])
            rows.append({
                "index": int(number(row[0]) or 0),
                "name": row[1].strip(),
                "vram_total_mb": total_mb,
                "vram_free_mb": free_mb,
                "vram_used_mb": used_mb,
                "compute_capability": row[5].strip() if row[5].strip() not in {"N/A", "[N/A]"} else None,
                "driver_version": row[6].strip() if row[6].strip() not in {"N/A", "[N/A]"} else None,
                "temperature_c": number(row[7]),
                "utilization_pct": number(row[8]),
            })
        return rows, None if rows else "nvidia-smi did not report an NVIDIA GPU."
    except subprocess.TimeoutExpired:
        return [], "nvidia-smi timed out while scanning the GPU."
    except (subprocess.CalledProcessError, OSError) as exc:
        detail = (getattr(exc, "stderr", None) or str(exc)).strip()
        return [], f"Could not query NVIDIA GPU: {detail[:300]}"


def _cuda_runtime() -> dict[str, Any]:
    info: dict[str, Any] = {"pytorch_installed": False, "cuda_available": False,
                            "pytorch_version": None, "cuda_version": None, "device_count": 0}
    try:
        import torch  # optional; do not make scanner depend on torch
        info.update({
            "pytorch_installed": True,
            "cuda_available": bool(torch.cuda.is_available()),
            "pytorch_version": str(torch.__version__),
            "cuda_version": str(torch.version.cuda) if torch.version.cuda else None,
            "device_count": int(torch.cuda.device_count()),
        })
    except Exception as exc:  # optional diagnostic only
        info["check_note"] = f"PyTorch CUDA check unavailable: {type(exc).__name__}"
    return info


def scan_hardware(project_dir: str | Path | None = None, include_torch: bool = True) -> dict[str, Any]:
    """Return a JSON-serializable hardware inventory without changing the PC."""
    root = Path(project_dir or Path(__file__).resolve().parent)
    memory = _system_memory()
    gpus, gpu_note = _nvidia_gpus()
    disk = shutil.disk_usage(root if root.exists() else Path.cwd())
    cpu_count = os.cpu_count()
    primary = max(gpus, key=lambda g: (g.get("vram_total_mb") or 0), default=None)
    result: dict[str, Any] = {
        "schema_version": 1,
        "scanned_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "system": {"os": platform.platform(), "python": platform.python_version(),
                   "cpu": platform.processor() or platform.machine(), "logical_cpu_cores": cpu_count},
        "memory": memory,
        "memory_gb": round(memory["total_bytes"] / (1024 ** 3), 1) if memory["total_bytes"] else None,
        "disk": {"path": str(root.resolve()), "total_bytes": disk.total,
                 "free_bytes": disk.free, "free_gb": round(disk.free / (1024 ** 3), 1)},
        "gpus": gpus,
        "primary_gpu": primary,
        "gpu_detected": bool(gpus),
        "gpu_scan_note": gpu_note,
    }
    if include_torch:
        result["compute_runtime"] = _cuda_runtime()
    return result


def _print_report(data: dict[str, Any]) -> None:
    print("\nOFFLINE STUDIO — HARDWARE SCAN")
    print("=" * 42)
    print(f"OS:       {data['system']['os']}")
    print(f"CPU:      {data['system']['cpu']} ({data['system']['logical_cpu_cores']} logical cores)")
    print(f"RAM:      {data['memory_gb'] if data['memory_gb'] is not None else 'Unknown'} GB")
    print(f"Disk:     {data['disk']['free_gb']} GB free")
    if data["gpus"]:
        for gpu in data["gpus"]:
            total = gpu.get("vram_total_mb")
            free = gpu.get("vram_free_mb")
            print(f"GPU {gpu['index']}:   {gpu['name']}")
            print(f"VRAM:     {total / 1024:.1f} GB total / {free / 1024:.1f} GB free" if total and free is not None else "VRAM:     Unknown")
            print(f"Compute:  {gpu.get('compute_capability') or 'Unknown'} | Driver: {gpu.get('driver_version') or 'Unknown'}")
    else:
        print(f"GPU:      Not detected ({data.get('gpu_scan_note')})")
    runtime = data.get("compute_runtime", {})
    print(f"PyTorch:  {runtime.get('pytorch_version') or 'Not installed'}")
    print(f"CUDA:     {'Available' if runtime.get('cuda_available') else 'Not available'} ({runtime.get('cuda_version') or 'no runtime detected'})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan hardware for Offline Studio model recommendations.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument("--no-torch", action="store_true", help="Skip optional PyTorch/CUDA check")
    args = parser.parse_args()
    inventory = scan_hardware(include_torch=not args.no_torch)
    if args.json:
        print(json.dumps(inventory, indent=2))
    else:
        _print_report(inventory)
