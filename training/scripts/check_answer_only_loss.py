#!/usr/bin/env python3
"""Check optimized Trainer CE/gradients against a full Qwen3 projection on CPU."""
import tempfile
import torch
from transformers import Qwen3Config, Qwen3ForCausalLM, TrainingArguments
from train_lora_qwen3 import AnswerOnlyTrainer


def main():
    torch.manual_seed(123)
    model = Qwen3ForCausalLM(Qwen3Config(
        vocab_size=128, hidden_size=32, intermediate_size=64,
        num_hidden_layers=2, num_attention_heads=4,
        num_key_value_heads=2, head_dim=8, attention_dropout=0.0,
    )).cpu().eval()
    with tempfile.TemporaryDirectory() as output:
        trainer = AnswerOnlyTrainer(model=model, args=TrainingArguments(
            output_dir=output, use_cpu=True, report_to='none',
        ))
        for prefix in [1, 8, 11]:
            inputs = torch.randint(0, 128, (1, 12))
            labels = inputs.clone()
            labels[:, :prefix] = -100
            # Includes cross-batch token normalization, not just local mean CE.
            count = torch.tensor(32)
            model.zero_grad()
            full = model(input_ids=inputs, labels=labels,
                         use_cache=False, num_items_in_batch=count).loss
            full.backward()
            grads = {n: p.grad.clone() for n, p in model.named_parameters() if p.grad is not None}
            model.zero_grad()
            optimized = trainer.compute_loss(model, {
                'input_ids': inputs, 'labels': labels, 'use_cache': False,
            }, num_items_in_batch=count)
            optimized.backward()
            torch.testing.assert_close(full, optimized, rtol=1e-6, atol=1e-6)
            for name, param in model.named_parameters():
                if param.grad is not None:
                    torch.testing.assert_close(param.grad, grads[name], rtol=1e-5, atol=1e-6)
    print('PASS: optimized Trainer preserves loss and all parameter gradients for 3 masks')


if __name__ == '__main__':
    main()
