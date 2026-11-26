"""Shared Foundry Local setup: everything (app data, model cache, logs) stays inside this folder.

GPU workaround: the SDK's own CUDA EP bundle download returns HTTP 403 (see out/diag/), so when
tools/cuda-ep exists (pip --target onnxruntime-gpu==1.32.0 + nvidia CUDA 13 wheels, plus
onnxruntime-genai-cuda.dll from the onnxruntime-genai-cuda==0.20.0 wheel) we point the
native runtime's FOUNDRY_LOCAL_CUDA_EP_LIBRARY override at it. Env/PATH changes live in this Python process only
(no system PATH or registry change). Verified 2026-11-26 with qwen2.5-0.5b-instruct-cuda-gpu:4 (out/diag/).
Rebuild tools/cuda-ep (about 1.9 GB) with:
  pip install --no-cache-dir --no-deps --only-binary=:all: --target tools/cuda-ep onnxruntime-gpu==1.32.0 ^
    "nvidia-cuda-runtime~=13.0" "nvidia-cuda-nvrtc~=13.0" "nvidia-cufft~=12.0" "nvidia-curand~=10.0" ^
    "nvidia-cudnn-cu13~=9.0" "nvidia-cublas~=13.0" "nvidia-nvjitlink~=13.0"
  then copy onnxruntime_genai/onnxruntime-genai-cuda.dll out of the onnxruntime-genai-cuda==0.20.0 wheel
  into tools/cuda-ep/onnxruntime/capi/.
"""
import os
import sys
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "fl-data"
CUDA_EP = HERE / "tools" / "cuda-ep"
CUDA_DLL_DIRS = [CUDA_EP / "onnxruntime" / "capi", CUDA_EP / "nvidia" / "cu13" / "bin" / "x86_64", CUDA_EP / "nvidia" / "cudnn" / "bin"]

if CUDA_EP.is_dir() and "FOUNDRY_LOCAL_CUDA_EP_LIBRARY" not in os.environ:
    for d in CUDA_DLL_DIRS:
        os.add_dll_directory(str(d))
    os.environ["PATH"] = os.pathsep.join(map(str, CUDA_DLL_DIRS)) + os.pathsep + os.environ["PATH"]
    os.environ["FOUNDRY_LOCAL_CUDA_EP_LIBRARY"] = str(CUDA_DLL_DIRS[0] / "onnxruntime_providers_cuda.dll")
    # The SDK preloads whichever `onnxruntime` package importlib finds: make that the GPU build (same 1.32.0).
    sys.path.insert(0, str(CUDA_EP))
    # ponytail: workaround, not a supported path. The pip CUDA provider is a "provider bridge" DLL: a plain
    # LoadLibrary (what Foundry and onnxruntime.dll do) fails DllMain with Win32 error 1114 until an ORT that
    # carries the bridge host has loaded it. The Python ORT (pybind) does, so let it load the DLL first;
    # Foundry's later LoadLibrary then reuses the already-initialised module. Drop this once the official
    # cuda-ep bundle download works again.
    import onnxruntime as _ort
    _ort.register_execution_provider_library("cuda-bridge-host", os.environ["FOUNDRY_LOCAL_CUDA_EP_LIBRARY"])

from foundry_local_sdk import Configuration, FoundryLocalManager  # noqa: E402  (env must be set first)


def manager() -> FoundryLocalManager:
    for sub in ("app", "models", "logs"):
        (DATA / sub).mkdir(parents=True, exist_ok=True)
    config = Configuration(
        app_name="hybrid-llm-bench",
        app_data_dir=str(DATA / "app"),
        model_cache_dir=str(DATA / "models"),
        logs_dir=str(DATA / "logs"),
        disable_nonessential_telemetry=True,
    )
    return FoundryLocalManager(config)


@contextmanager
def serve(variant: str):
    """Load one CUDA model variant and yield the base URL of Foundry Local's OpenAI-compatible endpoint."""
    with manager() as m:
        m.download_and_register_eps(["CUDAExecutionProvider"], None)
        model = m.get_catalog().get_model_variant(variant)
        if model is None:
            sys.exit(f"{variant} is not in the catalog (is the CUDA EP registered?)")
        if not model.is_cached:
            model.download(lambda p: print(f"\r  download {p:5.1f}%", end="", flush=True))
        model.load()
        m.start_web_service()
        try:
            yield m.urls[0].rstrip("/") + "/v1"
        finally:
            model.unload()
