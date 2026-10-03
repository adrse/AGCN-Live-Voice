# AGCN Presenter v0.1 — snapshot preservado

Este diretório guarda o estado essencial do primeiro treinamento do Presenter antes da limpeza das branches de pesquisa.

## O que foi realmente treinado

- Modelo-base: `Qwen/Qwen3-4B`
- Método: QLoRA / LoRA
- Gold total usado no experimento: **100 exemplos**
  - **28 Gold Real** em `gold_real_28.jsonl`
  - **72 Gold Synthetic** em `gold_synthetic_72.jsonl`
- Split: **93 treino + 7 validação**
- Melhor checkpoint do experimento: **checkpoint-36**
- Melhor validation loss registrado: **0,551506**
- Avaliação congelada: **25 casos**, preservados em `frozen_eval_25.jsonl`

Os resultados completos da avaliação ficam em:
- `eval_results_25.jsonl`
- `eval_summary_25.json`
- `training_summary.json`
- `docs/presenter_v0.1/EXPERIMENT_REPORT.md`
- `docs/presenter_v0.1/COMPARISON.md`
- `docs/presenter_v0.1/CONTROL_COMPARISON.md`

## Adapter

A configuração PEFT usada no adapter está em `adapter_config.json`.

Adapter PEFT final:
- arquivo original: `adapter_model.safetensors`
- tamanho registrado: **132.187.888 bytes**
- SHA256: `5652197ef5f1bc212822d071ed28cd5a9802fea62aa3f5f802e88896486a6524`
- armazenamento: Google Drive privado do projeto, em `MyDrive/AGCN/Presenter/agcn-presenter-v0.1-lora/`

Os pesos binários não são versionados neste repositório público.

## Uso no programa Windows

A `main` está preparada para usar o adapter pelo `llama.cpp`.

O runtime procura por:
`AGCN-Presenter-v0.1-F16.gguf`

Locais aceitos:
1. dentro do pacote: `brain_local/models/`
2. instalação local do usuário: `%LOCALAPPDATA%\AGCN Live Voice\models\`

Quando o GGUF existe, o `llama-server` é iniciado com `--lora` e o Brain passa a se identificar como **AGCN Presenter v0.1**.

Se o adapter ainda não estiver instalado, o programa continua funcional com o Qwen3-4B base. Isso é intencional para não quebrar o instalador atual.

> Importante: o `adapter_model.safetensors` original precisa ser convertido para LoRA GGUF antes de ser usado pelo `llama.cpp`. Não renomeie apenas a extensão.

## Estado do projeto

Novos treinos estão pausados. O próximo passo é teste manual do Presenter no programa Windows.

Os 400 exemplos v0.2 preparados posteriormente não fazem parte deste modelo v0.1 e não são necessários para executar o estado atualmente aprovado para teste.
