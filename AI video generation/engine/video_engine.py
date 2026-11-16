"""Native video generation adapters for OfflineYouTubeStudio.

Hardware inventory is produced by hardware_scanner.py, evaluated by
model_selector.py, and enforced again here immediately before inference.
Image Motion remains an explicitly non-generative media renderer.
"""
from __future__ import annotations

import math
import os
import random
import threading
from pathlib import Path
from typing import Any, Callable
from safe_mode import nvidia_gpu_metrics
from model_selector import recommend_models

LTX_MODEL_ID = os.environ.get("OFFLINE_STUDIO_LTX_MODEL", "Lightricks/LTX-Video")
LTX_MIN_VRAM_GB = 10.0
LTX_MIN_FREE_VRAM_GB = 8.5


def ltx_capability(inventory: dict[str, Any]) -> dict[str, Any]:
    """Return runtime eligibility from the same selector used by the UI/API.

    This prevents the scanner, model advisor, production endpoint and inference
    engine from maintaining different hardware rules.
    """
    recommendation = recommend_models(inventory)
    selected = recommendation.get("selected_model")
    candidate = next((item for item in recommendation.get("ranked_models", [])
                      if item.get("id") == "ltx-video-diffusers"), None)
    blockers = list(candidate.get("blockers", [])) if candidate else [
        "LTX is not present in the integrated model catalog."
    ]
    available = bool(selected and selected.get("id") == "ltx-video-diffusers" and not blockers)
    return {
        "available": available,
        "selected_model_id": selected.get("id") if selected else None,
        "model_id": LTX_MODEL_ID,
        "model_name": "LTX-Video (Diffusers native pipeline)",
        "minimum_vram_gb": LTX_MIN_VRAM_GB,
        "minimum_free_vram_gb": LTX_MIN_FREE_VRAM_GB,
        "blockers": blockers,
        "selector_status": recommendation.get("status"),
        "note": "Hardware scan → model selector → this runtime gate. First inference downloads model weights; cached weights can be used offline.",
    }


def _aspect_size(aspect: str, target: int = 512) -> tuple[int, int]:
    ratios = {"16:9": (16, 9), "9:16": (9, 16), "1:1": (1, 1), "4:3": (4, 3), "3:2": (3, 2)}
    rw, rh = ratios.get(aspect, (16, 9))
    if rw >= rh:
        width, height = target, max(64, int(target * rh / rw))
    else:
        height, width = target, max(64, int(target * rw / rh))
    return max(64, width - width % 32), max(64, height - height % 32)


