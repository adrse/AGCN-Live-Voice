#!/usr/bin/env python3
"""Compara baseline atual e AGCN Presenter v0.1 lado a lado."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load(path: str):
    rows = {}
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        if raw.strip():
            row = json.loads(raw)
            if row["id"] in rows:
                raise ValueError(f"Duplicate case ID in {path}: {row['id']}")
            rows[row["id"]] = row
    return rows


def main() -> int:
    if len(sys.argv) != 4:
        print("Uso: compare_models.py baseline.jsonl lora.jsonl saida.md")
        return 2

    baseline = load(sys.argv[1])
    lora = load(sys.argv[2])
    if set(baseline) != set(lora):
        raise ValueError("Baseline and LoRA must contain exactly the same case IDs")
    ids = sorted(baseline)

    lines = [
        "# Comparação — Qwen atual vs AGCN Presenter v0.1",
        "",
        f"Casos comparáveis: **{len(ids)}**",
        "",
        "A comparação automática é só apoio. A decisão final vem da revisão humana cega.",
        "O baseline oficial usa GGUF Q4_K_M + prompt/validators de produção. O adapter usa Transformers NF4 + política de treinamento, sem os mesmos validators. Diferenças de latência e comportamento também incluem essas mudanças; não são atribuíveis apenas ao treino.",
        "",
    ]

    for ex_id in ids:
        b = baseline[ex_id]
        a = lora[ex_id]
        b_speech = (
            ((b.get("baseline") or {}).get("speech") or b.get("error") or "")
            .replace("|", "\\|")
        )
        a_speech = (
            ((a.get("model_output") or {}).get("speech") or a.get("error") or "")
            .replace("|", "\\|")
        )
        target = ((a.get("target") or {}).get("speech") or "").replace("|", "\\|")
        checks = json.dumps(a.get("checks") or {}, ensure_ascii=False)

        lines += [
            f"## {ex_id}",
            "",
            f"**Alvo de referência:** {target}",
            "",
            f"**Qwen atual:** {b_speech}",
            "",
            f"**AGCN v0.1:** {a_speech}",
            "",
            f"**Latência:** Qwen atual {b.get('latency_seconds')}s; AGCN v0.1 {a.get('latency_seconds')}s.",
            "",
            f"**Checks AGCN:** {checks}",
            "",
        ]

    Path(sys.argv[3]).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK: {len(ids)} casos -> {sys.argv[3]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
