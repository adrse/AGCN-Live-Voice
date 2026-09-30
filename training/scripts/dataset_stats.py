#!/usr/bin/env python3
"""Mostra cobertura dos datasets AGCN Presenter."""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("Uso: dataset_stats.py <dataset1.jsonl> [dataset2.jsonl ...]")
        return 2

    counters = {
        "mode": collections.Counter(),
        "split": collections.Counter(),
        "product": collections.Counter(),
        "voice": collections.Counter(),
        "tag": collections.Counter(),
        "source": collections.Counter(),
    }
    total = 0
    scarcity = 0
    quantity_scarcity = 0

    for arg in sys.argv[1:]:
        path = Path(arg)
        with path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                raw = raw.strip()
                if not raw:
                    continue
                ex = json.loads(raw)
                total += 1
                inp = ex.get("input") or {}
                meta = ex.get("metadata") or {}
                product = inp.get("product") or {}
                rules = inp.get("commercial_rules") or {}

                counters["mode"][str(inp.get("mode"))] += 1
                counters["split"][str(meta.get("split"))] += 1
                counters["product"][str(product.get("name") or "sem_nome")] += 1
                counters["voice"][str(meta.get("voice_style") or "sem_tag")] += 1
                counters["source"][str(meta.get("source_document") or "sem_fonte")] += 1
                for tag in meta.get("tags") or []:
                    counters["tag"][str(tag)] += 1

                tags = set(meta.get("tags") or [])
                if "scarcity" in tags:
                    scarcity += 1
                if rules.get("stock_quantity") is not None:
                    quantity_scarcity += 1

    print(f"TOTAL: {total}")
    print(f"SCARCITY: {scarcity}")
    print(f"COM QUANTIDADE: {quantity_scarcity}")
    for name, counter in counters.items():
        print(f"\n{name.upper()}")
        for key, value in counter.most_common():
            print(f"{value:4d}  {key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
