"""Native video generation adapters for OfflineYouTubeStudio.

LTX inference runs in-process through Hugging Face Diffusers when the machine
passes a conservative hardware gate. The low-resource image-motion renderer is
an honest non-generative fallback: it animates a supplied still image with a
Ken Burns camera move and encodes MP4 locally.
"""
from __future__ import annotations

import math
import os
import random
import threading
from pathlib import Path
from typing import Any, Callable
from safe_mode import nvidia_gpu_metrics

LTX_MODEL_ID = os.environ.get("OFFLINE_STUDIO_LTX_MODEL", "Lightricks/LTX-Video")
LTX_MIN_VRAM_GB = 10.0  # Diffusers' published LTX example reports about 10 GB VRAM.
LTX_MIN_FREE_VRAM_GB = 8.5


def ltx_capability(inventory: dict[str, Any]) -> dict[str, Any]:
    gpu = inventory.get("primary_gpu") or {}
    total_mb = gpu.get("vram_total_mb")
    free_mb = gpu.get("vram_free_mb")
    runtime = inventory.get("compute_runtime") or {}
    total = float(total_mb) / 1024 if total_mb is not None else None
    free = float(free_mb) / 1024 if free_mb is not None else None
    blockers: list[str] = []
    if not gpu:
        blockers.append("No supported NVIDIA GPU was detected.")
    if runtime.get("cuda_available") is not True:
        blockers.append("CUDA-enabled PyTorch is not available in this Python environment.")
    if total is None or total < LTX_MIN_VRAM_GB:
        blockers.append(f"LTX is gated at {LTX_MIN_VRAM_GB:g} GB total VRAM; detected {total if total is not None else 'unknown'} GB.")
    if free is not None and free < LTX_MIN_FREE_VRAM_GB:
        blockers.append(f"Only {free:.1f} GB VRAM is currently free; at least {LTX_MIN_FREE_VRAM_GB:.1f} GB is required by this safety profile.")
    disk_free = (inventory.get("disk") or {}).get("free_gb")
    if disk_free is not None and float(disk_free) < 50:
        blockers.append("At least 50 GB free disk space is required for model weights and temporary files.")
    return {
        "available": not blockers,
        "model_id": LTX_MODEL_ID,
        "model_name": "LTX-Video (Diffusers native pipeline)",
        "minimum_vram_gb": LTX_MIN_VRAM_GB,
        "minimum_free_vram_gb": LTX_MIN_FREE_VRAM_GB,
        "blockers": blockers,
        "note": "First use downloads model weights; after the weights are cached, inference can run offline.",
    }


def _aspect_size(aspect: str, target: int = 512) -> tuple[int, int]:
    ratios = {"16:9": (16, 9), "9:16": (9, 16), "1:1": (1, 1), "4:3": (4, 3), "3:2": (3, 2)}
    rw, rh = ratios.get(aspect, (16, 9))
    if rw >= rh:
        width, height = target, max(64, int(target * rh / rw))
    else:
        height, width = target, max(64, int(target * rw / rh))
    # LTX VAE requires dimensions divisible by 32.
    return max(64, width - width % 32), max(64, height - height % 32)


