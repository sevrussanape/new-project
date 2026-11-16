# Changelog

## 2.0.0 — Native local engine migration
- Replaced ComfyUI API bridge with an in-process Python engine and local job queue.
- Added native LTX Diffusers adapter with conservative VRAM/CUDA/disk checks.
- Added a low-resource Image Motion MP4 renderer for still images; explicitly not generative AI.
- Added job progress, cancellation, output preview and hardware-aware model advisor UI.
- Simplified Windows launcher; base install no longer downloads a separate workflow application or large model framework.
- Kept channel scripting, niche research, Piper/FFmpeg post-production and YouTube OAuth integration, with video generation routed through the native engine.
- Removed obsolete workflow import and startup-hook files.


## 2.1.0 — Reliability, safety and workflow improvements
- Persisted job history in SQLite and recover interrupted jobs with an explicit restart message.
- Added a bounded waiting queue and clearer queue-full responses.
- Added prompt, aspect-ratio, duration, frame-rate, image-size and image-dimension validation.
- Added local API configuration endpoint and browser security headers.
- Added optional reproducible seed input, MP4 download links and visible job failure details.
- Expanded automated coverage to 16 tests, including persistence and API validation.
