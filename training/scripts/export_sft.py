#!/usr/bin/env python3
"""Exporta exemplos AGCN Presenter para JSONL de chat SFT.

Uso:
  python training/scripts/export_sft.py \
    training/datasets/real_live_gold_v0.2.jsonl \
    training/outputs/sft_real_live_v0.2.jsonl

O payload imita o runtime para reduzir train-serving skew.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.presenter_policy import build_system_instruction  # noqa: E402


def build_user_payload(inp: dict) -> str:
    payload = {
        "MODE": inp.get("mode"),
        "PRODUCT": inp.get("product") or {},
        "LIVE_CONDITIONS": inp.get("live_conditions") or {},
        "COMMERCIAL_RULES": inp.get("commercial_rules") or {},
        "COMMENT": inp.get("comment"),
        "DECISION": inp.get("decision") or {},
        "RECENT_COMMENTS": inp.get("recent_comments") or [],
        "RECENT_SPEECHES": (inp.get("recent_speeches") or [])[-8:],
        "RECENT_FACTS": (inp.get("recent_facts") or [])[-12:],
        "SALES_THREAD": inp.get("sales_thread") or "",
        "PLANNER_TOPIC": inp.get("planner_topic") or "",
        "ALLOWED_FACTS": inp.get("allowed_facts") or [],
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def target_json(target: dict) -> str:
    out = {
        "speech": target["speech"],
        "topic": target.get("topic") or "",
        "used_facts": target.get("used_facts") or [],
        "needs_fact": bool(target.get("needs_fact", False)),
        "next_sales_thread": target.get("next_sales_thread") or "",
    }
    return json.dumps(out, ensure_ascii=False, separators=(",", ":"))


def main() -> int:
    if len(sys.argv) != 3:
        print("Uso: export_sft.py <entrada.jsonl> <saida.jsonl>")
        return 2

    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    dst.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with src.open("r", encoding="utf-8") as fin, dst.open("w", encoding="utf-8") as fout:
        for raw in fin:
            raw = raw.strip()
            if not raw:
                continue
            ex = json.loads(raw)
            if ex.get("metadata", {}).get("quality") != "gold":
                continue

            record = {
                "messages": [
                    {"role": "system", "content": build_system_instruction()},
                    {"role": "user", "content": build_user_payload(ex["input"])},
                    {"role": "assistant", "content": target_json(ex["target"])},
                ],
                "metadata": {
                    "id": ex.get("id"),
                    "source_document": ex.get("metadata", {}).get("source_document", ""),
                    "source_timestamp": ex.get("metadata", {}).get("source_timestamp", ""),
                    "tags": ex.get("metadata", {}).get("tags", []),
                },
            }
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1

    print(f"OK: {count} exemplo(s) exportados para {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
