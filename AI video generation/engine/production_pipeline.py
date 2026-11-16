"""Local multi-scene video production pipeline.

All generation and media processing happens on the user's machine. Script
writing requires a locally running Ollama service; narration requires local
Piper voices; scene generation uses the already-configured native video engine.
No cloud API or synthetic still-image fallback is used.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.request
from pathlib import Path
from typing import Any, Callable

from .duration_planner import plan_scene_slots, resolve_duration
from .video_engine import generate_video

CONTENT_TYPES = {
    "educational": "Teach one useful concept with a clear explanation and example.",
    "facts": "Present surprising but verifiable facts; avoid unsupported statistics.",
    "story": "Tell a coherent story with a hook, progression, climax and resolution.",
    "documentary": "Use a measured documentary voice, context, evidence and nuance.",
    "motivational": "Use grounded encouragement and practical steps; avoid empty hype.",
    "podcast": "Create a conversational host-led segment with natural spoken language.",
    "product-explainer": "Explain a product category, problem, features and practical use without invented claims.",
    "news-style": "Use a neutral news explainer structure; clearly label uncertainty and do not invent current events.",
    "how-to": "Give ordered, actionable steps with a concise outcome.",
    "shorts": "Create a fast-paced vertical short with an immediate hook and clear payoff.",
}

def _post_local_json(url: str, payload: dict[str, Any], timeout: int = 600) -> dict[str, Any]:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("Local script model returned an invalid response.")
    return data


def create_script_package(topic: str, content_type: str, duration_seconds: int,
                          scene_count: int, *, model: str | None = None) -> dict[str, Any]:
    """Ask a local Ollama model for a structured script and scene prompts."""
    topic = str(topic).strip()
    if not topic or len(topic) > 500:
        raise ValueError("Enter a topic between 1 and 500 characters.")
    if content_type not in CONTENT_TYPES:
        raise ValueError("Unsupported content type.")
    duration = resolve_duration("Custom", duration_seconds)
    if not 2 <= scene_count <= 450:
        raise ValueError("Scene count is outside supported bounds.")
    model = model or os.environ.get("OLLAMA_MODEL", "llama3.2:1b")
    base = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    seconds = max(90, duration_seconds * 2)
    prompt = f"""
