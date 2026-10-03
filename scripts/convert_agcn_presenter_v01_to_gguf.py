#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path

import numpy as np
from safetensors import safe_open

GGUF_MAGIC = 0x46554747
GGUF_VERSION = 3
ALIGNMENT = 32
TYPE_F16 = 1
V_STRING = 8
V_FLOAT32 = 6
V_UINT32 = 4

EXPECTED_ADAPTER_SHA256 = "5652197ef5f1bc212822d071ed28cd5a9802fea62aa3f5f802e88896486a6524"
EXPECTED_OUTPUT_SHA256 = "19298caf2b03b90fbbc215786df16e5ea83fa005dc9a595125cac20376585ee5"
EXPECTED_LAYERS = 36
EXPECTED_MODULES = {
    "self_attn.q_proj": "attn_q",
    "self_attn.k_proj": "attn_k",
    "self_attn.v_proj": "attn_v",
    "self_attn.o_proj": "attn_output",
    "mlp.gate_proj": "ffn_gate",
    "mlp.up_proj": "ffn_up",
    "mlp.down_proj": "ffn_down",
}
MODULE_ORDER = [
    "attn_q", "attn_k", "attn_v", "attn_output",
    "ffn_gate", "ffn_up", "ffn_down",
]


def sha256_file(path: Path, chunk=8 * 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                return h.hexdigest()
            h.update(b)


def pad(n: int, align: int = ALIGNMENT) -> int:
    return (n + align - 1) // align * align


def pstr(value: str) -> bytes:
    b = value.encode("utf-8")
    return struct.pack("<Q", len(b)) + b


def pkv_string(key: str, value: str) -> bytes:
    return pstr(key) + struct.pack("<I", V_STRING) + pstr(value)


def pkv_f32(key: str, value: float) -> bytes:
    return pstr(key) + struct.pack("<I", V_FLOAT32) + struct.pack("<f", value)


def pkv_u32(key: str, value: int) -> bytes:
    return pstr(key) + struct.pack("<I", V_UINT32) + struct.pack("<I", value)


def gguf_tensor_name(hf_key: str) -> str:
    m = re.fullmatch(
        r"base_model\.model\.model\.layers\.(\d+)\."
        r"(self_attn\.(?:q_proj|k_proj|v_proj|o_proj)|mlp\.(?:gate_proj|up_proj|down_proj))\."
        r"lora_([AB])\.weight",
        hf_key,
    )
    if not m:
        raise ValueError(f"Tensor inesperado no adapter: {hf_key}")
    layer = int(m.group(1))
    module = m.group(2)
    side = m.group(3).lower()
    return f"blk.{layer}.{EXPECTED_MODULES[module]}.weight.lora_{side}"


def collect_tensors(adapter_path: Path):
    tensors = []
    coverage = {
        (layer, module): set()
        for layer in range(EXPECTED_LAYERS)
        for module in EXPECTED_MODULES
    }
    with safe_open(str(adapter_path), framework="numpy") as f:
        keys = list(f.keys())
        if len(keys) != EXPECTED_LAYERS * len(EXPECTED_MODULES) * 2:
            raise ValueError(f"Esperados 504 tensors; encontrados {len(keys)}")
        for key in keys:
            name = gguf_tensor_name(key)
            mm = re.search(r"layers\.(\d+)\.(.+?)\.lora_([AB])\.weight$", key)
            assert mm
            layer = int(mm.group(1))
            module = mm.group(2)
            side = mm.group(3)
            coverage[(layer, module)].add(side)
            arr = f.get_tensor(key)
            if arr.ndim != 2:
                raise ValueError(f"Tensor {key} deveria ser 2D, recebeu {arr.shape}")
            arr16 = np.ascontiguousarray(arr, dtype=np.float16)
            tensors.append((name, tuple(arr16.shape), arr16))

    missing = [k for k, sides in coverage.items() if sides != {"A", "B"}]
    if missing:
        raise ValueError(f"Pares LoRA incompletos: {missing[:10]}")

    def sort_key(item):
        name = item[0]
        parts = name.split(".")
        layer = int(parts[1])
        module = parts[2]
        side = 0 if name.endswith(".lora_a") else 1
        return (layer, MODULE_ORDER.index(module), side)

    tensors.sort(key=sort_key)
    return tensors


def validate_pair_shapes(tensors):
    by_base = {}
    for name, shape, _ in tensors:
        base, side = name.rsplit(".lora_", 1)
        by_base.setdefault(base, {})[side] = shape
    if len(by_base) != EXPECTED_LAYERS * len(EXPECTED_MODULES):
        raise ValueError(f"Esperados 252 pares; encontrados {len(by_base)}")
    for base, pair in by_base.items():
        if set(pair) != {"a", "b"}:
            raise ValueError(f"Par incompleto: {base}")
        a = pair["a"]
        b = pair["b"]
        if len(a) != 2 or len(b) != 2 or a[0] != b[1] or a[0] != 16:
            raise ValueError(f"Shape LoRA inválido em {base}: A={a}, B={b}")


def write_gguf(adapter_path: Path, out_path: Path):
    tensors = collect_tensors(adapter_path)
    validate_pair_shapes(tensors)

    kv = [
        pkv_string("general.architecture", "qwen3"),
        pkv_string("general.type", "adapter"),
        pkv_string("general.name", "AGCN Presenter v0.1"),
        pkv_string("general.version", "v0.1"),
        pkv_string("general.description", "AGCN Presenter v0.1 LoRA adapter for Qwen3-4B"),
        pkv_u32("general.quantization_version", 2),
        pkv_u32("general.alignment", 32),
        pkv_string("adapter.type", "lora"),
        pkv_f32("adapter.lora.alpha", 32.0),
    ]

    tensor_infos = bytearray()
    offset = 0
    for name, shape, arr in tensors:
        tensor_infos += pstr(name)
        tensor_infos += struct.pack("<I", len(shape))
        for dim in reversed(shape):
            tensor_infos += struct.pack("<Q", int(dim))
        tensor_infos += struct.pack("<I", TYPE_F16)
        tensor_infos += struct.pack("<Q", offset)
        offset += pad(arr.nbytes)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as out:
        out.write(struct.pack("<I", GGUF_MAGIC))
        out.write(struct.pack("<I", GGUF_VERSION))
        out.write(struct.pack("<Q", len(tensors)))
        out.write(struct.pack("<Q", len(kv)))
        for entry in kv:
            out.write(entry)
        out.write(tensor_infos)
        pos = out.tell()
        out.write(b"\0" * (pad(pos) - pos))
        for _, _, arr in tensors:
            arr.tofile(out)
            out.write(b"\0" * (pad(arr.nbytes) - arr.nbytes))
    return tensors


def read_string(f):
    (n,) = struct.unpack("<Q", f.read(8))
    return f.read(n).decode("utf-8")


def verify_gguf(path: Path):
    size = path.stat().st_size
    with path.open("rb") as f:
        magic, version = struct.unpack("<II", f.read(8))
        n_tensors, n_kv = struct.unpack("<QQ", f.read(16))
        if magic != GGUF_MAGIC or version != GGUF_VERSION:
            raise ValueError("Cabeçalho GGUF inválido")
        meta = {}
        for _ in range(n_kv):
            key = read_string(f)
            (vtype,) = struct.unpack("<I", f.read(4))
            if vtype == V_STRING:
                meta[key] = read_string(f)
            elif vtype == V_FLOAT32:
                meta[key] = struct.unpack("<f", f.read(4))[0]
            elif vtype == V_UINT32:
                meta[key] = struct.unpack("<I", f.read(4))[0]
            else:
                raise ValueError(f"Tipo de metadata inesperado: {vtype}")
        infos = []
        for _ in range(n_tensors):
            name = read_string(f)
            (ndim,) = struct.unpack("<I", f.read(4))
            dims = tuple(struct.unpack("<Q", f.read(8))[0] for _ in range(ndim))
            typ = struct.unpack("<I", f.read(4))[0]
            offs = struct.unpack("<Q", f.read(8))[0]
            infos.append((name, dims, typ, offs))
        data_offset = pad(f.tell())

    if n_tensors != 504:
        raise ValueError(f"GGUF deveria ter 504 tensors, tem {n_tensors}")
    for key, value in {
        "general.architecture": "qwen3",
        "general.type": "adapter",
        "adapter.type": "lora",
    }.items():
        if meta.get(key) != value:
            raise ValueError(f"Metadata inválida {key}: {meta.get(key)!r}")
    if abs(float(meta.get("adapter.lora.alpha", 0)) - 32.0) > 1e-6:
        raise ValueError("adapter.lora.alpha inválido")
    if any(t != TYPE_F16 for _, _, t, _ in infos):
        raise ValueError("Há tensor que não é F16")
    if len({n for n, *_ in infos}) != n_tensors:
        raise ValueError("Nomes de tensor duplicados")
    if infos[0][3] != 0:
        raise ValueError("Primeiro tensor não começa no offset 0")
    last_name, last_dims, _, last_off = infos[-1]
    last_bytes = 2
    for d in last_dims:
        last_bytes *= d
    if data_offset + last_off + last_bytes > size:
        raise ValueError("Último tensor excede o tamanho do arquivo")
    return {
        "size_bytes": size,
        "tensor_count": n_tensors,
        "kv_count": n_kv,
        "data_offset": data_offset,
        "metadata": meta,
        "first_tensor": infos[0][0],
        "last_tensor": last_name,
        "sha256": sha256_file(path),
    }


def main():
    ap = argparse.ArgumentParser(
        description="Converte o adapter PEFT do AGCN Presenter v0.1 para LoRA GGUF F16"
    )
    ap.add_argument("adapter", type=Path, help="adapter_model.safetensors")
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("AGCN-Presenter-v0.1-F16.gguf"),
    )
    ap.add_argument(
        "--allow-unverified-input",
        action="store_true",
        help="permite converter um arquivo cujo SHA256 não seja o adapter v0.1 oficial",
    )
    args = ap.parse_args()

    adapter = args.adapter.resolve()
    if not adapter.is_file():
        raise SystemExit(f"Adapter não encontrado: {adapter}")
    source_hash = sha256_file(adapter)
    if source_hash != EXPECTED_ADAPTER_SHA256 and not args.allow_unverified_input:
        raise SystemExit(
            f"SHA256 do adapter não confere. Esperado {EXPECTED_ADAPTER_SHA256}; "
            f"recebido {source_hash}"
        )

    tensors = write_gguf(adapter, args.output.resolve())
    report = verify_gguf(args.output.resolve())
    report["source_adapter_sha256"] = source_hash
    report["pairs"] = len(tensors) // 2
    if source_hash == EXPECTED_ADAPTER_SHA256 and report["sha256"] != EXPECTED_OUTPUT_SHA256:
        raise SystemExit(
            f"GGUF reproduzido não confere. Esperado {EXPECTED_OUTPUT_SHA256}; "
            f"recebido {report['sha256']}"
        )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
