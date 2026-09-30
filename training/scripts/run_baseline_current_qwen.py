#!/usr/bin/env python3
"""Executa o baseline congelado com o Qwen3-4B atual do AGCN.

Este script mede o comportamento do Presenter *antes* do fine-tuning.
Ele usa exatamente PresenterBrain + validators + prompt atual da branch,
mas ignora campos novos de laboratório que o runtime atual ainda não conhece
(ex.: COMMERCIAL_RULES). Isso é intencional: queremos uma fotografia do "antes".

Uso:
  python training/scripts/run_baseline_current_qwen.py \
    training/evaluation/frozen_eval_v0.1.jsonl \
    training/baselines/qwen3_4b_current_v0.1.jsonl \
    training/baselines/qwen3_4b_current_v0.1_summary.json
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.brain_orchestrator import PresenterBrain  # noqa: E402
from core.integration_contracts import BrainContext, CommentPayload  # noqa: E402
from core.local_llama_brain import LlamaCppLocalTransport  # noqa: E402


def _comment(value):
    if not isinstance(value, dict):
        return None
    return CommentPayload(
        id=str(value.get("id") or ""),
        username=str(value.get("username") or ""),
        text=str(value.get("text") or ""),
    )


def _recent_comments(values):
    out = []
    for value in values or []:
        item = _comment(value)
        if item is not None:
            out.append(item)
    return out


def _context(inp: dict) -> BrainContext:
    # Importante: commercial_rules NÃO entra aqui porque o BrainContext atual
    # ainda não possui esse campo. O baseline deve medir exatamente essa versão.
    return BrainContext(
        mode=str(inp.get("mode") or "proactive"),
        product=dict(inp.get("product") or {}),
        live_conditions=dict(inp.get("live_conditions") or {}),
        comment=_comment(inp.get("comment")),
        decision=dict(inp.get("decision") or {}),
        recent_comments=_recent_comments(inp.get("recent_comments")),
        recent_speeches=[str(x) for x in (inp.get("recent_speeches") or [])],
        recent_facts=[str(x) for x in (inp.get("recent_facts") or [])],
        sales_thread=str(inp.get("sales_thread") or ""),
        planner_topic=str(inp.get("planner_topic") or ""),
        allowed_facts=[str(x) for x in (inp.get("allowed_facts") or [])],
    )


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    folded = str(text or "").casefold()
    return any(term.casefold() in folded for term in terms)


def _auto_flags(example: dict, speech: str, failed: bool) -> dict:
    tags = set((example.get("metadata") or {}).get("tags") or [])
    target = example.get("target") or {}
    speech_fold = str(speech or "").casefold()

    flags = {
        "expected_ignore": target.get("speech") == "IGNORAR",
        "returned_ignore": str(speech or "").strip() == "IGNORAR",
        "formal_marker": _contains_any(
            speech,
            (
                "está ",
                "estou ",
                "para você",
                "não deixe para depois",
                "realize a compra",
                "informo que",
            ),
        ),
        "scarcity_expected": "scarcity" in tags,
        "scarcity_present": _contains_any(
            speech,
            (
                "últimas unidades",
                "ultimas unidades",
                "poucas unidades",
                "não vai ter pra todo mundo",
                "nao vai ter pra todo mundo",
                "pra não ficar sem",
                "pra nao ficar sem",
                "enquanto tem",
                "restam ",
                "só restam ",
                "so restam ",
            ),
        ),
        "buying_intent": "buying_intent" in tags,
        "purchase_guidance_present": _contains_any(
            speech,
            (
                "produto fixado",
                "carrinho",
                "sacolinha",
                "finaliza",
                "comprar",
                "compra",
            ),
        ),
        "quantity_scarcity": "quantity_scarcity" in tags,
        "model_failed": bool(failed),
    }

    stock = ((example.get("input") or {}).get("commercial_rules") or {}).get(
        "stock_quantity"
    )
    if stock is not None:
        flags["expected_stock_quantity"] = int(stock)
        flags["stock_quantity_spoken"] = str(int(stock)) in speech_fold
    else:
        flags["expected_stock_quantity"] = None
        flags["stock_quantity_spoken"] = None

    return flags


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "Uso: run_baseline_current_qwen.py "
            "<eval.jsonl> <saida.jsonl> <summary.json>"
        )
        return 2

    src = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    summary_path = Path(sys.argv[3])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    pack_dir = Path(
        os.getenv("AGCN_BASELINE_BRAIN_PACK", str(ROOT / "brain_local"))
    ).resolve()

    transport = LlamaCppLocalTransport(
        pack_dir=pack_dir,
        startup_timeout_seconds=240,
        timeout_seconds=120,
        temperature=0.25,
        max_output_tokens=350,
        context_size=4096,
    )
    brain = PresenterBrain(transport, max_retries=1)

    ok, detail = brain.healthcheck()
    if not ok:
        print(detail)
        return 1
    print(detail)

    examples = []
    with src.open("r", encoding="utf-8") as handle:
        for raw in handle:
            raw = raw.strip()
            if raw:
                examples.append(json.loads(raw))

    results = []
    latencies = []
    failed = 0

    try:
        for index, example in enumerate(examples, 1):
            started = time.perf_counter()
            error = ""
            result_payload = None
            speech = ""
            try:
                result = brain.generate(_context(example["input"]))
                speech = result.speech
                result_payload = {
                    "speech": result.speech,
                    "topic": result.topic,
                    "used_facts": result.used_facts,
                    "needs_fact": result.needs_fact,
                    "next_sales_thread": result.next_sales_thread,
                }
            except Exception as exc:  # baseline deve registrar falha, não abortar
                failed += 1
                error = f"{type(exc).__name__}: {exc}"

            elapsed = round(time.perf_counter() - started, 3)
            latencies.append(elapsed)
            record = {
                "id": example.get("id"),
                "target": example.get("target"),
                "tags": (example.get("metadata") or {}).get("tags", []),
                "baseline": result_payload,
                "error": error,
                "latency_seconds": elapsed,
                "auto_flags": _auto_flags(example, speech, bool(error)),
            }
            results.append(record)
            print(
                f"[{index:02d}/{len(examples):02d}] "
                f"{example.get('id')} {elapsed:.2f}s "
                f"{'ERRO' if error else speech[:100]}"
            )
    finally:
        brain.close()

    with out_path.open("w", encoding="utf-8") as handle:
        for record in results:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    valid = [x for x in results if not x["error"]]
    scarcity_rows = [
        x for x in valid if x["auto_flags"].get("scarcity_expected")
    ]
    buying_rows = [
        x for x in valid if x["auto_flags"].get("buying_intent")
    ]
    quantity_rows = [
        x for x in valid if x["auto_flags"].get("quantity_scarcity")
    ]
    ignore_rows = [
        x for x in results if x["auto_flags"].get("expected_ignore")
    ]

    summary = {
        "model": "Qwen3-4B-Q4_K_M.gguf",
        "engine": "llama.cpp / AGCN LlamaCppLocalTransport",
        "purpose": "baseline antes do fine-tuning AGCN Presenter",
        "total": len(results),
        "completed": len(valid),
        "failed": failed,
        "latency_seconds": {
            "mean": round(statistics.mean(latencies), 3) if latencies else None,
            "median": round(statistics.median(latencies), 3) if latencies else None,
            "min": round(min(latencies), 3) if latencies else None,
            "max": round(max(latencies), 3) if latencies else None,
        },
        "automatic_checks": {
            "formal_markers": sum(
                1 for x in valid if x["auto_flags"].get("formal_marker")
            ),
            "scarcity_expected": len(scarcity_rows),
            "scarcity_present": sum(
                1 for x in scarcity_rows
                if x["auto_flags"].get("scarcity_present")
            ),
            "buying_intent_cases": len(buying_rows),
            "purchase_guidance_present": sum(
                1 for x in buying_rows
                if x["auto_flags"].get("purchase_guidance_present")
            ),
            "quantity_scarcity_cases": len(quantity_rows),
            "correct_quantity_spoken": sum(
                1 for x in quantity_rows
                if x["auto_flags"].get("stock_quantity_spoken")
            ),
            "expected_ignore_cases": len(ignore_rows),
            "ignore_or_rejected": sum(
                1 for x in ignore_rows
                if x["error"]
                or x["auto_flags"].get("returned_ignore")
                or (
                    x.get("baseline")
                    and x["baseline"].get("needs_fact")
                )
            ),
        },
        "note": (
            "As checagens automáticas são apenas indicadores. "
            "A avaliação final é lado a lado, humana, depois do LoRA."
        ),
    }

    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
