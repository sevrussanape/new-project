# ◈ OfflineYouTubeStudio

**A local-first video creation workspace with an honest hardware advisor, a native LTX-Video adapter, and a non-generative image-motion renderer.**

![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)
![Runtime](https://img.shields.io/badge/Runtime-Local%20Python-3776AB)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D4)

## What this project does

| Feature | Behavior |
|---|---|
| Text-to-video | Native LTX-Video Diffusers pipeline, only when the integrated model passes the shared hardware/runtime gate |
| Image-to-video | LTX-Video with a supplied reference image, under the same gate |
| Image Motion | Creates a camera-motion MP4 from a still image; **not** generative AI |
| Hardware advisor | Reads NVIDIA GPU/VRAM, system RAM, free disk and optional PyTorch CUDA status |
| Model selection | Selects only a model that has a real adapter in this codebase and passes all planning gates |
| Production pipeline | Local script generation, per-scene video, Piper narration, captions, music/SFX, transitions and MP4 assembly when dependencies are configured |
| Job queue | Local sequential queue, progress, cancellation, history and outputs |

The application never silently substitutes Image Motion for generative video. If no integrated generative model is safe to run, text/image generation and full AI production are blocked with an explanation.

## Hardware detection, model selection and runtime: how they connect

This is the actual control path:

```text
hardware_scanner.py
  └─ reads GPU/VRAM, RAM, disk, CUDA facts (no installs or downloads)
       ↓
model_selector.py
  └─ ranks only models with an integrated runtime adapter
       ↓
studio.py /api/models and /api/produce
  └─ shows the recommendation and refuses unsafe jobs
       ↓
engine/video_engine.py
  └─ re-runs the SAME selector gate immediately before inference
       ↓
LTXRuntime (Diffusers) → generated scene clips
```

**Important:** the hardware scanner is a detector, not an installer. It must not download multi-gigabyte weights or install CUDA packages during a hardware scan. Model/dependency installation is an explicit user action. This separation avoids unexpected downloads and prevents a hardware name alone from being treated as proof that a model can run.

At present, **LTX-Video is the only integrated generative video adapter**. The selector does not advertise experimental models as runnable. Adding another model requires implementing and testing its adapter, declaring its requirements, and registering it in the model catalog. Merely detecting an RTX GPU does not make an unsupported model available.

The model advisor and runtime now share the same eligibility decision. Missing free-VRAM telemetry is treated as unknown/unsafe rather than assumed to be sufficient. Runtime checks still run immediately before model loading.

## Complete local production pipeline

The browser UI exposes a multi-scene production workflow. The Hardware & model advisor also has a **Download & install AI video engine + model** button. Clicking it starts a background installer, shows status in the UI, installs CUDA-enabled PyTorch and the Diffusers dependencies, then downloads the LTX-Video weights into the Hugging Face cache. The installer does not block the browser while downloading.

1. A local Ollama model creates the title, hook, script and visual prompts for educational, facts, story, documentary, motivational, podcast, product-explainer, news-style, how-to and Shorts formats.
2. The integrated generative video adapter creates short clips for each scene. A failed model check stops the job; still-image motion is not substituted.
3. Local Piper creates narration. Scripts with `SPEAKER 1:` / `SPEAKER 2:` labels can use separate local Piper voice models.
4. FFmpeg assembles scenes, applies cuts/dissolves, burns subtitles and mixes optional local music and sound effects.
5. The final export supports portrait, landscape, square and other configured aspect ratios at 30 or 60 FPS. Scene clips, script, captions and `timeline.json` are kept in the project output folder.

### Required local tools for production

- **Ollama:** installed and running at `http://127.0.0.1:11434`; download a local language model once and set `OLLAMA_MODEL` if needed.
- **Piper:** installed locally and on `PATH`; set `PIPER_MODEL` to a local voice `.onnx` file.
- **FFmpeg + FFprobe:** installed and on `PATH`; subtitle burn-in requires FFmpeg with libass support.
- **Video model runtime:** CUDA-enabled PyTorch, Diffusers, Transformers, Accelerate and the LTX model weights, on hardware that passes the selector.

Ollama/Piper/FFmpeg are not silently downloaded by the GPU scanner. They are separate prerequisites. The first model-weight download requires internet access; once all required packages and weights are cached, generation can run offline.

## YouTube Creator Skills (11 local-first workflows)

The Studio now includes a YouTube Creator Skills panel with eleven focused workflows:
channel audit, chapters, comment triage, edit decision lists, title/thumbnail packaging,
content planning, retention analysis, hook/script writing, SEO, Shorts repurposing and
relative-view viral outlier research.

Language tasks use the configured local Ollama model only. Transcript and analytics
checks run in Python. There is no Gemini, OpenAI, ElevenLabs or other hosted inference
fallback, and the skills never publish, upload, reply to comments or modify source media.

Install Ollama separately, then download the recommended local language model once:

```bat
ollama pull qwen3:4b
```

The default creator model is qwen3:4b; set OLLAMA_MODEL before launching Studio to
use another model. Qwen3 4B is a starting recommendation for a 4 GB VRAM / 32 GB RAM
class of PC, not a promise that all model layers will fit in dedicated VRAM. Ollama may
offload layers to system RAM; close GPU-heavy apps or use a smaller model if necessary.
The model weights must be downloaded once before offline use.

Use the **YouTube Creator Skills** section in the browser. Paste the evidence requested
for the selected skill: transcripts for chapters/edit/Shorts, a CSV export for retention,
or JSON video records for relative-view research. Channel audit does not scrape a channel
URL or access private YouTube Studio data. Viral research does not scrape competitor
channels. These tools analyze only the evidence you supply and cannot guarantee virality.

Detailed guide: [docs/CREATOR_SKILLS.md](docs/CREATOR_SKILLS.md).

## Hardware requirements and realistic expectations

The integrated LTX adapter uses conservative planning requirements:

- NVIDIA GPU with CUDA-enabled PyTorch
- 10 GB total VRAM and at least 8.5 GB currently free
- 32 GB system RAM
- Approximately 50 GB free disk space

These are **safety gates, not a promise** that inference will succeed. Architecture, driver, CUDA/PyTorch compatibility, other GPU workloads, model revision and resolution all matter. A compatible GPU should first be tested with a short clip.

| Hardware situation | Expected behavior |
|---|---|
| 4 GB GPU | LTX blocked; Image Motion remains available |
| RTX 4050 with 6 GB VRAM (common laptop configuration) | LTX blocked by the 10 GB planning floor; Image Motion remains available |
| GPU with 10–12 GB VRAM | May meet the total-VRAM floor, but must also meet free VRAM, RAM, disk and CUDA checks; test first |
| GPU with 16 GB+ VRAM | More headroom; still subject to the same checks and model/runtime compatibility |
| CPU-only | Studio and Image Motion; native LTX generation is disabled |

**Do not bypass the gate to force LTX onto a lower-memory GPU.** System RAM is not interchangeable with dedicated VRAM. The selector currently has one integrated model, so it cannot automatically switch to an unimplemented low-VRAM model.

## Get started (Windows)

1. Install 64-bit Python 3.11 or newer.
2. Open the `AI video generation` folder.
3. Install the lightweight Studio dependencies:

   ```bat
   ONE_CLICK.bat install
   ```

4. Launch:

   ```bat
   ONE_CLICK.bat start
   ```

5. Open [http://127.0.0.1:8765](http://127.0.0.1:8765).

### Hardware check

Run:

```bat
CHECK_GPU.bat
```

This prints detected hardware, the selected integrated model (if any), and why a model is blocked. It does not install software or download model weights.

### Install the optional LTX runtime

On hardware you expect to meet the LTX gate, explicitly run:

```bat
ONE_CLICK.bat install-ltx
```

This installs CUDA-enabled PyTorch and the Diffusers dependencies. The model weights are fetched on the first eligible generation request. This installer does not override the hardware gate. The provided installer currently targets the CUDA 12.6 PyTorch wheel index; verify compatibility with your NVIDIA driver and Python version.

## Image Motion on lower-memory PCs

1. Open Image Motion in the Studio.
2. Upload a PNG, JPEG or WebP.
3. Choose aspect ratio, duration and frame rate.
4. Render and preview/download the MP4.

This uses Pillow and imageio-ffmpeg to animate a still image with a deterministic camera move. It does not create new objects, scenes or motion through a generative model.

## Local API

| Endpoint | Method | Purpose |
|---|:---:|---|
| `/api/health` | GET | Application status and hardware report |
| `/api/creator/skills` | GET | List YouTube creator workflows and local model guidance |
| `/api/creator/run` | POST | Run one local creator workflow (Ollama or deterministic Python) |\n| `/api/setup/ai` | GET/POST | Read installer status / start AI runtime and model installation |
| `/api/hardware` | GET | Raw hardware inventory |
| `/api/models` | GET | Model recommendation, runtime gate and fallback |
| `/api/config` | GET | UI/API limits and modes |
| `/api/durations` | GET | Duration presets and custom range |
| `/api/plan` | POST | Build a scene-slot plan |
| `/api/generate` | POST | Queue a short generative or Image Motion job |
| `/api/produce` | POST | Queue a full local multi-scene production |
| `/api/jobs` | GET | Recent jobs |
| `/api/jobs/{id}` | GET | Job state |
| `/api/jobs/{id}/cancel` | POST | Cancel an active job |
| `/projects/{id}/timeline.json` | GET | Read generated project timeline metadata |
| `/outputs/{file}.mp4` | GET | Preview/download an MP4 |

## Project layout

```text
AI video generation/
├── engine/             # Runtime adapter, queue, duration and production pipeline
├── creator_skills/     # Upstream MIT attribution for adapted skill workflows
├── creator_skills.py   # 11 local-first YouTube creator skill handlers
├── web/                # Browser interface
├── tests/              # Automated regression tests
├── docs/               # Architecture and model-selection documentation
├── studio.py           # Local HTTP server and API\n├── ai_setup.py         # Explicit CUDA runtime + LTX model installer
├── hardware_scanner.py # Side-effect-free hardware inventory
├── model_selector.py   # Integrated-model eligibility and recommendation
├── channel_pipeline.py # Local channel workflow CLI
├── ONE_CLICK.bat       # Windows install and launch
├── CHECK_GPU.bat       # Hardware/model diagnostic
└── TEST.bat            # Test runner
```

Generated outputs, uploads, logs, SQLite job data and cached model weights are runtime data and should not be committed.

## Tests

From the project directory:

```bat
TEST.bat
```

Or:

```bash
python -m unittest discover -s tests -v
python -m compileall -q .
```

Automated tests validate policy and code paths. They do not prove CUDA inference, voice-model compatibility, FFmpeg filter support or end-to-end Windows production. Those need to be tested on the target PC.

## Current limitations (read before relying on it)

- Only LTX-Video is integrated for genuine generative video. No low-VRAM generative adapter is currently included.
- A typical 6 GB RTX 4050 laptop GPU does not meet the current LTX gate. The app should report this accurately rather than claiming it can run AI video.
- The project timeline is currently exported as JSON metadata; it is **not yet a full interactive clip-editing timeline**.
- Full production depends on locally installed Ollama, Piper, FFmpeg/FFprobe and a video model runtime.
- The first package/model downloads require internet. Offline use is possible only after all required dependencies and model files are cached.
- The LTX adapter and full production workflow still require an actual target-PC GPU/media end-to-end validation.

## License and attribution

Review the license terms for LTX-Video and every optional dependency/model before commercial use or redistribution of weights. OfflineYouTubeStudio is an independent integration and is not affiliated with Lightricks.