Create a production-ready video package in JSON only.
Topic: {topic}
Format: {content_type} — {CONTENT_TYPES[content_type]}
Target length: {duration} seconds. Scene count: exactly {scene_count}.
Return keys: title, description, hook, script, scenes.
scenes must be an array of exactly {scene_count} objects with keys:
narration (short exact excerpt from script), visual_prompt (specific cinematic
video-generation prompt, no text/logos), and transition (cut or dissolve).
Write a complete spoken script suitable for about {duration} seconds. The
first spoken sentence must be the hook. Scene narration must cover the script
in order without inventing new claims. For factual subjects, do not invent
statistics, quotations, sources or events; use cautious wording when unsure.
Do not include markdown fences or commentary.
"""
    result = _post_local_json(base + "/api/generate", {
        "model": model, "prompt": prompt, "stream": False, "format": "json",
        "keep_alive": 0, "options": {"num_gpu": 0, "num_ctx": 4096,
                                      "num_predict": min(8192, max(1800, seconds * 18))},
    })
    try:
        package = json.loads(result.get("response", ""))
    except (TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Local language model did not return valid JSON.") from exc
    if not isinstance(package, dict):
        raise RuntimeError("Local language model returned an invalid script package.")
    script = str(package.get("script", "")).strip()
    scenes = package.get("scenes")
    if not script or not isinstance(scenes, list) or len(scenes) != scene_count:
        raise RuntimeError(f"Script model must return a script and exactly {scene_count} scenes.")
    cleaned = []
    for index, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            raise RuntimeError(f"Scene {index} is not a JSON object.")
        visual = str(scene.get("visual_prompt", "")).strip()
        narration = str(scene.get("narration", "")).strip()
        if not visual:
            raise RuntimeError(f"Scene {index} is missing its visual prompt.")
        cleaned.append({
            "index": index, "narration": narration,
            "visual_prompt": visual[:2000],
            "transition": "dissolve" if scene.get("transition") == "dissolve" else "cut",
        })
    return {
        "title": str(package.get("title") or topic)[:120],
        "description": str(package.get("description") or "")[:5000],
        "hook": str(package.get("hook") or "")[:1000],
        "script": script, "scenes": cleaned,
        "content_type": content_type, "topic": topic,
    }


def _exe(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"{name} is required. Install it locally and add it to PATH.")
    return path


def _run(args: list[str], *, timeout: int = 1800) -> None:
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "Media command failed.")[-3000:])


def _timestamp(seconds: float) -> str:
    ms = max(0, int(seconds * 1000))
    hours, ms = divmod(ms, 3600000)
    minutes, ms = divmod(ms, 60000)
    secs, ms = divmod(ms, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"


def write_captions(script: str, duration: float, path: Path) -> None:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\\s+", script.strip()) if s.strip()]
    if not sentences:
        raise RuntimeError("Cannot create captions from an empty script.")
    weights = [max(1, len(s.split())) for s in sentences]
    total = sum(weights)
    cursor = 0.0
    lines = []
    for index, (sentence, weight) in enumerate(zip(sentences, weights), 1):
        end = cursor + duration * weight / total
        lines.extend([str(index), f"{_timestamp(cursor)} --> {_timestamp(end)}", sentence, ""])
        cursor = end
    path.write_text("\\n".join(lines), encoding="utf-8-sig")


def _make_voice(script: str, output: Path, model_path: str | None = None) -> None:
    piper = _exe("piper")
    voice = model_path or os.environ.get("PIPER_MODEL", "")
    if not voice or not Path(voice).is_file():
        raise RuntimeError("Set PIPER_MODEL to a downloaded local Piper .onnx voice file.")
    result = subprocess.run([piper, "--model", voice, "--output_file", str(output)],
                            input=script, text=True, capture_output=True, timeout=600)
    if result.returncode or not output.is_file():
        raise RuntimeError("Piper narration failed: " + result.stderr[-2000:])


def _render_dialogue(script: str, output: Path, voice_models: dict[str, str]) -> None:
    """Render SPEAKER 1:/SPEAKER 2: dialogue with separate local Piper voices."""
    segments = re.split(r"(?im)^\\s*(SPEAKER\\s+\\d+)\\s*:\\s*", script)
    if len(segments) < 3:
        _make_voice(script, output)
        return
    piper = _exe("piper")
    import wave
    pieces: list[Path] = []
    for i in range(1, len(segments), 2):
        speaker = segments[i].upper()
        text = segments[i + 1].strip() if i + 1 < len(segments) else ""
        if not text:
            continue
        model = voice_models.get(speaker) or voice_models.get(speaker.lower()) or os.environ.get("PIPER_MODEL", "")
        if not model or not Path(model).is_file():
            raise RuntimeError(f"No local Piper voice model configured for {speaker}.")
        piece = output.with_name(f"{output.stem}_{len(pieces)+1}.wav")
        result = subprocess.run([piper, "--model", model, "--output_file", str(piece)],
                                input=text, text=True, capture_output=True, timeout=600)
        if result.returncode or not piece.is_file():
            raise RuntimeError(f"Piper failed for {speaker}: {result.stderr[-1000:]}")
        pieces.append(piece)
    if not pieces:
        raise RuntimeError("No speaker dialogue was found.")
    with wave.open(str(output), "wb") as target:
        with wave.open(str(pieces[0]), "rb") as first:
            target.setparams(first.getparams())
        for piece in pieces:
            with wave.open(str(piece), "rb") as source:
                if (source.getnchannels(), source.getsampwidth(), source.getframerate()) != (
                    target.getnchannels(), target.getsampwidth(), target.getframerate()
                ):
                    raise RuntimeError("Piper voice models produced incompatible WAV formats.")
                target.writeframes(source.readframes(source.getnframes()))
            piece.unlink(missing_ok=True)


def _concat_scenes(clips: list[Path], output: Path, *, width: int, height: int, fps: int,
                   transition: str = "cut") -> None:
    ffmpeg = _exe("ffmpeg")
    if not clips:
        raise RuntimeError("No scene clips were generated.")
    if transition == "dissolve" and len(clips) > 1:
        inputs: list[str] = []
        for clip in clips:
            inputs += ["-i", str(clip)]
        filters = []
        previous = "[0:v]"
        offset = 0.0
        for index in range(1, len(clips)):
            # Clips are short, equalized to 0.5-second overlap.
            offset += max(0.5, 3.5) if index == 1 else 3.5
            label = f"[xf{index}]"
            filters.append(f"{previous}[{index}:v]xfade=transition=fade:duration=0.5:offset={offset:.3f}{label}")
            previous = label
        _run([ffmpeg, "-y", *inputs, "-filter_complex", ";".join(filters),
              "-map", previous, "-an", "-r", str(fps), "-c:v", "libx264",
              "-pix_fmt", "yuv420p", str(output)])
        return
    listing = output.with_suffix(".concat.txt")
    listing.write_text("".join("file '" + str(p.resolve()).replace("'", "'\\''") + "'\\n" for p in clips),
                       encoding="utf-8")
    _run([ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
          "-an", "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps}",
          "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", str(output)])
    listing.unlink(missing_ok=True)


def produce_video(task: dict[str, Any], output_path: str | Path, *,
                  cancel_event=None, progress: Callable[[float, str], None] | None = None) -> dict[str, Any]:
    """Generate script, short generative scenes, voice, captions and final MP4."""
    root = Path(output_path).parent / (Path(output_path).stem + "_project")
    root.mkdir(parents=True, exist_ok=True)
    duration = resolve_duration(task.get("duration_preset", "60 seconds"),
                                task.get("custom_duration_seconds"))
    slots = plan_scene_slots(duration, max_scene_seconds=4, min_scene_seconds=2)
    package = create_script_package(
        task.get("topic", ""), task.get("content_type", "educational"), duration, len(slots),
        model=task.get("ollama_model"),
    )
    (root / "script_package.json").write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    (root / "script.txt").write_text(package["script"], encoding="utf-8")
    clips = []
    for index, (scene, slot) in enumerate(zip(package["scenes"], slots), 1):
        if cancel_event and cancel_event.is_set():
            raise RuntimeError("Production cancelled.")
        clip = root / f"scene_{index:03}.mp4"
        scene_task = {
            "mode": task.get("scene_mode", "text"),
            "prompt": scene["visual_prompt"],
            "image_path": task.get("reference_image_path") if task.get("scene_mode") == "image" else None,
            "duration": min(4, max(2, slot.duration_seconds)),
            "fps": min(12, int(task.get("fps", 30))),
            "aspect": task.get("aspect", "9:16"),
            "seed": None, "inventory": task.get("inventory") or {},
        }
        result = generate_video(scene_task, clip, cancel_event=cancel_event,
            progress=(lambda p, m, i=index: progress(0.1 + 0.55 * ((i - 1 + p) / len(slots)), f"Scene {i}/{len(slots)}: {m}") if progress else None))
        if not result.get("is_generative_ai"):
            raise RuntimeError("Scene engine did not report genuine generative video; refusing to label a still-image render as AI video.")
        clips.append(clip)
    if cancel_event and cancel_event.is_set():
        raise RuntimeError("Production cancelled.")
    voice = root / "narration.wav"
    _render_dialogue(package["script"], voice, task.get("voice_models") or {})
    # Determine narration duration with ffprobe, then align subtitles and final video.
    ffprobe = _exe("ffprobe")
    probe = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                            "-of", "default=noprint_wrappers=1:nokey=1", str(voice)],
                           capture_output=True, text=True, check=True)
    voice_duration = float(probe.stdout.strip())
    captions = root / "captions.srt"
    write_captions(package["script"], voice_duration, captions)
    aspect = task.get("aspect", "9:16")
    width, height = {"9:16": (1080, 1920), "16:9": (1920, 1080),
                     "1:1": (1080, 1080), "4:3": (1440, 1080), "3:2": (1620, 1080)}[aspect]
    visual = root / "visual_track.mp4"
    _concat_scenes(clips, visual, width=width, height=height,
                   fps=int(task.get("fps", 30)), transition=task.get("transition", "cut"))
    ffmpeg = _exe("ffmpeg")
    subtitle_path = str(captions.resolve()).replace("\\\\", "/").replace(":", "\\:").replace("'", "\\'")
    command = [ffmpeg, "-y", "-i", str(visual), "-i", str(voice)]
    music = task.get("music_path")
    if music and Path(music).is_file():
        command += ["-stream_loop", "-1", "-i", str(music)]
    filters = [f"[0:v]subtitles='{subtitle_path}':force_style='FontName=Arial,FontSize=22,Outline=2,Shadow=1,Alignment=2,MarginV=45'[v]"]
    if music and Path(music).is_file():
        filters.append("[2:a]volume=0.12[music]")
        filters.append("[1:a][music]amix=inputs=2:duration=first:dropout_transition=2[a]")
        audio_map = "[a]"
    else:
        audio_map = "1:a"
    command += ["-filter_complex", ";".join(filters), "-map", "[v]", "-map", audio_map,
                "-r", str(task.get("fps", 30)), "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                "-shortest", "-movflags", "+faststart", str(output_path)]
    _run(command, timeout=3600)
    if not Path(output_path).is_file() or Path(output_path).stat().st_size < 2048:
        raise RuntimeError("Final MP4 was not created successfully.")
    timeline = {
        "title": package["title"], "duration_seconds": duration, "aspect": aspect,
        "fps": int(task.get("fps", 30)), "script": package["script"],
        "scenes": [{"index": s["index"], "start_seconds": slot.start_seconds,
                    "duration_seconds": slot.duration_seconds,
                    "visual_prompt": s["visual_prompt"], "transition": s["transition"],
                    "clip": clips[i].name}
                   for i, (s, slot) in enumerate(zip(package["scenes"], slots))],
        "audio": {"narration": voice.name, "captions": captions.name,
                  "music": Path(music).name if music and Path(music).is_file() else None},
    }
    (root / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    if progress:
        progress(1.0, "Production complete")
    return {"path": str(output_path), "engine": "local-multi-scene-production",
            "is_generative_ai": True, "description": "Multi-scene local generative video with local narration and captions.",
            "project_dir": str(root), "title": package["title"]}
