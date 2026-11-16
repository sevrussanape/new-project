# Offline AI Video Studio — Product Specification

## Product goal

Extend the existing OfflineYouTubeStudio into a complete, local-first AI video production workspace. Preserve the current native Python server, job queue, hardware scanner, model advisor, and web UI. Do not replace the project with a new application.

## Non-negotiable constraints

- No cloud video generation, hosted inference, fal.ai, or paid generation APIs.
- After models and dependencies have been installed, generation and editing must work locally/offline.
- Detect the actual machine at runtime: GPU model, dedicated VRAM, currently free VRAM, CUDA/PyTorch availability, system RAM, free disk, and thermal status where available.
- Select only models and settings whose requirements have been tested against the detected hardware.
- Never bypass hardware, memory, thermal, or disk safety checks.
- Never describe pan/zoom of a still image as generative AI video. Text-to-video and image-to-video must use a genuine local generative model.
- Preserve existing app functionality and test each stage before moving to the next.

## User-facing workflow

1. Choose a content type and enter a topic or provide source material.
2. Choose language, tone, audience, aspect ratio, frame rate, quality, and video duration.
3. Generate a script, narration plan, scene outline, and visual prompts locally.
4. Review and edit the script and scene plan.
5. Generate each scene using a supported local text-to-video or image-to-video model. Allow local media assets where generative video is not suitable.
6. Generate voice-over or multi-speaker dialogue locally; add optional local music and sound effects.
7. Assemble scenes, audio, captions, transitions, and timing into an editable timeline.
8. Preview, revise, and export an MP4 locally.

## Duration is user-selected

Duration is not fixed at 60 seconds. Provide presets for:
- 15 seconds
- 30 seconds
- 45 seconds
- 60 seconds
- 90 seconds
- 2 minutes
- 5 minutes
- Custom duration

The user may choose any supported duration and change it before generation. The selected duration is the target length of the complete video, not the length of one diffusion inference. The planner must allocate scene durations so the assembled timeline matches the target within a documented tolerance. Long videos must be assembled from multiple short generated scenes; do not attempt one very long diffusion inference.

## Content types

Support extensible templates for:
- Podcasts and multi-speaker conversations
- Educational explainers and tutorials
- Facts and list videos
- Stories and narration
- Documentaries
- Motivational videos
- Product explainers
- News-style explainers
- General/custom videos

Templates define script structure and scene pacing; they must not invent factual claims for news or documentary content.

## Visual generation

- Genuine local Text-to-Video.
- Genuine local Image-to-Video.
- Scene-by-scene prompt planning and generation.
- User-provided reference images and local media.
- Optional locally stored stock/media library.
- Hardware-aware model selection and clear capability explanations.
- If no tested generative model is supported, explain that generation is unavailable on this PC. Do not silently substitute image-motion.

## Audio and editing

- Local text-to-speech voice-over.
- Multiple selectable local voices where installed.
- Multi-speaker dialogue for podcast formats.
- Optional locally generated or user-supplied background music and sound effects.
- Automatic subtitles/captions with editable text and timing.
- Scene trimming, ordering, transitions, audio mixing, and timeline preview.
- Keep audio and video durations synchronized.

## Export

- MP4 output.
- Aspect ratios: 9:16 vertical, 16:9 landscape, 1:1 square, plus custom where supported.
- 1080x1920 vertical export preset; landscape and square presets as applicable.
- 30 FPS and 60 FPS export options, subject to source generation and encoder capability.
- Quality/bitrate presets and custom export settings.
- Export options must clearly distinguish generated source frame rate/resolution from upscaling or frame-rate conversion.

## Hardware profiles

Hardware profiles are based on measured resources and model-specific validated requirements, not GPU names alone. Laptop and desktop variants can have different VRAM. GTX 1650 4 GB, RTX 3050, RTX 4050, RTX 4060, RTX 4070, and higher GPUs must be evaluated by actual available resources and tested model support. A profile may offer script/audio/editing features while disabling unsupported generative video. System RAM does not count as dedicated VRAM.

## Current baseline — do not overstate

The existing repository currently has:
- A local Python HTTP server and browser UI.
- Hardware/model reporting and a conservative LTX capability gate.
- A persistent local job queue.
- Short native LTX text-to-video and image-conditioned generation when its existing hardware gate passes.
- A still-image camera-motion MP4 renderer, explicitly non-generative.
- Basic preview, job history, and MP4 download.

The current baseline does **not** yet provide the complete production workflow above. In particular, do not claim that it already has multi-scene planning, long-form video assembly, an editable timeline, complete podcast dialogue, music/SFX mixing, automatic captions, or the full export matrix.

## Implementation phases and acceptance criteria

### Phase 1 — Product foundation and duration planning
- Document product architecture and feature boundaries.
- Add validated duration presets and custom duration to the project planner.
- Define scene allocation rules for arbitrary target durations.
- Add tests for preset parsing, custom values, bounds, and scene-duration totals.
- Keep the current short-clip endpoint behavior explicit until multi-scene orchestration is implemented.

### Phase 2 — Local content and scene planner
- Add content-type templates.
- Add a local LLM adapter with explicit model availability checks.
- Generate editable scripts, narration blocks, scene descriptions, and visual prompts.
- No external API fallback.
- Tests must cover offline/unavailable model behavior and prompt/script validation.

### Phase 3 — Multi-scene generative engine
- Add a scene job model and sequential GPU-aware execution.
- Generate short genuine T2V/I2V clips per scene with cancellation and progress.
- Assemble clips with local FFmpeg, preserve ordering, and match the selected total duration.
- Fail clearly if the selected model cannot run; never substitute image-motion as AI.
- Test scene sequencing, cancellation, cleanup, and duration tolerance.

### Phase 4 — Local audio and captions
- Integrate local TTS and multi-voice dialogue where available.
- Add optional local/user audio, music, and SFX tracks.
- Generate editable captions and synchronize narration.
- Test missing voices, offline operation, audio mixing, and subtitle timing.

### Phase 5 — Timeline and export
- Add editable scene/audio/caption timeline and preview.
- Add transitions, trimming, aspect-ratio presets, and export controls.
- Support 30/60 FPS export where technically valid, with clear conversion labeling.
- Test MP4 validity, audio/video synchronization, duration, dimensions, and cancellation.

### Phase 6 — Hardware compatibility and release validation
- Maintain a tested model compatibility matrix by measured VRAM/RAM/disk/runtime.
- Test representative low-, mid-, and high-VRAM machines.
- Verify first-time model setup and subsequent offline operation.
- Run the full test suite and document known limitations before calling the product complete.

## Definition of done

The project is complete only when all workflow stages are integrated in the UI, work locally without cloud inference, pass automated tests, and have been verified on supported hardware. A feature listed in this specification is a requirement, not a claim that it has already been implemented.
