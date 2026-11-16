"""Explainable hardware-aware model recommendation for the installed runtimes.

This is a deterministic rule-based advisor, not a trained ML model. A model is
only selectable when it is actually wired into this build and its conservative
resource requirements are met. Runtime checks still run before inference.
"""
from __future__ import annotations
from typing import Any

MODEL_CATALOG: list[dict[str, Any]] = [
    {
        "id": "ltx-video-diffusers",
        "name": "LTX-Video (native Diffusers)",
        "family": "LTX-Video",
        "tasks": ["text-to-video", "image-to-video"],
        "recommended_vram_gb": 12,
        "minimum_planning_vram_gb": 10,
        "recommended_system_ram_gb": 32,
        "disk_gb_estimate": 50,
        "runtime_supported": True,
        "status": "integrated-candidate",
        "precision_options": ["FP16", "BF16 when supported by the GPU"],
        "offload": "Diffusers model CPU offload; inference can be slow and requires Accelerate.",
        "source_url": "https://huggingface.co/docs/diffusers/main/api/pipelines/ltx_video",
        "notes": "The official Diffusers example reports approximately 10 GB VRAM. This project uses a conservative 10 GB minimum gate and validates free VRAM before loading.",
    },
]


def _gb(value: Any) -> float | None:
    try:
        return float(value) / 1024 if value is not None else None
    except (TypeError, ValueError):
        return None


def recommend_models(inventory: dict[str, Any]) -> dict[str, Any]:
    gpu = inventory.get("primary_gpu") or {}
    vram_gb = _gb(gpu.get("vram_total_mb"))
    free_vram_gb = _gb(gpu.get("vram_free_mb"))
    ram_gb = inventory.get("memory_gb")
    disk_free_gb = (inventory.get("disk") or {}).get("free_gb")
    cuda = (inventory.get("compute_runtime") or {}).get("cuda_available")
    gpu_name = gpu.get("name") or "No NVIDIA GPU detected"
    ranked: list[dict[str, Any]] = []
    for model in MODEL_CATALOG:
        reasons: list[str] = []
        blockers: list[str] = []
        floor, recommended = float(model["minimum_planning_vram_gb"]), float(model["recommended_vram_gb"])
        if not model.get("runtime_supported"):
            blockers.append("This model is catalog-only and is not integrated into the current runtime.")
        if vram_gb is None:
            blockers.append("NVIDIA VRAM could not be measured; GPU compatibility cannot be confirmed.")
        elif vram_gb < floor:
            blockers.append(f"Detected {vram_gb:.1f} GB VRAM; the conservative planning floor is {floor:.0f} GB.")
        elif vram_gb < recommended:
            reasons.append(f"VRAM meets the minimum planning floor but is below the {recommended:.0f} GB recommended target.")
        else:
            reasons.append("GPU VRAM meets the recommended planning target.")
        if free_vram_gb is not None and free_vram_gb < 8.5:
            blockers.append(f"Only {free_vram_gb:.1f} GB VRAM is currently free; at least 8.5 GB is required by the runtime safety gate.")
        if ram_gb is not None and float(ram_gb) < float(model["recommended_system_ram_gb"]):
            blockers.append(f"System RAM is below the {model['recommended_system_ram_gb']} GB recommended target.")
        elif ram_gb is not None:
            reasons.append("System RAM meets the recommended target.")
        if disk_free_gb is not None and float(disk_free_gb) < float(model["disk_gb_estimate"]):
            blockers.append(f"Only {disk_free_gb:.1f} GB disk space is free; allow about {model['disk_gb_estimate']} GB.")
        elif disk_free_gb is not None:
            reasons.append("Available disk space meets the estimated model-storage allowance.")
        if cuda is not True:
            blockers.append("CUDA-enabled PyTorch is not available in this Python environment.")
        else:
            reasons.append("PyTorch reports CUDA availability.")
        score = (50 if vram_gb is not None and vram_gb >= recommended else 25 if vram_gb is not None and vram_gb >= floor else 0)
        score += 20 if ram_gb is not None and float(ram_gb) >= float(model["recommended_system_ram_gb"]) else 0
        score += 10 if disk_free_gb is not None and float(disk_free_gb) >= float(model["disk_gb_estimate"]) else 0
        score += 20 if cuda is True else 0
        ranked.append({**model, "compatible_by_planning_rules": not blockers, "score": score,
                       "reasons": reasons, "blockers": blockers})
    eligible = [m for m in ranked if m["compatible_by_planning_rules"]]
    eligible.sort(key=lambda m: (m["score"], -m["recommended_vram_gb"]), reverse=True)
    selected = eligible[0] if eligible else None
    experimental = None
    if selected:
        status = "recommended"
        headline = f"{selected['name']} is the best integrated model match for this hardware."
        caveat = "This is a conservative planning decision, not a guarantee. Start with a short test generation."
    else:
        status = "no-validated-fit"
        headline = "No integrated generative video model is a safe fit for the detected hardware."
        caveat = "Use the built-in image-motion renderer for an offline MP4, or run this app on a GPU meeting the LTX requirements. Image motion is not generative AI."
        if vram_gb is not None and vram_gb >= 4 and vram_gb < floor and ram_gb is not None and float(ram_gb) >= 32:
            experimental = {"id": "ltx-video-2b-experimental", "name": "LTX 2B experimental offload research", "label": "EXPERIMENTAL — NOT ENABLED",
                            "warning": "Not integrated or validated on this GPU. It is deliberately not exposed as a runnable model because a failed multi-GB load would make the application unreliable."}
    return {
        "selector_version": "2.0.0", "selection_method": "explainable-rule-based-runtime-aware-ranking",
        "hardware_summary": {"gpu": gpu_name, "vram_gb": round(vram_gb, 1) if vram_gb is not None else None,
                             "free_vram_gb": round(free_vram_gb, 1) if free_vram_gb is not None else None,
                             "system_ram_gb": ram_gb, "disk_free_gb": disk_free_gb, "cuda_available": cuda},
        "status": status, "headline": headline, "caveat": caveat,
        "selected_model": selected, "experimental_candidate": experimental,
        "ranked_models": ranked, "catalog_count": len(MODEL_CATALOG),
    }
