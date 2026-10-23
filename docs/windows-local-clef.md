# Local Clef on Windows with D: storage

The scripts acquire a pinned portable llama.cpp runtime and a pinned quantized Clef-Flash model. They install no drivers or global software. The pipeline talks only to the loopback SystemOne endpoint. A real inference failure remains a failure; no demo substitution is allowed. Model and domain validity are separate from whether this runtime returns probabilities.

On the tested NVIDIA GTX 1660 Ti 6 GB machine, the Vulkan route with 20 GPU layers completed real rubric requests and is the recommended starting configuration for this computer. CPU remains the portable script default and also passed the two-request check, but was much slower and left less available RAM. Memory headroom was small on both routes; close other applications before a larger pilot. See the measured probes below before planning a long run.

## Set storage before any installation

Open PowerShell in the checkout on D: and run:

```powershell
. .\scripts\Set-ProjectEnvironment.ps1 | Out-Null
```

Do this in every new terminal before venv creation, pip, builds or tests. The environment changes last only for that process and its children. They cover `TEMP`, `TMP`, `TMPDIR`, `PIP_CACHE_DIR`, `HF_HOME`, `HF_HUB_CACHE`, `HF_XET_CACHE`, `TORCH_HOME`, `XDG_CACHE_HOME`, `LLAMA_CACHE` and `UV_CACHE_DIR`. New project caches and temporary files go under `D:\...\cache\`. Existing system executables on C: are reused; the scripts do not install anything there. Put the virtual environment on D: too.

Storage defaults to the checkout root. If needed, pass `-StorageRoot D:\clef-local` to environment/setup/start. C: roots, junctions and symlink storage paths are rejected. The checked-in HTTP config resolves outputs/cache relative to this checkout; it assumes the checkout is on D:. For a different configuration location, explicitly set its outputs/cache paths to D: before running it. Company snapshots/configs/results must remain in a private directory on D: outside the public checkout.

## Acquire and verify the assets

```powershell
.\scripts\Setup-ClefLocal.ps1
```

The script downloads over HTTPS using existing `curl.exe`, with retries and a resumable `.part` file on D:. It verifies both exact byte count and SHA-256 before renaming the download or extracting the runtime. Existing valid files are verified and reused. A wrong hash/size stops setup and leaves the suspect file for inspection; it is never executed. Download/storage paths are:

| Asset | Default path | Size / identity |
| --- | --- | --- |
| CPU runtime archive | `cache/downloads/llama-b11669-bin-win-cpu-x64.zip` | 19,537,886 bytes; llama.cpp b11669 |
| Extracted CPU runtime | `runtime/llama-b11669-cpu/` | All archive contents, including licenses, retained |
| Model | `models/clef-flash/Clef-Flash-Q4_K_M.gguf` | 6,486,448,288 bytes; Q4_K_M |

Pinned sources and SHA-256 values:

* [CPU runtime](https://github.com/ggml-org/llama.cpp/releases/download/b11669/llama-b11669-bin-win-cpu-x64.zip): `37b3efcf962847ca869745fd4ccf7f5e7e8dacfeff9fa3523b4ca8cdc66d632b`.
* [Quantized model at immutable revision 8aa35d1cc7e141f3771e564eeb630a501597c681](https://huggingface.co/ggml-org/Clef-Flash-GGUF/resolve/8aa35d1cc7e141f3771e564eeb630a501597c681/Clef-Flash-Q4_K_M.gguf): `3626116623ca8d89641952471fac9ce12af84fb3517520029a2ac6f5146868a2`.

Allow room on D: for the approximately 6.5 GB model, partial downloads, runtime, caches and results. Model loading also requires substantial RAM. The model file size is not a peak-memory estimate. No model execution happens during setup.

## Start a local CPU server

In the first PowerShell terminal:

```powershell
.\scripts\Start-ClefLocal.ps1
```

The foreground server binds `127.0.0.1:30000` and uses alias `Cloudflare/clef-flash`, matching the client's exact model-ID check. Stop it with Ctrl+C. Before execution, the start script rechecks the pinned archive, compares extracted files to the archive, rejects unexpected executable/DLL files and verifies the model hash. The full model hash check can take time; it does not download anything.

Initial CPU settings are `--ctx-size 2048 --batch-size 2048 --ubatch-size 2048 --parallel 1 --threads 6 --n-gpu-layers 0`, with an explicit `-m` local model path. Clef's full prompt must fit a single microbatch: do **not** reduce `--ubatch-size` to 128. If a real rubric request does not fit, stop and adjust context, batch and microbatch together, then update the config's inference identity before rescoring. The default settings are a bounded feasibility starting point, not a throughput guarantee.

In a second terminal, set the environment again and run a small pilot:

```powershell
. .\scripts\Set-ProjectEnvironment.ps1 | Out-Null
.\.venv\Scripts\python.exe -m goal_eval benchmark --config examples/synthetic/clef-cpu-http.yaml --limit 3
```

This uses real quantized model inference on fabricated goals. The limit is an input prefix and can cover only one year; its report is labeled partial. For complete synthetic snapshots, run `goal_eval run` with that config and no limit after feasibility is established. The HTTP timeout is 600 seconds with no automatic retry, so a slow CPU request may take several minutes and failures remain explicit. Configured inference values identify the operator-started server; the HTTP client does not apply them to the server. Change the recorded values if you change the runtime, quantization, thread count, port or GPU layers.

The Q4_K_M model is not numerically identical to the original full-precision release. Neither successful requests nor hash checks establish rating accuracy, calibration or equivalence across years. Quantized-model results should not be mixed with demo/full-precision scores under one cache identity. CPU latency and memory fit depend on hardware and prompt length; the million-record workload remains unbenchmarked.

## Tested Vulkan route for this machine

For an already installed compatible GPU/driver, setup can acquire a separate portable Vulkan runtime:

```powershell
.\scripts\Setup-ClefLocal.ps1 -Backend vulkan
.\scripts\Start-ClefLocal.ps1 -Backend vulkan -GpuLayers 20
```

In a second terminal:

```powershell
. .\scripts\Set-ProjectEnvironment.ps1 | Out-Null
.\.venv\Scripts\python.exe -m goal_eval benchmark --config examples/synthetic/clef-vulkan-http.yaml --limit 3
```

No drivers are installed. If Vulkan or VRAM allocation fails, the error is visible; the script does not silently switch runtimes. Twenty layers worked in the bounded probe on this computer; other hardware and prompt lengths need their own check. The [pinned Vulkan archive](https://github.com/ggml-org/llama.cpp/releases/download/b11669/llama-b11669-bin-win-vulkan-x64.zip) is 32,182,350 bytes with SHA-256 `2c07574e7bde71321cb785282b20cc821e951132149eeceeea32ddebdbf0598e`; it extracts to `runtime/llama-b11669-vulkan`. The same verified model file is reused. [The Vulkan config](../examples/synthetic/clef-vulkan-http.yaml) records this runtime/hash and 20 layers, and keeps its results/cache separate from the CPU config. Update its inference identity if changing any settings.

## Observed bounded probe, 2026-10-23

The pinned 6,486,448,288-byte Q4_K_M model passed the SHA-256 check. Native llama.cpp b11669 reported a Clef decision model. With the already installed GTX 1660 Ti 6 GB and driver 457.49, Vulkan needed no driver changes. The server used `127.0.0.1:30000`, alias `Cloudflare/clef-flash`, context/batch/microbatch 2048, parallelism 1, six threads and 20 GPU layers.

| Observation | Result |
| --- | --- |
| Server ready after process launch | 7.64 seconds; launcher file verification adds separate time |
| Full rubric request 1 | 1,061 input tokens, zero generated output tokens; 5.75 seconds |
| Full rubric request 2 | 1,036 input tokens, zero generated output tokens; 4.28 seconds |
| Response validation | Model ID and all six probability distributions passed for both requests |
| Peak server RAM observed | 7,197,315,072 bytes, approximately 6.7 GiB |
| Total GPU memory used during probe | Approximately 5,003 MiB, including roughly 700 MiB of desktop usage |
| Available system RAM while active | Approximately 1.4 GB at the observed point |

The additional GPU usage was roughly 4,300 MiB. These readings describe this short probe and its concurrent desktop load, not a memory guarantee. It fit with little headroom; larger prompts, different settings or other applications can exhaust RAM/VRAM. Close other applications and run a bounded pilot before attempting substantial scoring. Do not extrapolate the two request times into a mass-scoring promise: sustained throughput, broader text-length variation and the potential 1.2 million-record workload remain unmeasured.

This was actual quantized-model execution, not the demo scorer or fixture server. It does not validate ratings, probability calibration, quantization equivalence or causal interpretation. Local detailed evidence is retained in `outputs/clef-local-check/vulkan.json` and the adjacent server logs; these D: outputs are ignored by Git. All acquired model/runtime archives, partial downloads, caches and temporary project files were kept on D:.

### CPU comparison on the same computer

The pinned native CPU runtime also completed the same two full-rubric requests with all six probability distributions valid. It used the same model, alias, context/batch/microbatch 2048, one parallel request and six threads, with zero GPU layers.

| Observation | Result |
| --- | --- |
| Server ready after process launch | 8.68 seconds; launcher verification is separate |
| Request 1 | 1,061 input tokens; 52.16 seconds |
| Request 2 | 1,036 input tokens; 48.84 seconds |
| Peak server process resident memory | 8,240,975,872 bytes, approximately 7.67 GiB |
| Available system RAM at the observed point | 550,948 KiB, approximately 0.53 GiB |

CPU execution succeeded but was much slower than Vulkan and left very little RAM headroom under the observed desktop load. These are two bounded requests, not a sustained CPU benchmark or a guarantee that larger jobs fit. Prefer the tested Vulkan configuration on this computer, close other applications, and retain a small pilot before substantial scoring. Local evidence is in the ignored D: files `outputs/clef-local-check/cpu.json` and `cpu-memory.json`.

### Complete synthetic workflow integration

The reviewed launcher (`Start-ClefLocal.ps1 -Backend vulkan -GpuLayers 20`) and the Vulkan HTTP configuration subsequently completed the full 823-record synthetic workflow in 70.38 seconds: 256/315/252 records for 2023/2024/2025, 472 records with combined-text scores and 351 language exclusions, with zero failed rows or inference failures. The run made 14 new native model requests and reused 581 cached scores. CSV, Parquet and HTML outputs were written; all 2,380 distributions across the four quality dimensions checked were finite, within range and summed to one within tolerance. These deliberately repeated synthetic templates make this an integration check, **not a throughput benchmark for unique goals**; no mass-run extrapolation follows from its elapsed time. Local evidence is in `outputs/clef-vulkan/runs/20261023T154233Z-73807fac/manifest.json`, the generated report and `outputs/clef-local-check/launcher-vulkan.log`, all ignored on D:.

All runtime/model/download/partial/cache/result paths are ignored by Git. Keep the downloaded license files with their runtime. Repository publication should contain only the scripts, pinned identities, documentation and fabricated examples.
