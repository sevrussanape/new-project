# Automated YouTube channel pipeline

The optional channel pipeline keeps the original local-first production workflow while routing video creation through the native OfflineYouTubeStudio engine.

## Pipeline stages

1. Optional public YouTube search research (`niche_research.py`). This stage requires internet and is a heuristic, not a prediction of virality.
2. Local script, hook, title, description and tags from Ollama.
3. Video rendering through the integrated Python engine:
   - On hardware passing the LTX capability gate, native LTX Diffusers inference is used.
   - On a low-VRAM machine, provide `--motion-image path\to\image.jpg` to create a still-image camera-motion clip. This is not diffusion-generated video.
4. Local narration using Piper and a downloaded local voice model.
5. Subtitle timing and final MP4 muxing using FFmpeg.
6. Optional YouTube upload using Google OAuth. Default privacy is private.

## Hardware behavior

The official Diffusers LTX example reports about 10 GB VRAM. Offline Studio uses a conservative gate of 10 GB total VRAM and 8.5 GB free VRAM, with CUDA-enabled PyTorch and disk checks. A GTX 1650 4 GB is below this gate. Do not bypass the gate and expect a full diffusion model to work just because the PC has 64 GB system RAM.

For a GTX 1650 4 GB, the pipeline can use `--motion-image` to animate a still image and finish a local MP4. The output is a pan/zoom media render, not a generative video. To make a full video with multiple different scenes on this hardware, prepare one still image per scene and assemble the scenes with a later scene-timeline feature; that automatic scene-timeline feature is not yet implemented.

## Setup

- Run `ONE_CLICK.bat install` for the base app.
- Install Ollama and download a small local language model; set `OLLAMA_MODEL` if not using the default `llama3.2:1b`.
- For public niche research, install `.venv\Scripts\python.exe -m pip install -r requirements-channel.txt` (includes `yt-dlp` and optional YouTube OAuth packages).
- Install Piper and a local voice `.onnx` file; set `PIPER_MODEL` to the voice path.
- Install FFmpeg and make sure `ffmpeg` is on PATH for subtitle burn-in and muxing.
- On an LTX-compatible GPU, run `ONE_CLICK.bat install-ltx`. Model weights download at first use and are cached for offline runs.

## Examples

Research-only niche report:

```bat
.venv\Scripts\python.exe channel_pipeline.py --auto-niche --research-only
```

Generate script and metadata without video:

```bat
.venv\Scripts\python.exe channel_pipeline.py --topic "Why octopuses change color" --skip-research --prompt-only
```

Use a still image for a low-VRAM visual:

```bat
.venv\Scripts\python.exe channel_pipeline.py --topic "Why octopuses change color" --skip-research --motion-image assets\octopus.jpg --no-upload
```

On an eligible LTX GPU, omit `--motion-image` to request native LTX generation.

## Important limitations

- Niche research requires internet; Ollama generation is local after the model is downloaded.
- Piper and FFmpeg are optional tools for narration and final assembly and must be installed separately.
- YouTube upload requires internet, OAuth credentials and explicit review of the finished content.
- The script does not guarantee factual accuracy, channel growth, or policy compliance. Review every script, visual, audio track and metadata before upload.
- The current pipeline does not automatically generate a unique AI image for every retention beat or build a full multi-scene timeline.