def render_image_motion(
    image_path: str | Path, output_path: str | Path, *, duration: float = 4.0,
    fps: int = 24, aspect: str = "16:9", motion: str = "balanced",
    cancel_event: threading.Event | None = None,
    progress: Callable[[float, str], None] | None = None,
) -> Path:
    """Create an MP4 from a still image; this is not generative AI."""
    try:
        from PIL import Image, ImageOps
        import imageio_ffmpeg
    except ImportError as exc:
        raise RuntimeError("Image-motion mode needs Pillow and imageio-ffmpeg. Run ONE_CLICK.bat install.") from exc
    source, destination = Path(image_path), Path(output_path)
    if not source.is_file():
        raise RuntimeError("The selected reference image could not be found.")
    duration, fps = min(max(float(duration), 2.0), 12.0), min(max(int(fps), 12), 30)
    width, height = _aspect_size(aspect, 640)
    total_frames = int(duration * fps)
    motion_factor = {"subtle": 0.035, "balanced": 0.075, "dynamic": 0.12}.get(motion, 0.075)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as opened:
        base = ImageOps.exif_transpose(opened).convert("RGB")
        scale = max(width / base.width, height / base.height)
        base = base.resize((math.ceil(base.width * scale), math.ceil(base.height * scale)), Image.Resampling.LANCZOS)
        if base.width < width or base.height < height:
            base = ImageOps.fit(base, (width, height), method=Image.Resampling.LANCZOS)
    writer = imageio_ffmpeg.write_frames(str(destination), (width, height), fps=fps,
        codec="libx264", pix_fmt_in="rgb24", pix_fmt_out="yuv420p", quality=8, macro_block_size=1)
    writer.send(None)
    try:
        for index in range(total_frames):
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("Generation cancelled by user.")
            t = index / max(1, total_frames - 1)
            eased = 0.5 - 0.5 * math.cos(math.pi * t)
            zoom = 1.0 + motion_factor * eased
            crop_w, crop_h = max(width, int(base.width / zoom)), max(height, int(base.height / zoom))
            left = int(max(0, base.width - crop_w) * (0.5 + 0.12 * math.sin(t * math.pi)))
            top = int(max(0, base.height - crop_h) * (0.5 - 0.08 * math.sin(t * math.pi)))
            frame = base.crop((left, top, left + crop_w, top + crop_h)).resize((width, height), Image.Resampling.LANCZOS)
            writer.send(frame.tobytes())
            if progress and (index % max(1, fps // 2) == 0 or index == total_frames - 1):
                progress((index + 1) / total_frames, f"Rendering frame {index + 1}/{total_frames}")
    finally:
        writer.close()
    if not destination.exists() or destination.stat().st_size < 1024:
        raise RuntimeError("MP4 encoder did not produce a valid output file.")
    return destination


class LTXRuntime:
    """Lazy in-process LTX Diffusers runtime. Model weights are cached by HF Hub."""
    def __init__(self) -> None:
        self._pipeline = None
        self._lock = threading.Lock()

    def generate(self, prompt: str, output_path: str | Path, *, image_path: str | Path | None = None,
        duration: float = 3.0, fps: int = 24, aspect: str = "16:9", seed: int | None = None,
        cancel_event: threading.Event | None = None,
        progress: Callable[[float, str], None] | None = None) -> Path:
        try:
            import torch
            from diffusers import LTXPipeline, AutoModel
            from diffusers.hooks import apply_group_offloading
            from diffusers.utils import export_to_video, load_image
        except ImportError as exc:
            raise RuntimeError("Native LTX needs CUDA PyTorch, diffusers, transformers and accelerate. Run ONE_CLICK.bat install-ltx on compatible hardware.") from exc
        if not torch.cuda.is_available():
            raise RuntimeError("LTX generation requires CUDA; CPU inference is disabled for this model.")
        with self._lock:
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("Generation cancelled by user.")
            if self._pipeline is None:
                if progress:
                    progress(0.02, "Loading LTX model (first load may download weights)")
                dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
                transformer = AutoModel.from_pretrained(LTX_MODEL_ID, subfolder="transformer", dtype=dtype)
                self._pipeline = LTXPipeline.from_pretrained(LTX_MODEL_ID, transformer=transformer, dtype=dtype)
                self._pipeline.transformer.enable_group_offload(onload_device=torch.device("cuda"),
                    offload_device=torch.device("cpu"), offload_type="leaf_level", use_stream=False)
                apply_group_offloading(self._pipeline.text_encoder, onload_device=torch.device("cuda"),
                    offload_type="block_level", num_blocks_per_group=2)
                apply_group_offloading(self._pipeline.vae, onload_device=torch.device("cuda"),
                    offload_type="leaf_level")
                if hasattr(self._pipeline.vae, "enable_tiling"):
                    self._pipeline.vae.enable_tiling()
            width, height = _aspect_size(aspect, 512)
            runtime_fps = min(int(fps), 12)
            frames = min(49, max(9, int(round(duration * runtime_fps / 8)) * 8 + 1))
            generator = torch.Generator(device="cpu").manual_seed(
                seed if seed is not None and seed >= 0 else random.randint(0, 2**31 - 1))
            kwargs: dict[str, Any] = {"prompt": prompt, "width": width, "height": height,
                "num_frames": frames, "num_inference_steps": 20, "guidance_scale": 3.0,
                "generator": generator}
            if image_path:
                kwargs["image"] = load_image(str(image_path))
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("Generation cancelled by user.")
            if progress:
                progress(0.1, "Running LTX inference")
            def on_step_end(pipe, step_index, timestep, callback_kwargs):
                if cancel_event and cancel_event.is_set():
                    raise RuntimeError("Generation cancelled by user.")
                metrics = nvidia_gpu_metrics()
                max_temp = float(os.environ.get("OFFLINE_STUDIO_MAX_GPU_TEMP", "80"))
                if metrics and metrics.get("temp_c", 0) >= max_temp:
                    raise RuntimeError(f"Thermal safety stop: GPU reached {metrics['temp_c']:.0f}°C (limit {max_temp:.0f}°C).")
                if progress:
                    progress(0.1 + 0.78 * (step_index + 1) / 20, f"LTX denoising step {step_index + 1}/20")
                return callback_kwargs
            kwargs["callback_on_step_end"] = on_step_end
            try:
                result = self._pipeline(**kwargs)
            except Exception as exc:
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                if "out of memory" in str(exc).lower():
                    self._pipeline = None
                raise
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("Generation cancelled by user.")
            destination = Path(output_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            export_to_video(result.frames[0], str(destination), fps=runtime_fps)
            if progress:
                progress(1.0, "Video encoded")
            return destination


_ltx_runtime = LTXRuntime()


def generate_video(task: dict[str, Any], output_path: str | Path, *,
                   cancel_event: threading.Event | None = None,
                   progress: Callable[[float, str], None] | None = None) -> dict[str, Any]:
    mode = task.get("mode", "text")
    if mode == "image-motion":
        path = render_image_motion(task.get("image_path", ""), output_path,
            duration=task.get("duration", 4), fps=task.get("fps", 24),
            aspect=task.get("aspect", "16:9"), motion=task.get("motion", "balanced"),
            cancel_event=cancel_event, progress=progress)
        return {"path": str(path), "engine": "image-motion-renderer", "is_generative_ai": False,
                "description": "Still-image camera-motion render; not diffusion-generated video."}
    if mode not in {"text", "image"}:
        raise RuntimeError("Unsupported generation mode.")
    if mode == "image" and not task.get("image_path"):
        raise RuntimeError("Image-to-video requires a reference image.")
    inventory = task.get("inventory") or {}
    capability = ltx_capability(inventory)
    if not capability["available"]:
        raise RuntimeError("No integrated generative model is eligible: " + " ".join(capability["blockers"]) +
                           " Image Motion is a separate non-generative option.")
    path = _ltx_runtime.generate(task.get("prompt", ""), output_path,
        image_path=task.get("image_path") if mode == "image" else None,
        duration=task.get("duration", 3), fps=task.get("fps", 24),
        aspect=task.get("aspect", "16:9"), seed=task.get("seed"),
        cancel_event=cancel_event, progress=progress)
    return {"path": str(path), "engine": "ltx-diffusers-native", "is_generative_ai": True,
            "model_id": LTX_MODEL_ID}
