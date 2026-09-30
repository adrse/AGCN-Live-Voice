#!/usr/bin/env python3
"""Validador leve do dataset AGCN Presenter.

Uso:
    python training/scripts/validate_dataset.py training/datasets/gold_seed_v0.1.jsonl

Não usa dependências externas.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED_TOP = {"id", "version", "input", "target", "metadata"}
REQUIRED_INPUT = {
    "mode", "product", "live_conditions", "recent_comments",
    "recent_speeches", "recent_facts", "sales_thread",
    "planner_topic", "allowed_facts",
}
REQUIRED_TARGET = {
    "speech", "topic", "used_facts", "needs_fact", "next_sales_thread",
}


def validate(example: dict, line_no: int) -> list[str]:
    errors: list[str] = []
    prefix = f"linha {line_no}"

    missing = REQUIRED_TOP - set(example)
    if missing:
        errors.append(f"{prefix}: campos de topo ausentes: {sorted(missing)}")
        return errors

    if example.get("version") != "1.0":
        errors.append(f"{prefix}: version deve ser 1.0")

    inp = example.get("input")
    target = example.get("target")
    metadata = example.get("metadata")

    if not isinstance(inp, dict):
        errors.append(f"{prefix}: input deve ser objeto")
        return errors
    if not isinstance(target, dict):
        errors.append(f"{prefix}: target deve ser objeto")
        return errors
    if not isinstance(metadata, dict):
        errors.append(f"{prefix}: metadata deve ser objeto")
        return errors

    miss_in = REQUIRED_INPUT - set(inp)
    miss_tg = REQUIRED_TARGET - set(target)
    if miss_in:
        errors.append(f"{prefix}: input ausente: {sorted(miss_in)}")
    if miss_tg:
        errors.append(f"{prefix}: target ausente: {sorted(miss_tg)}")

    mode = inp.get("mode")
    if mode not in {"proactive", "comment_reply"}:
        errors.append(f"{prefix}: mode inválido: {mode!r}")

    if mode == "comment_reply" and not isinstance(inp.get("comment"), dict):
        errors.append(f"{prefix}: comment_reply exige comment objeto")

    if mode == "proactive" and inp.get("comment") not in (None, {}):
        errors.append(f"{prefix}: proactive deve usar comment=null")

    allowed = inp.get("allowed_facts")
    used = target.get("used_facts")
    if not isinstance(allowed, list):
        errors.append(f"{prefix}: allowed_facts deve ser lista")
        allowed = []
    if not isinstance(used, list):
        errors.append(f"{prefix}: used_facts deve ser lista")
        used = []

    allowed_set = {str(x).strip().casefold() for x in allowed}
    for fact in used:
        if str(fact).strip().casefold() not in allowed_set:
            errors.append(
                f"{prefix}: used_fact não autorizado: {fact!r}"
            )

    speech = str(target.get("speech") or "").strip()
    needs_fact = bool(target.get("needs_fact"))

    if not speech:
        errors.append(f"{prefix}: speech vazio")

    if needs_fact:
        if speech != "IGNORAR":
            errors.append(
                f'{prefix}: needs_fact=true exige speech="IGNORAR"'
            )
        if used:
            errors.append(
                f"{prefix}: needs_fact=true não deve usar used_facts"
            )
    elif speech == "IGNORAR":
        errors.append(
            f'{prefix}: speech="IGNORAR" exige needs_fact=true'
        )

    split = metadata.get("split")
    if split not in {"train", "validation", "test"}:
        errors.append(f"{prefix}: split inválido: {split!r}")

    quality = metadata.get("quality")
    if quality not in {"gold", "silver", "rejected"}:
        errors.append(f"{prefix}: quality inválido: {quality!r}")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: validate_dataset.py <arquivo.jsonl>")
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Arquivo não encontrado: {path}")
        return 2

    total = 0
    all_errors: list[str] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, 1):
            raw = raw.strip()
            if not raw:
                continue
            total += 1
            try:
                example = json.loads(raw)
            except json.JSONDecodeError as exc:
                all_errors.append(f"linha {line_no}: JSON inválido: {exc}")
                continue
            if not isinstance(example, dict):
                all_errors.append(f"linha {line_no}: exemplo deve ser objeto")
                continue
            all_errors.extend(validate(example, line_no))

    if all_errors:
        print(f"FALHOU: {len(all_errors)} erro(s) em {total} exemplo(s)")
        for error in all_errors:
            print(f"- {error}")
        return 1

    print(f"OK: {total} exemplo(s) válidos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
