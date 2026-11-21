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
import subprocess
import sys
import threading
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from hardware_scanner import scan_hardware
from model_selector import recommend_models
from engine.video_engine import ltx_capability
from engine.job_manager import JobManager
from engine.duration_planner import DURATION_PRESETS, plan_scene_slots, resolve_duration
from engine.production_pipeline import CONTENT_TYPES
from creator_skills import list_skills as list_creator_skills, run_skill as run_creator_skill

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
AI_SETUP_PROCESS = None
AI_SETUP_LOCK = threading.Lock()
AI_SETUP_STATE = ROOT / "logs" / "ai_setup.json"


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


def build_duration_plan(body: dict) -> dict:
    """Validate a full-video target and return a contiguous short-scene timeline.

    This is a planning API; it does not claim to generate or assemble the scenes.
    """
    if not isinstance(body, dict):
        raise ValueError("Request JSON must be an object.")
    preset = str(body.get("duration_preset", "60 seconds"))
    custom = body.get("custom_duration_seconds")
    total = resolve_duration(preset, custom)
    try:
        max_scene = int(body.get("max_scene_seconds", 4))
        min_scene = int(body.get("min_scene_seconds", 2))
    except (TypeError, ValueError) as exc:
        raise ValueError("Scene duration limits must be whole numbers.") from exc
    slots = plan_scene_slots(total, max_scene_seconds=max_scene, min_scene_seconds=min_scene)
    return {
        "total_duration_seconds": total,
        "scene_count": len(slots),
        "scene_slots": [
            {"index": slot.index, "start_seconds": slot.start_seconds,
             "duration_seconds": slot.duration_seconds}
            for slot in slots
        ],
        "status": "planned",
        "note": "Timeline planning only. Scene generation, audio, editing and export are separate pipeline stages.",
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
        if path == "/api/setup/ai":
            if AI_SETUP_STATE.is_file():
                try:
                    state = json.loads(AI_SETUP_STATE.read_text(encoding="utf-8"))
                except Exception:
                    state = {"status": "unknown", "message": "Could not read setup status."}
            else:
                state = {"status": "not_started", "message": "AI engine has not been installed yet.", "progress": 0}
            process = AI_SETUP_PROCESS
            if process is not None and process.poll() is not None and state.get("status") == "running":
                state = {"status": "failed", "message": "Installer stopped unexpectedly. Check logs/ai_setup.log.", "progress": 0}
            self._send(200, state)
            return
        if path == "/api/creator/skills":
            self._send(200, list_creator_skills())
            return
        if path == "/api/durations":
            self._send(200, {"presets": DURATION_PRESETS, "custom_min_seconds": 5,
                             "custom_max_seconds": 1800, "default_preset": "60 seconds"})
            return
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
        if path.startswith("/projects/") and path.endswith("/timeline.json"):
            parts = path.strip("/").split("/")
            if len(parts) != 3 or not re.fullmatch(r"[a-f0-9]{12}", parts[1]):
                self._send(404, {"error": "Project not found"}); return
            timeline = (OUTPUTS / (parts[1] + "_project") / "timeline.json").resolve()
            if timeline.parent.parent != OUTPUTS.resolve() or not timeline.is_file():
                self._send(404, {"error": "Project timeline is not available yet"}); return
            self._send(200, json.loads(timeline.read_text(encoding="utf-8")))
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
        if path == "/api/creator/run":
            try:
                body = self._json_body()
                if not isinstance(body, dict):
                    raise ValueError("Request JSON must be an object.")
                skill = str(body.get("skill", "")).strip()
                skill_input = body.get("input", "")
                if not isinstance(skill_input, str):
                    raise ValueError("Skill input must be text.")
                result = run_creator_skill(skill, skill_input, model=body.get("model"))
                self._send(200, result)
            except (ValueError, json.JSONDecodeError) as exc:
                self._send(400, {"error": f"Invalid creator-skill request: {exc}"})
            except RuntimeError as exc:
                self._send(503, {"error": str(exc)})
            except Exception as exc:
                self._send(500, {"error": f"Creator skill failed: {exc}"})
            return
        if path == "/api/setup/ai":
            global AI_SETUP_PROCESS
            try:
                with AI_SETUP_LOCK:
                    if AI_SETUP_PROCESS is not None and AI_SETUP_PROCESS.poll() is None:
                        self._send(409, {"error": "AI engine installation is already running."})
                        return
                    inventory = scan_hardware(ROOT)
                    gpu = inventory.get("primary_gpu") or {}
                    vram = (gpu.get("vram_total_mb") or 0) / 1024
                    ram = inventory.get("memory_gb") or 0
                    disk = (inventory.get("disk") or {}).get("free_gb") or 0
                    if vram < 10 or ram < 32 or disk < 50:
                        self._send(409, {"error": f"This PC does not meet LTX installation requirements. Detected {vram:.1f} GB VRAM, {ram} GB RAM and {disk:.1f} GB free disk; required: 10 GB VRAM, 32 GB RAM and 50 GB free disk. No model was downloaded. A compatible low-VRAM adapter is not yet integrated."})
                        return
                    (ROOT / "logs").mkdir(exist_ok=True)
                    log_handle = (ROOT / "logs" / "ai_setup.log").open("a", encoding="utf-8")
                    AI_SETUP_PROCESS = subprocess.Popen(
                        [sys.executable, str(ROOT / "ai_setup.py")],
                        cwd=str(ROOT), stdout=log_handle, stderr=subprocess.STDOUT,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                self._send(202, {"status": "running", "message": "AI engine installation started.", "progress": 1})
            except Exception as exc:
                self._send(500, {"error": f"Could not start AI installer: {exc}"})
            return
        if path == "/api/plan":
            try:
                plan = build_duration_plan(self._json_body())
                self._send(200, plan)
            except (ValueError, json.JSONDecodeError) as exc:
                self._send(400, {"error": f"Invalid timeline request: {exc}"})
            return
        if path == "/api/produce":
            saved_paths = []
            try:
                body = self._json_body()
                if not isinstance(body, dict):
                    raise ValueError("Request JSON must be an object.")
                topic = str(body.get("topic", "")).strip()
                if not topic or len(topic) > 500:
                    raise ValueError("Topic must contain 1–500 characters.")
                content_type = str(body.get("content_type", "educational"))
                if content_type not in CONTENT_TYPES:
                    raise ValueError("Unsupported content type.")
                preset = str(body.get("duration_preset", "60 seconds"))
                duration = resolve_duration(preset, body.get("custom_duration_seconds"))
                slots = plan_scene_slots(duration, max_scene_seconds=4, min_scene_seconds=2)
                aspect = str(body.get("aspect", "9:16"))
                fps = int(body.get("fps", 30))
                if aspect not in ALLOWED_ASPECTS:
                    raise ValueError("Unsupported aspect ratio.")
                if fps not in {30, 60}:
                    raise ValueError("Final export frame rate must be 30 or 60 FPS.")
                transition = str(body.get("transition", "cut"))
                if transition not in {"cut", "dissolve"}:
                    raise ValueError("Transition must be cut or dissolve.")
                scene_mode = str(body.get("scene_mode", "text"))
                if scene_mode not in {"text", "image"}:
                    raise ValueError("Scene mode must be text or image.")
                inventory = scan_hardware(ROOT)
                capability = ltx_capability(inventory)
                if not capability["available"]:
                    self._send(409, {"error": "Generative scene production is blocked by the active model safety checks.",
                                     "blockers": capability["blockers"],
                                     "note": "The production pipeline will not substitute still-image motion for generative scenes."})
                    return
                reference_path = None
                if scene_mode == "image":
                    data_url = str(body.get("image_data", ""))
                    match = re.fullmatch(r"data:image/(png|jpeg|webp);base64,([A-Za-z0-9+/=]+)", data_url)
                    if not match:
                        raise ValueError("Image-to-video production requires a PNG, JPEG or WebP reference image.")
                    raw = base64.b64decode(match.group(2), validate=True)
                    if len(raw) > MAX_IMAGE_BYTES:
                        raise ValueError("Reference image exceeds 20 MB.")
                    suffix = {"png": ".png", "jpeg": ".jpg", "webp": ".webp"}[match.group(1)]
                    reference_path = UPLOADS / (uuid.uuid4().hex + suffix)
                    reference_path.write_bytes(raw); saved_paths.append(reference_path)
                    from PIL import Image
                    with Image.open(reference_path) as image:
                        if image.width * image.height > MAX_IMAGE_PIXELS:
                            raise ValueError("Reference image exceeds the 40-megapixel limit.")
                        image.verify()
                music_path = None
                music_data = str(body.get("music_data", ""))
                if music_data:
                    match = re.fullmatch(r"data:audio/(wav|mpeg|ogg|mp4|x-wav);base64,([A-Za-z0-9+/=]+)", music_data)
                    if not match:
                        raise ValueError("Music must be a WAV, MP3, OGG or M4A audio file.")
                    raw = base64.b64decode(match.group(2), validate=True)
                    if len(raw) > 12 * 1024 * 1024:
                        raise ValueError("Music file exceeds 12 MB.")
                    suffix = {"wav": ".wav", "x-wav": ".wav", "mpeg": ".mp3", "ogg": ".ogg", "mp4": ".m4a"}[match.group(1)]
                    music_path = UPLOADS / (uuid.uuid4().hex + suffix)
                    music_path.write_bytes(raw); saved_paths.append(music_path)
                voice_models = body.get("voice_models") or {}
                if not isinstance(voice_models, dict) or len(voice_models) > 4:
                    raise ValueError("Voice model mapping must be an object with at most four speakers.")
                voice_models = {str(k).upper(): str(v) for k, v in voice_models.items()}
                sfx_paths = []
                sfx_data = body.get("sfx_data") or []
                if not isinstance(sfx_data, list) or len(sfx_data) > 5:
                    raise ValueError("Upload no more than five sound-effect files.")
                for sound_data in sfx_data:
                    match = re.fullmatch(r"data:audio/(wav|mpeg|ogg|mp4|x-wav);base64,([A-Za-z0-9+/=]+)", str(sound_data))
                    if not match:
                        raise ValueError("Sound effects must be WAV, MP3, OGG or M4A audio files.")
                    raw = base64.b64decode(match.group(2), validate=True)
                    if len(raw) > 8 * 1024 * 1024:
                        raise ValueError("Each sound effect must be 8 MB or smaller.")
                    suffix = {"wav": ".wav", "x-wav": ".wav", "mpeg": ".mp3", "ogg": ".ogg", "mp4": ".m4a"}[match.group(1)]
                    sound_path = UPLOADS / (uuid.uuid4().hex + suffix)
                    sound_path.write_bytes(raw); saved_paths.append(sound_path); sfx_paths.append(str(sound_path))
                task = {
                    "mode": "production", "prompt": topic, "topic": topic,
                    "content_type": content_type, "duration_preset": preset,
                    "custom_duration_seconds": body.get("custom_duration_seconds"),
                    "aspect": aspect, "fps": fps, "transition": transition,
                    "scene_mode": scene_mode, "reference_image_path": str(reference_path) if reference_path else None,
                    "music_path": str(music_path) if music_path else None, "sfx_paths": sfx_paths,
                    "voice_models": voice_models, "inventory": inventory,
                }
                job = JOBS.submit(task)
                self._send(202, {"job": job, "message": "Local multi-scene production job accepted.",
                                 "duration_seconds": duration, "scene_count": len(slots)})
            except (ValueError, json.JSONDecodeError) as exc:
                for saved in saved_paths: saved.unlink(missing_ok=True)
                self._send(400, {"error": f"Invalid production request: {exc}"})
            except RuntimeError as exc:
                for saved in saved_paths: saved.unlink(missing_ok=True)
                self._send(429, {"error": str(exc)})
            except Exception as exc:
                for saved in saved_paths: saved.unlink(missing_ok=True)
                self._send(500, {"error": f"Production request failed: {exc}"})
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
