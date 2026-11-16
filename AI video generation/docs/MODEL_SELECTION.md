# Hardware-aware model selection

The scanner returns a JSON inventory with GPU name, total/free VRAM, driver, temperature, utilization, system RAM, free disk and optional PyTorch/CUDA state.

The selector uses explicit policy gates, not a trained classifier:

1. Is the model integrated into this runtime?
2. Is an NVIDIA GPU and CUDA-enabled PyTorch available?
3. Does total VRAM meet the 10 GB planning floor?
4. Is at least 8.5 GB VRAM currently free?
5. Is system RAM at least 32 GB?
6. Is at least 50 GB disk space available?

If any required gate fails, the selector returns `no-validated-fit`. The UI still offers the Image Motion renderer, but labels it as non-generative media rendering.

For the user's GTX 1650 4 GB, the expected outcome is no validated LTX fit. 64 GB system RAM does not override the VRAM gate.

The current LTX-2.5 generation is not in this runtime catalog: its official requirements list 32 GB+ NVIDIA VRAM and 100 GB free storage. The integrated candidate is the older LTX-Video Diffusers pipeline, whose published memory example is approximately 10 GB VRAM.
