#!/usr/bin/env python3
"""Baseline rápido do Qwen3-4B atual via Transformers + GPU.

Mantém o PresenterBrain, prompt e validators atuais do AGCN, mas troca o
transporte llama.cpp/GGUF por Qwen3-4B 4-bit no Transformers. Isso deixa o
baseline muito mais rápido no Colab/T4 e usa o mesmo modelo-base do futuro LoRA.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from core.brain_orchestrator import PresenterBrain
from core.integration_contracts import BrainContext, CommentPayload


class TransformersTransport:
    def __init__(self, model_name: str = "Qwen/Qwen3-4B") -> None:
        if not torch.cuda.is_available():
            raise RuntimeError("Ative uma GPU no Colab.")

        bf16 = torch.cuda.is_bf16_supported()
        dtype = torch.bfloat16 if bf16 else torch.float16

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        quant = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=dtype,
        )
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=quant,
            device_map="auto",
            torch_dtype=dtype,
        )
        self.model.eval()
        self.model_name = model_name

    @property
    def name(self) -> str:
        return f"{self.model_name} / Transformers 4-bit"

    def healthcheck(self):
        return True, f"Qwen pronto na GPU: {torch.cuda.get_device_name(0)}"

    def close(self):
        try:
            del self.model
            torch.cuda.empty_cache()
        except Exception:
            pass

    def complete(self, *, system_instruction: str, user_payload: str) -> str:
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": user_payload},
        ]
        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            out = self.model.generate(
                **inputs,
                max_new_tokens=220,
                do_sample=False,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        new_ids = out[0][inputs["input_ids"].shape[-1]:]
        return self.tokenizer.decode(new_ids, skip_special_tokens=True).strip()


def _comment(value):
    if not isinstance(value, dict):
        return None
    return CommentPayload(
        id=str(value.get("id") or ""),
        username=str(value.get("username") or ""),
        text=str(value.get("text") or ""),
    )


def _context(inp: dict) -> BrainContext:
    return BrainContext(
        mode=str(inp.get("mode") or "proactive"),
        product=dict(inp.get("product") or {}),
        live_conditions=dict(inp.get("live_conditions") or {}),
        comment=_comment(inp.get("comment")),
        decision=dict(inp.get("decision") or {}),
        recent_comments=[
            x for x in (_comment(v) for v in inp.get("recent_comments") or [])
            if x is not None
        ],
        recent_speeches=[str(x) for x in inp.get("recent_speeches") or []],
        recent_facts=[str(x) for x in inp.get("recent_facts") or []],
        sales_thread=str(inp.get("sales_thread") or ""),
        planner_topic=str(inp.get("planner_topic") or ""),
        allowed_facts=[str(x) for x in inp.get("allowed_facts") or []],
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--model", default="Qwen/Qwen3-4B")
    args = ap.parse_args()

    examples = [
        json.loads(x)
        for x in Path(args.eval).read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]

    transport = TransformersTransport(args.model)
    brain = PresenterBrain(transport, max_retries=1)
    print(brain.healthcheck()[1], flush=True)

    rows = []
    latencies = []
    try:
        for i, ex in enumerate(examples, 1):
            started = time.perf_counter()
            error = ""
            result_payload = None
            speech = ""
            try:
                result = brain.generate(_context(ex["input"]))
                speech = result.speech
                result_payload = {
                    "speech": result.speech,
                    "topic": result.topic,
                    "used_facts": result.used_facts,
                    "needs_fact": result.needs_fact,
                    "next_sales_thread": result.next_sales_thread,
                }
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"

            elapsed = round(time.perf_counter() - started, 3)
            latencies.append(elapsed)
            rows.append({
                "id": ex.get("id"),
                "target": ex.get("target"),
                "tags": (ex.get("metadata") or {}).get("tags", []),
                "baseline": result_payload,
                "error": error,
                "latency_seconds": elapsed,
            })
            print(
                f"[{i:02d}/{len(examples):02d}] {ex.get('id')} "
                f"{elapsed:.2f}s {'ERRO -> '+error if error else speech[:120]}",
                flush=True,
            )
    finally:
        brain.close()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "model": args.model,
        "transport": "Transformers 4-bit / GPU",
        "purpose": "baseline antes do fine-tuning AGCN Presenter",
        "total": len(rows),
        "completed": sum(1 for r in rows if not r["error"]),
        "failed": sum(1 for r in rows if r["error"]),
        "latency_seconds": {
            "mean": round(statistics.mean(latencies), 3) if latencies else None,
            "median": round(statistics.median(latencies), 3) if latencies else None,
            "min": round(min(latencies), 3) if latencies else None,
            "max": round(max(latencies), 3) if latencies else None,
        },
        "note": (
            "Este baseline usa o mesmo Qwen3-4B base do futuro LoRA, "
            "em 4-bit no Transformers, mantendo PresenterBrain/prompt/validators atuais."
        ),
    }
    Path(args.summary).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
