# Histórico de branches antes da limpeza

Data da revisão: 2026-10-03.

A `main` é a fonte canônica. Antes da remoção das branches antigas, os ponteiros abaixo foram registrados para referência:

| Branch | Tip SHA | Situação na revisão |
|---|---|---|
| `astra-handoff-2026-09-29` | `c0cb1b720b9a86be4e79c0c12527a6f414e3946b` | 0 commits à frente da main; antiga |
| `integration/agcn-presenter-v01` | `dc6283594e1d767325845aaac52e7a49fcb6325b` | 0 commits à frente da main; integração já absorvida |
| `research/agcn-presenter-training-v1` | `85f33d1b086200d78166d4bc58045753b21da801` | laboratório de treino; conteúdo essencial arquivado na main |
| `v0.5.2-product-research` | `2ed8187d48d3b31388b64b027899eafbc29859b6` | linha antiga, muito atrás da main |
| `v0.6.1-natural-presenter` | `e2fc2381cddf639a4d1452d4bc34d884f90ed187` | linha antiga, muito atrás da main |

## O que foi preservado antes da limpeza

O estado essencial do Presenter v0.1 está em:
- `data/training/presenter_v0.1/`
- `docs/presenter_v0.1/`

O rascunho de dados v0.2 que já existia foi consolidado em:
- `data/training/presenter_v0.2_draft/gold_synthetic_400.jsonl`

A aplicação e a integração do LoRA v0.1 estão na própria `main`.

Não é necessário manter as branches antigas para executar o programa ou preservar o primeiro experimento.
