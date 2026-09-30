# Baselines do AGCN Presenter

Este diretório guarda a fotografia do comportamento do modelo antes e depois de cada etapa de treinamento.

## Baseline v0.1 — Qwen3-4B atual

Entrada congelada:
- `training/evaluation/frozen_eval_v0.1.jsonl`
- 25 situações que não entram no SFT/LoRA.

Runner:
- `training/scripts/run_baseline_current_qwen.py`

Saídas esperadas:
- `qwen3_4b_current_v0.1.jsonl`
- `qwen3_4b_current_v0.1_summary.json`

Modelo:
- Qwen3-4B-Q4_K_M.gguf
- llama.cpp
- PresenterBrain/validators atuais do AGCN

## O que será medido

- latência;
- resposta vs. IGNORAR;
- intenção de compra;
- orientação de compra;
- escassez;
- escassez com quantidade;
- marcadores formais de fala;
- falhas/rejeições dos validators.

A avaliação automática é só um indicador. A comparação final será cega e lado a lado com o modelo treinado.

## Regra de isolamento

O conjunto `frozen_eval_v0.1.jsonl` nunca pode entrar no treinamento, expansão sintética ou preference tuning.
