# OfflineYouTubeStudio

**A local-first video production workspace with hardware-aware model selection and a native Python inference backend.**

OfflineYouTubeStudio runs its website, API, job queue, hardware scanner and media engine in one Python application. It does not require a separate workflow server or a workflow editor.

## What works in this build

- Local web UI served at `http://127.0.0.1:8765`.
- Hardware scanner for NVIDIA GPU/VRAM, CPU, system RAM, disk and optional PyTorch/CUDA details.
- Explainable model advisor that only recommends models integrated into this runtime and checks current free VRAM.
- Native LTX-Video Diffusers adapter, lazily loaded in the Studio Python process on compatible CUDA hardware.
- A single-worker background job queue with status, progress, cancellation, MP4 preview and direct downloads. Job history is persisted in a local SQLite database; jobs interrupted by a restart are clearly marked rather than silently lost.
- Bounded queue (up to three waiting jobs), request validation, 20 MB image limit, 40-megapixel image safety limit, prompt-length limits and browser security headers.
- Low-resource Image Motion renderer: upload a still image and create a real MP4 with a smooth camera move. This is deliberately labelled as image animation, not generative AI.
- Existing Ollama script generation, niche research, Piper narration, subtitle creation and YouTube OAuth pipeline remain available, with video generation routed through the native engine.

## Hardware truth and supported modes

The legacy LTX-Video Diffusers memory example reports approximately **10 GB VRAM**. This project uses a conservative gate of 10 GB total VRAM, 8.5 GB currently free VRAM, CUDA-enabled PyTorch, and 50 GB free disk. This is a planning gate, not a guarantee; a short validation generation is still required. LTX-2.5 is the newer model family and its official system-requirements page lists 32 GB+ NVIDIA VRAM and 100 GB free storage, so it is deliberately not selected for this low-resource build.

| Hardware | Application behavior |
|---|---|
| GTX 1650 4 GB + 64 GB RAM | Studio and hardware advisor work. LTX is disabled. Image Motion mode creates MP4 from a supplied image. |
| 10–12 GB CUDA GPU | LTX may pass the planning gate; test a short clip first. |
| 16 GB+ CUDA GPU | Better headroom for native LTX inference; exact model/runtime compatibility still applies. |
| CPU-only | Hardware scan and image-motion rendering work; LTX diffusion generation is disabled. |

System RAM does not replace dedicated VRAM. CPU offload can reduce GPU memory pressure but may be slow and is not a promise that a 4 GB GPU can run LTX.

## Quick start (Windows 11)

1. Install Python 3.11 x64.
2. Extract this repository to a normal folder (not inside another AI application's plugin directory).
3. Double-click `ONE_CLICK.bat` or run `ONE_CLICK.bat install` once.
4. Run `ONE_CLICK.bat start`; the browser opens at `http://127.0.0.1:8765`.
5. Run `CHECK_GPU.bat` for a separate hardware report.
6. Run `TEST.bat` any time to execute the built-in regression tests.

Base installation only installs Pillow and imageio-ffmpeg. It does not install a large AI framework or download model weights.

### Enable native LTX on a compatible GPU

Run:

```bat
ONE_CLICK.bat install-ltx
```

This installs CUDA-enabled PyTorch and Diffusers/Transformers/Accelerate. The LTX weights are downloaded from Hugging Face on the first eligible generation request. After the weights are cached locally, inference can run without internet. Check the model license before redistribution or commercial use.

The native LTX safety profile is intentionally short: 512-pixel long edge, at most 4 seconds, 12 FPS and 20 denoising steps. The default model ID is `Lightricks/LTX-Video`; it can be overridden with `OFFLINE_STUDIO_LTX_MODEL` before launching the app. Model loading is lazy so the Studio can start without PyTorch or model weights installed. The legacy LTX-Video repository is no longer the actively developed line; the current LTX-2.5 requirements are substantially higher and need a separate adapter.

## Low-VRAM image-motion mode

On a GTX 1650 4 GB, select **Image Motion**, upload a PNG/JPEG/WebP image, choose aspect ratio/duration/FPS, and render. The app uses Pillow plus the FFmpeg binary bundled by `imageio-ffmpeg` to produce MP4. The camera move is deterministic pan/zoom; it does not invent new objects or synthesize motion like a diffusion video model.

## API

The automated regression suite can be run with `TEST.bat` or `python -m unittest discover -s tests -v`. The local server binds to loopback only.

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/health` | GET | Engine, hardware and LTX capability |
| `/api/config` | GET | UI/API limits and supported generation modes |
| `/api/hardware` | GET | Raw hardware inventory |
| `/api/models` | GET | Model recommendation and runtime gates |
| `/api/generate` | POST | Queue LTX or Image Motion job |
| `/api/jobs` | GET | Recent local jobs |
| `/api/jobs/{id}` | GET | Job progress/result |
| `/api/jobs/{id}/cancel` | POST | Cancel queued/running job |
| `/outputs/{file}.mp4` | GET | Preview/download local result |

Example Image Motion request shape:

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

## Project structure

```text
OfflineYouTubeStudio/
├── studio.py                 # Local web server and JSON API
├── hardware_scanner.py       # GPU/VRAM/RAM/disk/CUDA inventory
├── model_selector.py         # Explainable hardware-aware model advisor
├── engine/
│   ├── video_engine.py       # Native LTX + Image Motion adapters
│   └── job_manager.py        # Single-worker queue, progress, cancellation
├── web/index.html            # Browser UI
├── channel_pipeline.py      # Ollama -> native video -> Piper -> FFmpeg -> YouTube
├── niche_research.py        # Public search-based niche research
├── safe_mode.py             # NVIDIA telemetry
├── models/                   # Reserved for local model assets
├── uploads/                  # Temporary reference images
├── outputs/                  # Generated MP4s and channel assets
├── logs/                     # Runtime logs
├── tests/                    # Automated tests
└── docs/                     # Architecture and model selection notes
```

## Development and tests

```bash
python -m unittest discover -s tests -v
python -m py_compile studio.py hardware_scanner.py model_selector.py channel_pipeline.py engine/*.py
```

Tests cover model selection, VRAM gates, missing CUDA, and the low-resource renderer. GPU inference tests require a compatible NVIDIA GPU, CUDA PyTorch, Diffusers and downloaded model weights; they are not simulated by unit tests.

## Limitations

- The GTX 1650 4 GB cannot be promised to run full LTX diffusion. This build disables LTX under the safety threshold rather than risking repeated CUDA out-of-memory failures.
- Image Motion is a deterministic still-image animation, not generative video.
- The native LTX adapter is implemented but has not been executed on the user's Windows GPU in this development environment.
- First LTX model load needs internet and substantial disk space; subsequent inference can be offline.
- YouTube research and OAuth upload require internet. Ollama, Piper voice files and FFmpeg are separate optional dependencies for the channel pipeline.

## License and attribution

Check each upstream model's license and the licenses of all optional dependencies before using outputs commercially or redistributing model weights. LTX-Video is developed by Lightricks. This project is an independent integration and is not affiliated with Lightricks.
