# Model and hardware guide

## Current integrated model

**LTX-Video v0.9.x through Hugging Face Diffusers**, loaded directly inside the OfflineYouTubeStudio Python process. The UI does not call an external model server. This is the legacy LTX-Video family; the current LTX-2.5 family is intentionally not targeted by this low-resource adapter.

- Model ID: `Lightricks/LTX-Video`
- Tasks: text-to-video and image-conditioned video generation (pipeline support dependent on model revision)
- Runtime: PyTorch + Diffusers + Accelerate
- Loading: lazy, with Diffusers model CPU offload and VAE tiling when available
- First use: downloads/caches model weights; later inference can run offline

The published legacy Diffusers LTX example reports approximately 10 GB VRAM. Offline Studio gates native LTX at 10 GB total VRAM and 8.5 GB currently free VRAM, plus CUDA and disk checks. These are conservative project gates, not official hardware guarantees. The official LTX-2.5 system-requirements page lists 32 GB+ NVIDIA VRAM and 100 GB free storage, so this application does not claim to support LTX-2.5.

## Hardware recommendations

| Hardware | Studio behavior |
|---|---|
| 4 GB VRAM (GTX 1650) | LTX disabled; use Image Motion renderer for still-to-MP4 output |
| 6–8 GB VRAM | LTX remains disabled by default; do not bypass gate without measured benchmarks |
| 10–12 GB VRAM | May pass the LTX planning gate; start with a short low-resolution test |
| 16 GB+ VRAM | Better headroom; validate exact driver, precision and model revision |

64 GB system RAM is useful for CPU offload and media work but cannot replace GPU VRAM. FP8 is not assumed: support depends on GPU architecture and the selected model/runtime.

## Low-memory renderer

Image Motion uses Pillow to create a smooth pan/zoom from one uploaded still image and `imageio-ffmpeg` to encode MP4. It is a media renderer, not AI video synthesis. It is included so a 4 GB GPU owner can still use the application to create local video assets.

## Install native LTX dependencies

On a compatible CUDA GPU, run `ONE_CLICK.bat install-ltx`. This installs CUDA PyTorch, Diffusers, Transformers, Accelerate and Safetensors. The model is downloaded on first use. The current safety profile caps clips at 4 seconds, 12 FPS and 20 inference steps to limit memory pressure. Do not run this optional installation just to use the base app or Image Motion mode.

Official references:
- [LTX-Video model and checkpoints](https://huggingface.co/Lightricks/LTX-Video)
- [Diffusers LTX-Video pipeline and memory example](https://huggingface.co/docs/diffusers/main/api/pipelines/ltx_video)
- [Current LTX-2.5 system requirements](https://docs.ltx.io/open-source-model/getting-started/system-requirements/)
- [PyTorch installation selector](https://pytorch.org/get-started/locally/)

## Safety

The model advisor is deterministic rule-based software, not a trained AI model. It explains why the detected PC does or does not meet the runtime gate. The engine repeats the capability check before loading weights. A recommendation is never a guarantee; run a short validation job before longer production tasks.
