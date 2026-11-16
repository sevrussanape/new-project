# Hardware-aware model selection

## Responsibility boundaries

- `hardware_scanner.py` is read-only diagnostics. It queries `nvidia-smi`, OS memory/disk information and optional PyTorch CUDA availability. It does not install packages, download weights or change the machine.
- `model_selector.py` evaluates the inventory against the catalog of **implemented runtime adapters**. It is a deterministic policy engine, not an ML classifier.
- `studio.py` exposes the recommendation and refuses production jobs when no integrated model is eligible.
- `engine/video_engine.py` calls the same selector again immediately before inference. The browser and API are not trusted as the only safety barrier.

## Current integrated catalog

Only `ltx-video-diffusers` is currently integrated. It supports text-to-video and image-to-video through the in-process Diffusers adapter.

| Gate | Current policy |
|---|---:|
| Total dedicated VRAM | At least 10 GB |
| Currently free VRAM | At least 8.5 GB |
| System RAM | At least 32 GB |
| Free disk | At least 50 GB |
| CUDA | CUDA-enabled PyTorch must be available |
| Adapter | Must be registered as runtime-supported |

Missing VRAM, free-memory, RAM, disk or CUDA evidence is not treated as a pass. Passing the policy only means the machine may attempt inference; it does not guarantee a successful run.

## End-to-end flow

```text
hardware_scanner.scan_hardware()
    → model_selector.recommend_models(inventory)
        → studio API / UI recommendation
            → engine.video_engine.ltx_capability(inventory)
                → LTXRuntime.generate(...)
```

The adapter gate delegates to the same model selector used by the advisor. This prevents a machine from being shown as compatible by one component and rejected (or incorrectly accepted) by another due to duplicated rules.

## Installation and downloads

Scanning and recommending are intentionally separate from installation. Installing CUDA PyTorch/Diffusers is an explicit `ONE_CLICK.bat install-ltx` action. LTX weights are downloaded lazily on the first eligible generation request and cached by Hugging Face Hub. After packages and weights are present, the runtime can be used offline.

Do not automatically download a model merely because a GPU name was detected. Hardware name alone does not establish available VRAM, free VRAM, CUDA compatibility, disk capacity or model support.

## Adding another model safely

A model can be added to `MODEL_CATALOG` only after:
1. A real adapter is implemented and invoked by the generation dispatcher.
2. The model's supported tasks, precision, dependencies and resource policy are documented.
3. The adapter checks current hardware immediately before loading.
4. A smoke test and failure/cleanup behavior are added.
5. The README and hardware tests reflect the actual requirements.

A catalog entry without a runtime adapter must never be selected as runnable.
