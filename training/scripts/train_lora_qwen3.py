#!/usr/bin/env python3
"""Treino QLoRA do AGCN Presenter v0.1 em Qwen3-4B.

Pensado para GPU CUDA (Colab, RunPod, workstation etc.).
Salva SOMENTE o adapter LoRA; não salva o modelo-base de ~8 GB.

Exemplo:
  python training/scripts/train_lora_qwen3.py \
    --train training/outputs/agcn_presenter_v0.1_train.jsonl \
    --validation training/outputs/agcn_presenter_v0.1_validation.jsonl \
    --output training/outputs/agcn-presenter-v0.1-lora
"""

from __future__ import annotations

import argparse
import json
import hashlib
import importlib.metadata
from pathlib import Path

import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from torch.utils.data import Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    Trainer,
    TrainingArguments,
    set_seed,
)


class ChatDataset(Dataset):
    def __init__(self, path: str | Path, tokenizer, max_length: int = 2048):
        self.rows = []
        self.tokenizer = tokenizer
        self.max_length = int(max_length)

        with Path(path).open("r", encoding="utf-8") as handle:
            for raw in handle:
                raw = raw.strip()
                if raw:
                    self.rows.append(json.loads(raw))

        # Validate every example before spending GPU time. Never silently lose
        # the assistant answer by truncating a long system/product prompt.
        lengths = [len(self[index]["input_ids"]) for index in range(len(self.rows))]
        print(f"Dataset {path}: {len(lengths)} examples; maximum {max(lengths, default=0)} tokens", flush=True)

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        messages = self.rows[index]["messages"]
        prompt_messages = messages[:-1]

        prompt_text = self.tokenizer.apply_chat_template(
            prompt_messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        prompt_ids = self.tokenizer(
            prompt_text,
            add_special_tokens=False,
        )["input_ids"]
        response_ids = self.tokenizer(
            messages[-1]["content"] + self.tokenizer.eos_token,
            add_special_tokens=False,
        )["input_ids"]
        input_ids = prompt_ids + response_ids
        if len(input_ids) > self.max_length:
            ex_id = (self.rows[index].get("metadata") or {}).get("id", index)
            raise ValueError(f"Example {ex_id} needs {len(input_ids)} tokens; raise --max-length (no answer truncation allowed)")
        if not response_ids:
            raise ValueError(f"Example {index} has no supervised response tokens")
        attention_mask = [1] * len(input_ids)
        labels = [-100] * len(prompt_ids) + response_ids

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


class CausalPadCollator:
    def __init__(self, tokenizer):
        self.tokenizer = tokenizer

    def __call__(self, features):
        max_len = max(len(x["input_ids"]) for x in features)
        pad_id = self.tokenizer.pad_token_id

        batch = {"input_ids": [], "attention_mask": [], "labels": []}
        for row in features:
            pad = max_len - len(row["input_ids"])
            batch["input_ids"].append(row["input_ids"] + [pad_id] * pad)
            batch["attention_mask"].append(row["attention_mask"] + [0] * pad)
            batch["labels"].append(row["labels"] + [-100] * pad)

        return {k: torch.tensor(v, dtype=torch.long) for k, v in batch.items()}


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--train", required=True)
    p.add_argument("--validation", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--model", default="Qwen/Qwen3-4B")
    p.add_argument("--epochs", type=float, default=4.0)
    p.add_argument("--learning-rate", type=float, default=2e-4)
    p.add_argument("--max-length", type=int, default=2048)
    p.add_argument("--lora-r", type=int, default=16)
    p.add_argument("--lora-alpha", type=int, default=32)
    p.add_argument("--gradient-accumulation", type=int, default=8)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    set_seed(42)

    if not torch.cuda.is_available():
        raise RuntimeError(
            "Treino QLoRA v0.1 exige GPU CUDA. Use Colab/RunPod/workstation."
        )

    bf16 = torch.cuda.is_bf16_supported(including_emulation=False)
    compute_dtype = torch.bfloat16 if bf16 else torch.float16

    print(f"GPU: {torch.cuda.get_device_name(0)}; native BF16: {bf16}; compute dtype: {compute_dtype if 'compute_dtype' in locals() else dtype}", flush=True)

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    quant = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        quantization_config=quant,
        device_map={"": 0},
        torch_dtype=compute_dtype,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model)

    lora = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    train_ds = ChatDataset(args.train, tokenizer, args.max_length)
    val_ds = ChatDataset(args.validation, tokenizer, args.max_length)

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    kwargs = dict(
        output_dir=str(out),
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=args.gradient_accumulation,
        warmup_ratio=0.1,
        weight_decay=0.01,
        logging_steps=1,
        save_strategy="epoch",
        eval_strategy="epoch",
        save_total_limit=2,
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        report_to="none",
        optim="paged_adamw_8bit",
        gradient_checkpointing=True,
        remove_unused_columns=False,
        bf16=bf16,
        fp16=not bf16,
        seed=42,
        data_seed=42,
    )

    training_args = TrainingArguments(**kwargs)

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=CausalPadCollator(tokenizer),
    )
    trainer.train()
    trainer.save_model(str(out))
    tokenizer.save_pretrained(str(out))

    summary = {
        "base_model": args.model,
        "train_examples": len(train_ds),
        "validation_examples": len(val_ds),
        "epochs": args.epochs,
        "learning_rate": args.learning_rate,
        "lora_r": args.lora_r,
        "lora_alpha": args.lora_alpha,
        "max_length": args.max_length,
        "bf16": bf16,
        "thinking_mode": False,
        "best_checkpoint": trainer.state.best_model_checkpoint,
        "best_eval_loss": trainer.state.best_metric,
        "log_history": trainer.state.log_history,
        "base_model_revision": getattr(model.config, "_commit_hash", None),
        "train_sha256": hashlib.sha256(Path(args.train).read_bytes()).hexdigest(),
        "validation_sha256": hashlib.sha256(Path(args.validation).read_bytes()).hexdigest(),
        "versions": {name: importlib.metadata.version(name) for name in ["torch", "transformers", "peft", "bitsandbytes", "accelerate"]},
        "purpose": "AGCN Presenter v0.1",
    }
    (out / "agcn_training_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
