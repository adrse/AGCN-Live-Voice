#!/usr/bin/env python3
"""Monta os arquivos SFT train/validation do AGCN Presenter v0.2.

Combina os datasets Gold curados, preserva o split e exclui qualquer teste
congelado. A saída fica em training/outputs/ (gitignored).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from training.training_policy import build_training_system_instruction


DEFAULT_INPUTS = [
    ROOT / "training/datasets/real_live_gold_v0.2.jsonl",
    ROOT / "training/datasets/gold_expansion_v0.3.jsonl",
    ROOT / "training/datasets/gold_synthetic_v0.2.jsonl",
]


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


def convert(example: dict) -> dict:
    meta = example.get("metadata") or {}
    return {
        "messages": [
            {
                "role": "system",
                "content": build_training_system_instruction(),
            },
            {
                "role": "user",
                "content": build_user_payload(example["input"]),
            },
            {
                "role": "assistant",
                "content": target_json(example["target"]),
            },
        ],
        "metadata": {
            "id": example.get("id"),
            "split": meta.get("split"),
            "tags": meta.get("tags", []),
            "source_document": meta.get("source_document", ""),
            "source_timestamp": meta.get("source_timestamp", ""),
        },
    }


def main() -> int:
    out_dir = (
        Path(sys.argv[1]).resolve()
        if len(sys.argv) > 1
        else ROOT / "training/outputs"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    buckets = {"train": [], "validation": []}
    seen: set[str] = set()
    frozen = [json.loads(line) for line in (ROOT / "training/evaluation/frozen_eval_v0.1.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    frozen_ids = {example["id"] for example in frozen}
    fingerprint = lambda inp: json.dumps(inp, sort_keys=True, ensure_ascii=False)
    frozen_inputs = {fingerprint(example["input"]) for example in frozen}

    for path in DEFAULT_INPUTS:
        with path.open("r", encoding="utf-8") as handle:
            for raw in handle:
                raw = raw.strip()
                if not raw:
                    continue
                example = json.loads(raw)
                meta = example.get("metadata") or {}
                if meta.get("quality") != "gold":
                    continue
                split = meta.get("split")
                if split not in buckets:
                    continue
                ex_id = str(example.get("id") or "")
                if ex_id in frozen_ids or fingerprint(example["input"]) in frozen_inputs:
                    raise RuntimeError(f"Frozen evaluation case cannot enter SFT: {ex_id}")
                if not ex_id or ex_id in seen:
                    raise RuntimeError(f"ID duplicado ou vazio: {ex_id!r}")
                seen.add(ex_id)
                buckets[split].append(convert(example))

    for split, rows in buckets.items():
        path = out_dir / f"agcn_presenter_v0.2_{split}.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"{split}: {len(rows)} -> {path}")

    print(f"TOTAL TREINÁVEL: {sum(len(x) for x in buckets.values())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