def render_image_motion(
    image_path: str | Path,
    output_path: str | Path,
    *,
    duration: float = 4.0,
    fps: int = 24,
    aspect: str = "16:9",
    motion: str = "balanced",
    cancel_event: threading.Event | None = None,
    progress: Callable[[float, str], None] | None = None,
) -> Path:
    """Create a real MP4 from a still image using deterministic camera motion.

    This is a media-rendering fallback, not diffusion-based AI video synthesis.
    """
    try:
        from PIL import Image, ImageOps
        import imageio_ffmpeg
    except ImportError as exc:
        raise RuntimeError("Image-motion mode needs Pillow and imageio-ffmpeg. Run ONE_CLICK.bat install.") from exc

    source = Path(image_path)
    destination = Path(output_path)
    if not source.is_file():
        raise RuntimeError("The selected reference image could not be found.")
    duration = min(max(float(duration), 2.0), 12.0)
    fps = min(max(int(fps), 12), 30)
    width, height = _aspect_size(aspect, 640)
    total_frames = int(duration * fps)
    motion_factor = {"subtle": 0.035, "balanced": 0.075, "dynamic": 0.12}.get(motion, 0.075)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(source) as opened:
        base = ImageOps.exif_transpose(opened).convert("RGB")
        # Cover the output canvas before applying a smooth crop/zoom.
        scale = max(width / base.width, height / base.height)
        base = base.resize((math.ceil(base.width * scale), math.ceil(base.height * scale)), Image.Resampling.LANCZOS)
        if base.width < width or base.height < height:
            base = ImageOps.fit(base, (width, height), method=Image.Resampling.LANCZOS)

    # imageio-ffmpeg supplies the encoder binary inside the Python environment.
    writer = imageio_ffmpeg.write_frames(
        str(destination), (width, height), fps=fps, codec="libx264",
        pix_fmt_in="rgb24", pix_fmt_out="yuv420p", quality=8,
        macro_block_size=1,
    )
    writer.send(None)
    try:
        max_zoom = 1.0 + motion_factor
        for index in range(total_frames):
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("Generation cancelled by user.")
            t = index / max(1, total_frames - 1)
            # Smooth zoom and a gentle diagonal camera drift.
            eased = 0.5 - 0.5 * math.cos(math.pi * t)
            zoom = 1.0 + (max_zoom - 1.0) * eased
            crop_w = max(width, int(base.width / zoom))
            crop_h = max(height, int(base.height / zoom))
            drift_x = 0.5 + 0.12 * math.sin(t * math.pi)
            drift_y = 0.5 - 0.08 * math.sin(t * math.pi)
            max_x = max(0, base.width - crop_w)
            max_y = max(0, base.height - crop_h)
            left = int(max_x * drift_x)
            top = int(max_y * drift_y)
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

    def generate(
        self, prompt: str, output_path: str | Path, *, image_path: str | Path | None = None,
        duration: float = 3.0, fps: int = 24, aspect: str = "16:9", seed: int | None = None,
        cancel_event: threading.Event | None = None,
        progress: Callable[[float, str], None] | None = None,
    ) -> Path:
        try:
            import torch
            from diffusers import LTXPipeline, AutoModel
            from diffusers.hooks import apply_group_offloading
            from diffusers.utils import export_to_video, load_image
        except ImportError as exc:
            raise RuntimeError("Native LTX needs CUDA PyTorch, diffusers, transformers and accelerate. Run ONE_CLICK.bat install-ltx on a compatible GPU.") from exc
        if not torch.cuda.is_available():
            raise RuntimeError("LTX generation requires CUDA. The CPU-only mode is not enabled for this large video model.")
        with self._lock:
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("Generation cancelled by user.")
            if self._pipeline is None:
                if progress:
                    progress(0.02, "Loading LTX model (first load may download weights)")
                dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
                transformer = AutoModel.from_pretrained(
                    LTX_MODEL_ID, subfolder="transformer", dtype=dtype
                )
                self._pipeline = LTXPipeline.from_pretrained(
                    LTX_MODEL_ID, transformer=transformer, dtype=dtype
                )
                # Follow Diffusers' documented LTX memory profile: stream model
                # groups between host RAM and CUDA rather than placing every
                # component on the GPU at once.
                onload = torch.device("cuda")
                offload = torch.device("cpu")
                self._pipeline.transformer.enable_group_offload(
                    onload_device=onload, offload_device=offload,
                    offload_type="leaf_level", use_stream=False
                )
                apply_group_offloading(
                    self._pipeline.text_encoder, onload_device=onload,
                    offload_type="block_level", num_blocks_per_group=2
                )
                apply_group_offloading(
                    self._pipeline.vae, onload_device=onload,
                    offload_type="leaf_level"
                )
                if hasattr(self._pipeline, "vae") and hasattr(self._pipeline.vae, "enable_tiling"):
                    self._pipeline.vae.enable_tiling()
            width, height = _aspect_size(aspect, 512)
            # Keep LTX clips short and cap output rate to reduce temporal memory use.
            runtime_fps = min(int(fps), 12)
            frames = max(9, int(round(duration * runtime_fps / 8)) * 8 + 1)
            frames = min(frames, 49)
            generator = torch.Generator(device="cpu").manual_seed(seed if seed is not None and seed >= 0 else random.randint(0, 2**31 - 1))
            kwargs: dict[str, Any] = {
                "prompt": prompt,
                "width": width,
                "height": height,
                "num_frames": frames,
                "num_inference_steps": 20,
                "guidance_scale": 3.0,
                "generator": generator,
            }
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
                    self._pipeline = None  # Release the cached pipeline before the next attempt.
                raise
            if cancel_event and cancel_event.is_set():
                raise RuntimeError("Generation cancelled by user.")
            frames_out = result.frames[0]
            destination = Path(output_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            export_to_video(frames_out, str(destination), fps=runtime_fps)
            if progress:
                progress(1.0, "Video encoded")
            return destination


_ltx_runtime = LTXRuntime()


def generate_video(task: dict[str, Any], output_path: str | Path, *,
                   cancel_event: threading.Event | None = None,
                   progress: Callable[[float, str], None] | None = None) -> dict[str, Any]:
    mode = task.get("mode", "text")
    if mode == "image-motion":
        path = render_image_motion(
            task.get("image_path", ""), output_path,
            duration=task.get("duration", 4), fps=task.get("fps", 24),
            aspect=task.get("aspect", "16:9"), motion=task.get("motion", "balanced"),
            cancel_event=cancel_event, progress=progress,
        )
        return {"path": str(path), "engine": "image-motion-renderer", "is_generative_ai": False,
                "description": "Still-image camera-motion render; not diffusion-generated video."}

    if mode not in {"text", "image"}:
        raise RuntimeError("Unsupported generation mode.")
    if mode == "image" and not task.get("image_path"):
        raise RuntimeError("Image-to-video requires a reference image.")
    inventory = task.get("inventory") or {}
    capability = ltx_capability(inventory)
    if not capability["available"]:
        raise RuntimeError("Native LTX is not enabled on this hardware: " + " ".join(capability["blockers"]) +
                           " Use Image Motion mode for a local MP4, or use a GPU that meets the LTX hardware gate.")
    path = _ltx_runtime.generate(
        task.get("prompt", ""), output_path,
        image_path=task.get("image_path") if mode == "image" else None,
        duration=task.get("duration", 3), fps=task.get("fps", 24),
        aspect=task.get("aspect", "16:9"), seed=task.get("seed"),
        cancel_event=cancel_event, progress=progress,
    )
    return {"path": str(path), "engine": "ltx-diffusers-native", "is_generative_ai": True,
            "model_id": LTX_MODEL_ID}