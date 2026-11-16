<!--
  OfflineYouTubeStudio
  Local-first video creation with transparent hardware limits.
-->

<div align="center">

# ◈ OfflineYouTubeStudio

### Your local video workspace. Your hardware. Your files.

**A native Python video studio with hardware-aware model selection, an in-process LTX adapter, and a low-resource image-motion renderer.**

<p>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/Run-Local--first-9BCF53?style=for-the-badge" alt="Local first">
  <img src="https://img.shields.io/badge/Backend-Native%20Python-20232A?style=for-the-badge" alt="Native Python backend">
  <img src="https://img.shields.io/badge/Platform-Windows-0078D4?style=for-the-badge&logo=windows&logoColor=white" alt="Windows">
</p>

[Features](#-what-you-can-do) · [Hardware guide](#-hardware--honest-expectations) · [Install](#-get-started) · [API](#-local-api) · [Docs](#-documentation)

</div>

---

## ✨ What you can do

| Feature | What it does |
|---|---|
| **Text → Video** | Generate short clips with the integrated LTX-Video Diffusers adapter when the GPU passes the runtime safety checks |
| **Image → Video** | Use a reference image with the native LTX path on eligible hardware |
| **Image Motion** | Turn a still image into an MP4 with smooth pan/zoom animation on lower-memory PCs |
| **Hardware advisor** | Inspect GPU, VRAM, RAM, disk and CUDA availability before selecting a generation path |
| **Local job queue** | Queue, monitor and cancel short renders and full production jobs; review results and download MP4 files |\n| **Multi-scene production** | Local scripts, scene prompts, generative clips, Piper narration, captions, music/SFX, transitions and MP4 assembly when prerequisites are configured |
| **Local-first workflow** | Run the UI, API, queue and media engine in one Python application |

> **Important distinction:** Image Motion creates an animated video from an existing image. It does **not** generate new visual content and is not presented as generative AI.

## 🎬 Full local production pipeline

The Studio now includes a multi-scene production endpoint and browser controls. It can orchestrate these local stages when their prerequisites are installed:

1. **Script package:** a local Ollama model writes the script, hook, title, and scene prompts for educational, facts, story, documentary, motivational, podcast, product-explainer, news-style, how-to, and Shorts formats.
2. **Scene generation:** the configured native video engine generates short clips for each scene. A failed or unavailable generative engine stops the job; Image Motion is not substituted.
3. **Narration:** local Piper generates speech. Dialogue labelled `SPEAKER 1:` and `SPEAKER 2:` can use separate local `.onnx` voice files supplied in the voice mapping.
4. **Editing and audio:** FFmpeg assembles the scenes, applies cuts or dissolves, burns subtitles, and mixes optional local music and up to five sound effects.
5. **Export and project data:** portrait, landscape, square and other supported aspect ratios can be exported at 30 or 60 FPS. A `timeline.json` project description is saved beside the MP4 and can be opened from job history.

### Local prerequisites

- Ollama installed and running at `http://127.0.0.1:11434`, with the selected model already downloaded. Set `OLLAMA_MODEL` to choose it.
- Piper installed locally and available on `PATH`; set `PIPER_MODEL` to a local voice `.onnx` file.
- FFmpeg and FFprobe available on `PATH`, with subtitle/libass support for burned-in captions.
- The video model selected by the existing hardware/model setup must be installed and pass its runtime safety gate.

The Studio UI can submit a complete production job through `POST /api/produce`. Job history exposes the resulting MP4 and the project timeline at `/projects/{job_id}/timeline.json`.

**Validation status:** the pipeline and unit tests are committed, but actual multi-scene inference, Piper voice compatibility, FFmpeg filters, 30/60 FPS export, and full Windows operation still need to be run on the target PC. Long projects can take substantial time and storage because each scene is generated separately.

## 🖥️ Hardware & honest expectations

The integrated LTX adapter uses a conservative planning gate:

- NVIDIA GPU with CUDA-enabled PyTorch
- **10 GB total VRAM** and at least **8.5 GB currently free**
- At least **32 GB system RAM**
- At least **50 GB free disk space**

Passing these checks only means the machine may be suitable for a guarded test. It is **not a guarantee** of successful inference. Validate with a short generation on the target machine.

| Your hardware | Expected experience |
|---|---|
| **GTX 1650 4 GB + 64 GB RAM** | Studio and hardware advisor can run; LTX is blocked by the VRAM safety gate; Image Motion can render still-image MP4s |
| **10–12 GB NVIDIA GPU** | May pass the planning gate; test a short clip first |
| **16 GB+ NVIDIA GPU** | More memory headroom; model/runtime compatibility still matters |
| **CPU-only** | Hardware scan and Image Motion; LTX diffusion generation is disabled |

<details>
<summary><strong>Why the GTX 1650 4 GB is not enough for LTX</strong></summary>

System RAM cannot replace dedicated GPU VRAM. CPU offload can reduce GPU memory pressure, but it does not make a 4 GB GPU equivalent to a supported high-memory GPU. Do not bypass the runtime gate or force-load LTX on hardware that fails it.

The legacy LTX-Video Diffusers memory example is approximately 10 GB VRAM. LTX-2.5 is a newer model family with substantially higher published requirements and is not part of this adapter's model catalog.

</details>

## 🚀 Get started

### Windows

1. Install a **64-bit Python 3.11 or newer**. The launcher automatically selects the newest installed Python 3 version it can run; you do not need to install exactly Python 3.11.
2. Download or clone this repository and open the `AI video generation` project folder.
3. Run the installer:

   ```bat
   ONE_CLICK.bat install
   ```

4. Start the studio:

   ```bat
   ONE_CLICK.bat start
   ```

5. Open the local app at **http://127.0.0.1:8765** if it does not open automatically.

Optional checks:

```bat
CHECK_GPU.bat
TEST.bat
```

The base application dependencies are kept lightweight. Python 3.14 may work for the base Studio, but optional AI packages such as CUDA-enabled PyTorch have their own Python-version and CUDA compatibility limits. The LTX installer can therefore require a supported Python environment even when the base Studio runs on a newer Python.

The base installation does not need to install a large AI framework or download LTX weights just to open the Studio.

### Enable LTX on compatible hardware

On a supported CUDA machine, run:

```bat
ONE_CLICK.bat install-ltx
```

The LTX adapter loads lazily. Model weights are fetched on the first eligible generation request and can be reused from the local cache afterward. The first download requires internet access and substantial disk space.

**Default conservative profile:** up to 4 seconds, 12 FPS, 512-pixel long edge and 20 denoising steps.

## 🎞️ Image Motion on lower-memory PCs

1. Open **Image Motion** in the Studio.
2. Upload a PNG, JPEG or WebP image (up to 20 MB).
3. Choose aspect ratio, duration and frame rate.
4. Render and preview/download the MP4.

This path uses Pillow and the FFmpeg binary supplied by `imageio-ffmpeg`. It animates the supplied still image with a deterministic camera move; it does not synthesize new scenes or objects.

## 🧩 How it is built

```text
Browser UI (web/)
      │  loopback HTTP / JSON
      ▼
studio.py  ───── hardware_scanner.py ─── model_selector.py
      │
      ▼
engine/job_manager.py
      │
      ▼
engine/video_engine.py
      ├── LTX-Video · PyTorch + Diffusers (eligible CUDA GPUs)
      └── Image Motion · Pillow + imageio-ffmpeg
      │
      ▼
outputs/*.mp4
```

The app uses one local Python process for the web API and job queue. Jobs run sequentially to reduce GPU memory pressure. The runtime repeats its own hardware capability checks immediately before model loading; the UI's disabled state is not the only safety control.

## 🔌 Local API

The server binds to loopback. The main endpoints are:

| Endpoint | Method | Purpose |
|---|:---:|---|
| `/api/health` | GET | Engine, hardware and LTX capability |
| `/api/config` | GET | UI/API limits and supported modes |
| `/api/hardware` | GET | Hardware inventory |
| `/api/models` | GET | Model recommendation and runtime gates |
| `/api/generate` | POST | Queue a short native video or Image Motion job |\n| `/api/produce` | POST | Queue a complete local multi-scene production |
| `/api/jobs` | GET | Recent local jobs |
| `/api/jobs/{id}` | GET | Job status and result |
| `/api/jobs/{id}/cancel` | POST | Cancel a queued/running job |
| `/outputs/{file}.mp4` | GET | Preview or download a result |

Example Image Motion request:

```json
{
  "mode": "image-motion",
  "prompt": "Slow cinematic push-in",
  "image_data": "data:image/jpeg;base64,...",
  "aspect": "16:9",
  "duration": 4,
  "fps": 24,
  "motion": "balanced"
}
```

## 📁 Project layout

```text
AI video generation/
├── engine/          # Job manager and video runtime
├── web/             # Browser interface
├── tests/           # Automated regression tests
├── docs/            # Architecture and model-selection notes
├── studio.py        # Local web server and JSON API
├── hardware_scanner.py
├── model_selector.py
├── channel_pipeline.py
├── ONE_CLICK.bat    # Windows setup and launch
├── CHECK_GPU.bat    # Hardware report
└── TEST.bat         # Test runner
```

Generated files, local databases, logs, uploaded images and cached model weights are runtime data; they should not be committed as source files.

## 🧪 Tests & development

Run the regression suite from the project directory:

```bash
python -m unittest discover -s tests -v
```

Compile the Python modules:

```bash
python -m py_compile studio.py hardware_scanner.py model_selector.py channel_pipeline.py engine/*.py
```

The repository includes tests for model selection, hardware gates, job management and the video engine. **The presence of tests does not mean GPU inference has been validated:** a compatible NVIDIA GPU, CUDA PyTorch, Diffusers and cached model weights are required to validate actual LTX generation. Windows launchers should also be tested on the target Windows machine.

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md) — components, runtime boundaries and design decisions
- [Hardware-aware model selection](docs/MODEL_SELECTION.md) — explicit model eligibility gates

## ⚠️ Current limitations

- The GTX 1650 4 GB is below the LTX safety threshold; use Image Motion on that hardware.
- Image Motion is still-image animation, not generative video.
- The LTX adapter is implemented but has **not** been physically validated on the target Windows GPU.
- First-time model download requires internet; cached weights can be reused offline.
- Optional YouTube research/OAuth, Ollama and Piper workflows have their own external requirements.

## 📜 License & attribution

Check the license terms for LTX-Video and every optional dependency before commercial use or redistribution of model weights. OfflineYouTubeStudio is an independent integration and is not affiliated with Lightricks.
