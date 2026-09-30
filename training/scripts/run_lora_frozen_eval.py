#!/usr/bin/env python3
"""Roda o adapter AGCN Presenter v0.1 nas 25 situações congeladas."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from training.evaluation_rules import evaluate_output
from training.training_policy import build_training_system_instruction


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--eval", required=True)
    p.add_argument("--adapter", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--model", default="Qwen/Qwen3-4B")
    p.add_argument("--max-new-tokens", type=int, default=350)
    return p.parse_args()


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


def parse_json(text: str) -> dict:
    value = str(text or "").strip()
    fence = chr(96) * 3
    if value.startswith(fence):
        lines = value.splitlines()[1:]
        if lines and lines[-1].strip() == fence:
            lines = lines[:-1]
        value = "\n".join(lines).strip()
        if value.lower().startswith("json"):
            value = value[4:].strip()
    return json.loads(value)


def main() -> int:
    args = parse_args()
    if not torch.cuda.is_available():
        raise RuntimeError("Avaliação do adapter exige GPU CUDA.")

    bf16 = torch.cuda.is_bf16_supported()
    dtype = torch.bfloat16 if bf16 else torch.float16

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token

    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=dtype,
    )
    base = AutoModelForCausalLM.from_pretrained(
        args.model,
        quantization_config=quant,
        device_map="auto",
        torch_dtype=dtype,
    )
    model = PeftModel.from_pretrained(base, args.adapter)
    model.eval()

    examples = [
        json.loads(x)
        for x in Path(args.eval).read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]

    rows = []
    for index, ex in enumerate(examples, 1):
        messages = [
            {"role": "system", "content": build_training_system_instruction()},
            {"role": "user", "content": build_user_payload(ex["input"])},
        ]
        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

        started = time.perf_counter()
        error = ""
        parsed = None
        raw = ""

        try:
            with torch.no_grad():
                out = model.generate(
                    **inputs,
                    max_new_tokens=args.max_new_tokens,
                    do_sample=True,
                    temperature=0.7,
                    top_p=0.8,
                    top_k=20,
                    pad_token_id=tokenizer.eos_token_id,
                )
            new_ids = out[0][inputs["input_ids"].shape[-1]:]
            raw = tokenizer.decode(new_ids, skip_special_tokens=True).strip()
            parsed = parse_json(raw)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

        elapsed = round(time.perf_counter() - started, 3)
        checks = evaluate_output(ex, parsed, error)
        rows.append({
            "id": ex.get("id"),
            "tags": (ex.get("metadata") or {}).get("tags", []),
            "target": ex.get("target"),
            "model_output": parsed,
            "raw": raw,
            "error": error,
            "latency_seconds": elapsed,
            "checks": checks,
        })
        print(
            f"[{index:02d}/{len(examples):02d}] {ex.get('id')} "
            f"{elapsed:.2f}s {'ERRO' if error else str(parsed)[:100]}"
        )

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    names = [
        "reported_facts_ok",
        "numeric_claims_ok",
        "ignore_ok",
        "oral_style_ok",
        "scarcity_ok",
        "quantity_ok",
        "buying_guidance_ok",
    ]
    summary = {
        "model": args.model,
        "adapter": str(args.adapter),
        "total": len(rows),
        "failed": sum(1 for r in rows if r["checks"].get("failed")),
        "checks": {},
    }
    for name in names:
        applicable = [
            r["checks"].get(name)
            for r in rows
            if r["checks"].get(name) is not None
        ]
        summary["checks"][name] = {
            "passed": sum(1 for x in applicable if x is True),
            "total": len(applicable),
        }

    Path(args.summary).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
