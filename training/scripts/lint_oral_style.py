#!/usr/bin/env python3
"""Lint simples de oralidade PT-BR para target.speech.

Não corrige automaticamente; só aponta frases que parecem formais demais.
Uso:
  python training/scripts/lint_oral_style.py arquivo1.jsonl [arquivo2.jsonl ...]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FORMAL_PATTERNS = {
    r"\bestá\b": "prefira 'tá' na fala",
    r"\bestou\b": "prefira 'tô' na fala",
    r"\bpara você\b": "prefira 'pra você' na fala",
    r"\bpara eu\b": "considere 'pra eu' na fala",
    r"\bnão deixe para depois\b": "prefira 'não deixa pra depois'",
    r"\bencontra-se\b": "reescreva em linguagem falada",
    r"\brealize a (?:compra|finalização)\b": "prefira CTA oral e direto",
    r"\binformo que\b": "evite linguagem de atendimento formal",
}


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: lint_oral_style.py <dataset.jsonl> [...]")
        return 2

    warnings = 0
    checked = 0

    for arg in sys.argv[1:]:
        path = Path(arg)
        with path.open("r", encoding="utf-8") as handle:
            for line_no, raw in enumerate(handle, 1):
                raw = raw.strip()
                if not raw:
                    continue
                ex = json.loads(raw)
                speech = str((ex.get("target") or {}).get("speech") or "")
                if speech == "IGNORAR":
                    continue
                checked += 1
                for pattern, message in FORMAL_PATTERNS.items():
                    if re.search(pattern, speech, flags=re.IGNORECASE):
                        warnings += 1
                        print(f"{path}:{line_no} {ex.get('id')}: {message}")
                        print(f"  {speech}")

    if warnings:
        print(f"AVISO: {warnings} ponto(s) de oralidade em {checked} fala(s)")
        return 1

    print(f"OK: {checked} fala(s) sem marcadores formais principais")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
