#!/usr/bin/env python3
"""Prepare the official GGUF baseline on Colab without changing production code."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

import requests
from huggingface_hub import hf_hub_download

ROOT = Path(__file__).resolve().parents[2]
TAG = "b11264"  # Same release as the packaged Windows Brain.
MODEL = "Qwen3-4B-Q4_K_M.gguf"


def run(command, **kwargs):
    print("+", " ".join(map(str, command)), flush=True)
    return subprocess.run(list(map(str, command)), check=True, **kwargs)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_asset(asset, destination):
    if not destination.exists() or sha256(destination) != asset["digest"].split(":", 1)[1]:
        print("Downloading official asset:", asset["name"], flush=True)
        with requests.get(asset["browser_download_url"], stream=True, timeout=(30, 120)) as response:
            response.raise_for_status()
            with destination.open("wb") as handle:
                for chunk in response.iter_content(8 * 1024 * 1024):
                    handle.write(chunk)
    if "sha256:" + sha256(destination) != asset["digest"]:
        raise RuntimeError("Official llama.cpp asset checksum mismatch")


def main():
    run(["nvidia-smi"])
    pack = ROOT / "brain_local"
    pack.mkdir(exist_ok=True)
    work = Path("/content/agcn-baseline-runtime")
    work.mkdir(exist_ok=True)
    release = requests.get(
        f"https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/{TAG}", timeout=30
    )
    release.raise_for_status()
    release = release.json()
    names = [f"llama-{TAG}-bin-ubuntu-cuda-12.8-x64.tar.gz",
             f"cudart-llama-{TAG}-bin-ubuntu-cuda-12.8-x64.tar.gz"]
    assets = {asset["name"]: asset for asset in release["assets"]}
    binary_error = ""
    source_commit = release["target_commitish"]
    try:
        for name in names:
            asset = assets[name]
            archive = work / name
            download_asset(asset, archive)
            with tarfile.open(archive) as handle:
                handle.extractall(work / "prebuilt", filter="data")
        server = next((work / "prebuilt").rglob("llama-server"))
        library_dirs = sorted({str(path.parent) for path in (work / "prebuilt").rglob("*.so*")})
        os.environ["LD_LIBRARY_PATH"] = ":".join(library_dirs + [os.environ.get("LD_LIBRARY_PATH", "")])
        devices = subprocess.check_output([str(server), "--list-devices"], text=True, stderr=subprocess.STDOUT)
        print(devices, flush=True)
        if "CUDA" not in devices:
            raise RuntimeError("Official binary did not detect a CUDA device")
        runtime_source = "official precompiled CUDA 12.8 release; SHA256 verified"
    except Exception as exc:
        binary_error = str(exc)
        print("Precompiled runtime incompatible; compiling the same official release:", exc, flush=True)
        source = work / "llama.cpp"
        if not source.exists():
            run(["git", "clone", "--depth", "1", "--branch", TAG,
                 "https://github.com/ggml-org/llama.cpp.git", source], timeout=180)
        import torch
        major, minor = torch.cuda.get_device_capability(0)
        run(["cmake", "-S", source, "-B", source / "build", "-DGGML_CUDA=ON",
             f"-DCMAKE_CUDA_ARCHITECTURES={major}{minor}", "-DCMAKE_BUILD_TYPE=Release",
             "-DLLAMA_CURL=OFF", "-DLLAMA_BUILD_TESTS=OFF", "-DLLAMA_BUILD_EXAMPLES=OFF"], timeout=180)
        run(["cmake", "--build", source / "build", "--target", "llama-server", "-j", "2"], timeout=900)
        server = source / "build/bin/llama-server"
        source_commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
        runtime_source = "official pinned source compiled with GGML_CUDA=ON"
        print(subprocess.check_output([str(server), "--list-devices"], text=True), flush=True)

    bin_link = pack / "bin"
    if not bin_link.exists():
        bin_link.symlink_to(server.parent, target_is_directory=True)
    elif (bin_link / "llama-server").resolve() != server.resolve():
        raise RuntimeError("Existing brain_local/bin points to a different runtime; inspect it first")
    model_dir = pack / "models"
    model_dir.mkdir(exist_ok=True)
    print("Downloading the production GGUF from Qwen/Qwen3-4B-GGUF", flush=True)
    model = Path(hf_hub_download(repo_id="Qwen/Qwen3-4B-GGUF", filename=MODEL))
    model_link = model_dir / MODEL
    if not model_link.exists():
        model_link.symlink_to(model)
    if model.stat().st_size < 2_000_000_000:
        raise RuntimeError("GGUF file is unexpectedly small")
    os.environ["AGCN_LLAMA_GPU_LAYERS"] = "99"
    env = {key: os.environ[key] for key in ("AGCN_LLAMA_GPU_LAYERS", "LD_LIBRARY_PATH") if key in os.environ}
    output = ROOT / "training/baselines"
    output.mkdir(exist_ok=True)
    (output / "colab_runtime_env.json").write_text(json.dumps(env, indent=2) + "\n")
    manifest = {
        "llama_release": TAG, "llama_source_commit": source_commit,
        "runtime_source": runtime_source, "prebuilt_error": binary_error,
        "model_repository": "Qwen/Qwen3-4B-GGUF", "model_file": MODEL,
        "model_revision": model.parent.name, "model_sha256": sha256(model),
        "model_size_bytes": model.stat().st_size, "gpu_layers_requested": 99,
        "gpu": subprocess.check_output(["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
                                         "--format=csv,noheader"], text=True).strip(),
        "repository_commit": subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip(),
    }
    (output / "qwen3_4b_current_v0.1_runtime.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
