#!/usr/bin/env python3
"""OfflineYouTubeStudio local web server and native inference API.

No external workflow server is required. The optional LTX pipeline executes
inside this Python process; low-VRAM systems can render image-motion MP4s.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import threading
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from hardware_scanner import scan_hardware
from model_selector import recommend_models
from engine.video_engine import ltx_capability
from engine.job_manager import JobManager

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web" / "index.html"
OUTPUTS = ROOT / "outputs"
UPLOADS = ROOT / "uploads"
PORT = int(os.environ.get("STUDIO_PORT", "8765"))
MAX_BODY = 28 * 1024 * 1024
MAX_IMAGE_BYTES = 20 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
MAX_PROMPT_CHARS = 2000
ALLOWED_ASPECTS = {"16:9", "9:16", "1:1", "4:3", "3:2"}
ALLOWED_MOTIONS = {"subtle", "balanced", "dynamic"}
OUTPUTS.mkdir(exist_ok=True)
UPLOADS.mkdir(exist_ok=True)
JOBS = JobManager(OUTPUTS)


def machine_report() -> dict:
    inventory = scan_hardware(ROOT)
    recommendation = recommend_models(inventory)
    capability = ltx_capability(inventory)
    gpu = inventory.get("primary_gpu") or {}
    total = gpu.get("vram_total_mb")
    free = gpu.get("vram_free_mb")
    if gpu:
        gpu_name = gpu.get("name", "NVIDIA GPU detected")
        vram = f"{total / 1024:.1f} GB total VRAM" if total else "VRAM unknown"
        if free is not None:
            vram += f" · {free / 1024:.1f} GB free"
        if gpu.get("temperature_c") is not None:
            vram += f" · {gpu['temperature_c']:.0f}°C"
    else:
        gpu_name, vram = "No NVIDIA GPU detected", "VRAM unknown"
    ram = inventory.get("memory_gb")
    return {
        "gpu": gpu_name, "vram": vram,
        "ram": f"{ram:g} GB" if ram is not None else "Unknown",
        "inventory": inventory, "recommendation": recommendation,
        "ltx": capability,
        "fallback": {"available": True, "id": "image-motion-renderer",
                     "name": "Image Motion Renderer", "is_generative_ai": False,
                     "description": "Creates an MP4 from an uploaded still image using a smooth camera move."},
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "OfflineYouTubeStudio/2.0"

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")

    def _send(self, status: int, payload: dict, content_type: str = "application/json; charset=utf-8"):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(raw)

    def _json_body(self) -> dict:
        size = int(self.headers.get("Content-Length", "0"))
        if size <= 0 or size > MAX_BODY:
            raise ValueError("Request body is empty or exceeds the 28 MB limit.")
        return json.loads(self.rfile.read(size).decode("utf-8"))

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/":
            if not WEB.exists():
                self._send(500, {"error": "web/index.html is missing"}); return
            raw = WEB.read_bytes()
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers(); self.wfile.write(raw); return
        if path == "/api/config":
            self._send(200, {"limits": {"max_prompt_chars": MAX_PROMPT_CHARS, "max_image_mb": MAX_IMAGE_BYTES // (1024 * 1024), "max_image_pixels": MAX_IMAGE_PIXELS, "max_waiting_jobs": JOBS.max_pending}, "modes": ["text", "image", "image-motion"], "aspects": sorted(ALLOWED_ASPECTS)})
            return
        if path in {"/api/health", "/api/hardware", "/api/models"}:
            report = machine_report()
            if path == "/api/hardware": self._send(200, report["inventory"])
            elif path == "/api/models": self._send(200, {"recommendation": report["recommendation"], "ltx": report["ltx"], "fallback": report["fallback"]})
            else: self._send(200, {"studio": True, "engine": "native-python", "hardware": report,
                                   "jobs": JOBS.list(5)})
            return
        if path == "/api/jobs":
            self._send(200, {"jobs": JOBS.list(30)}); return
        if path.startswith("/api/jobs/"):
            job_id = path.rsplit("/", 1)[-1]
            job = JOBS.get(job_id)
            if not job: self._send(404, {"error": "Job not found"})
            else: self._send(200, job)
            return
        if path.startswith("/outputs/"):
            name = Path(path.rsplit("/", 1)[-1]).name
            target = (OUTPUTS / name).resolve()
            if target.parent != OUTPUTS.resolve() or not target.is_file():
                self._send(404, {"error": "Output not found"}); return
            file_size = target.stat().st_size
            range_header = self.headers.get("Range")
            start, end, status = 0, file_size - 1, 200
            if range_header and range_header.startswith("bytes="):
                try:
                    first, last = range_header[6:].split("-", 1)
                    if first:
                        start = int(first)
                        end = int(last) if last else file_size - 1
                    else:
                        suffix_length = int(last)
                        start = max(0, file_size - suffix_length)
                        end = file_size - 1
                    if start < 0 or start >= file_size or end < start:
                        raise ValueError("Invalid byte range")
                    end = min(end, file_size - 1)
                    status = 206
                except (ValueError, TypeError):
                    self.send_response(416); self.send_header("Content-Range", f"bytes */{file_size}")
                    self.send_header("Content-Length", "0"); self.end_headers(); return
            length = end - start + 1
            self.send_response(status); self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(length)); self.send_header("Accept-Ranges", "bytes")
            if status == 206: self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
            self.end_headers()
            with target.open("rb") as stream:
                stream.seek(start)
                remaining = length
                while remaining:
                    chunk = stream.read(min(1024 * 1024, remaining))
                    if not chunk: break
                    self.wfile.write(chunk); remaining -= len(chunk)
            return
        self._send(404, {"error": "Not found"})

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        if path.startswith("/api/jobs/") and path.endswith("/cancel"):
            job_id = path.split("/")[-2]
            if JOBS.cancel(job_id): self._send(200, {"cancelled": True, "job_id": job_id})
            else: self._send(409, {"error": "Job cannot be cancelled because it is no longer active."})
            return
        if path != "/api/generate":
            self._send(404, {"error": "Not found"}); return
        image_path = None
        try:
            body = self._json_body()
            if not isinstance(body, dict):
                self._send(400, {"error": "Request JSON must be an object."}); return
            mode = str(body.get("mode", "text"))
            prompt = str(body.get("prompt", "")).strip()
            if len(prompt) > MAX_PROMPT_CHARS:
                self._send(400, {"error": f"Prompt is too long (maximum {MAX_PROMPT_CHARS} characters)."}); return
            if mode not in {"text", "image", "image-motion"}:
                self._send(400, {"error": "Mode must be text, image, or image-motion."}); return
            if mode in {"text", "image"} and not prompt:
                self._send(400, {"error": "A prompt is required for LTX generation."}); return
            if mode == "image-motion" and not prompt:
                prompt = "Image motion render"
            inventory = scan_hardware(ROOT)
            if mode in {"text", "image"}:
                cap = ltx_capability(inventory)
                if not cap["available"]:
                    self._send(409, {"error": "Native LTX generation is not available on this PC.", "blockers": cap["blockers"],
                                     "alternative": "Select Image Motion mode and upload a still image for a locally rendered MP4."}); return
            if mode in {"image", "image-motion"}:
                data_url = str(body.get("image_data", ""))
                match = re.fullmatch(r"data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)", data_url)
                if not match:
                    self._send(400, {"error": "Upload a PNG, JPEG or WebP image first."}); return
                raw = base64.b64decode(match.group(2), validate=True)
                if len(raw) > MAX_IMAGE_BYTES:
                    self._send(413, {"error": "Image exceeds the 20 MB limit."}); return
                suffix = {"png": ".png", "jpeg": ".jpg", "webp": ".webp"}[match.group(1)]
                image_path = UPLOADS / f"{uuid.uuid4().hex}{suffix}"
                image_path.write_bytes(raw)
                try:
                    from PIL import Image
                    with Image.open(image_path) as img:
                        if img.width * img.height > MAX_IMAGE_PIXELS:
                            raise ValueError("Image dimensions exceed the 40-megapixel safety limit.")
                        img.verify()
                except Exception:
                    image_path.unlink(missing_ok=True)
                    self._send(400, {"error": "The uploaded file is not a valid image."}); return
            aspect = str(body.get("aspect", "16:9"))
            motion = str(body.get("motion", "balanced"))
            if aspect not in ALLOWED_ASPECTS:
                if image_path: image_path.unlink(missing_ok=True)
                self._send(400, {"error": "Unsupported aspect ratio."}); return
            if motion not in ALLOWED_MOTIONS:
                if image_path: image_path.unlink(missing_ok=True)
                self._send(400, {"error": "Unsupported camera motion preset."}); return
            try:
                import math
                duration = float(body.get("duration", 4))
                fps = int(body.get("fps", 24))
                if not math.isfinite(duration):
                    raise ValueError("Duration must be finite.")
            except (TypeError, ValueError):
                if image_path: image_path.unlink(missing_ok=True)
                self._send(400, {"error": "Duration and frame rate must be numeric."}); return
            if not 2 <= duration <= (12 if mode == "image-motion" else 4) or fps not in {12, 24, 30}:
                if image_path: image_path.unlink(missing_ok=True)
                self._send(400, {"error": "Settings exceed the selected engine's supported duration or frame-rate limits."}); return
            task = {
                "mode": mode, "prompt": prompt, "image_path": str(image_path) if image_path else None,
                "duration": duration,
                "fps": fps,
                "aspect": aspect,
                "motion": motion,
                "seed": int(body["seed"]) if str(body.get("seed", "-1")).isdigit() and 0 <= int(body.get("seed", -1)) <= 2147483647 else None,
                "inventory": inventory,
            }
            job = JOBS.submit(task)
            self._send(202, {"job": job, "message": "Job accepted by the native local engine."})
        except (ValueError, json.JSONDecodeError) as exc:
            self._send(400, {"error": f"Invalid request: {exc}"})
        except RuntimeError as exc:
            if image_path: image_path.unlink(missing_ok=True)
            self._send(429, {"error": str(exc)})
        except Exception as exc:
            if image_path: image_path.unlink(missing_ok=True)
            self._send(500, {"error": f"Local server error: {exc}"})


def already_running() -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/health", timeout=1.2) as response:
            data = json.loads(response.read().decode("utf-8"))
            return response.status == 200 and data.get("engine") == "native-python"
    except Exception:
        return False


if __name__ == "__main__":
    if already_running():
        print(f"OfflineYouTubeStudio is already running at http://127.0.0.1:{PORT}")
        raise SystemExit(0)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    server.daemon_threads = True
    print(f"OfflineYouTubeStudio native engine: http://127.0.0.1:{PORT}")
    print("No external workflow server is started. Local jobs are processed in-process.")
    server.serve_forever()
