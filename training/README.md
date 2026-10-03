# AGCN Presenter Training Lab

Laboratório isolado para desenvolver e avaliar um modelo especializado em LIVE commerce antes de qualquer integração com a `main`.

## Objetivo

Especializar o Brain local do AGCN para:
- responder comentários comerciais com naturalidade;
- continuar vendendo quando não houver comentário;
- priorizar intenção de compra, objeções e dúvidas que travam conversão;
- trabalhar escassez/urgência como técnica central de LIVE;
- usar quantidade exata quando ela estiver disponível;
- variar abordagem e evitar repetição;
- escolher linguagem curta, oral e apropriada para TTS;
- preservar a linha comercial depois de interrupções.

O laboratório **não altera o runtime atual**. O alvo desta fase é transformar LIVEs reais em dados revisáveis, construir avaliação e preparar o primeiro SFT/LoRA.

## Estrutura

- `schema/presenter_example.schema.json`: contrato oficial de cada exemplo.
- `datasets/gold_seed_v0.1.jsonl`: seed inicial.
- `datasets/real_live_gold_v0.2.jsonl`: 28 exemplos Gold de situações observadas/revisadas.
- `datasets/gold_expansion_v0.3.jsonl`: 72 exemplos Gold derivados dos relatórios e revisados para oralidade.
- `datasets/preferences_v0.1.jsonl`: pares melhor/pior para treinamento por preferência futuro.
- `datasets/source_manifest_v0.2.json`: origem, produto e grupos de duplicidade dos relatórios analisados.
- `evaluation/README.md`: regras de avaliação e critérios de aprovação.
- `evaluation/frozen_eval_v0.1.jsonl`: 25 situações congeladas que não entram no treino.
- `policies/SCARCITY_POLICY.md`: regra operacional de escassez do AGCN.
- `policies/ORAL_STYLE_PTBR.md`: padrão informal de fala ("tá", "tô", "pra", etc.).
- `scripts/validate_dataset.py`: validação estrutural e de escassez.
- `scripts/export_sft.py`: exporta exemplos aprovados para formato de chat SFT.
- `scripts/dataset_stats.py`: estatísticas de cobertura.
- `scripts/lint_oral_style.py`: aponta falas formais demais no `target.speech`.
- `../docs/AGCN_PRESENTER_TRAINING.md`: plano de evolução do modelo.

## Filosofia dos dados

O AGCN aprende comportamento:

`situação -> intenção -> estratégia -> fala -> retomada`

O produto continua chegando dinamicamente. O modelo não precisa decorar preço, características ou estoque de um item específico.

## Escassez no treinamento

A LIVE opera com a premissa comercial de inventário limitado. O contexto pode receber:

```json
{
  "commercial_rules": {
    "live_inventory_limited": true,
    "generic_scarcity_enabled": true,
    "stock_quantity": null
  }
}
```

Sem quantidade exata, o modelo aprende linguagem genérica de escassez e fechamento. Quando `stock_quantity` existir, aprende também contagem específica.

A quantidade exata nunca deve ser criada pelo modelo; ela vem do contexto.

## Estado atual — CONGELADO EM v0.1

**Decisão de 02/10/2026:** pausar novos treinos e novas baterias de avaliação por enquanto.

O estado que deve ser preservado é o experimento **AGCN Presenter v0.1** já concluído:

- base Gold usada no primeiro treino: **100 exemplos**;
- split do treino: **93 train + 7 validation**;
- avaliação já realizada: **25 casos congelados** em `evaluation/frozen_eval_v0.1.jsonl`;
- adapter/resultados do v0.1 permanecem como referência de pesquisa;
- próximo passo prático: **testar manualmente no computador o comportamento do programa** antes de qualquer novo treino.

Os materiais v0.2/500 Gold que já foram preparados **não devem disparar novo treino automaticamente**. Eles ficam preservados apenas como trabalho futuro, sem integração na `main` e sem nova avaliação até nova decisão.

A `main` continua sendo a branch do programa funcional. A branch `research/agcn-presenter-training-v1` fica como o único laboratório ativo de pesquisa do Presenter.


A base principal já chegou a **100 exemplos Gold derivados/revisados a partir das LIVEs**:

- 28 em `real_live_gold_v0.2.jsonl`;
- 72 em `gold_expansion_v0.3.jsonl`.

Além disso há **25 situações congeladas** em `evaluation/frozen_eval_v0.1.jsonl` para comparação do modelo-base com o futuro AGCN Presenter.

O seed inicial de 10 exemplos continua separado para referência e testes de schema.

### Oralidade

A resposta ideal do AGCN deve soar falada, não escrita. O padrão prioriza formas como:

- tá;
- tô;
- pra;
- ó;
- bora;
- cê, quando combinar com a frase.

A informalidade deve ser natural, sem transformar toda frase em gíria ou repetir a mesma muleta.

Esta branch é um laboratório. Nada daqui é enviado automaticamente para a aplicação de produção.


## Pipeline v0.1 preparado

A branch agora já contém o caminho completo até a primeira comparação:

1. `scripts/run_baseline_current_qwen.py` — roda o Qwen3-4B atual nas 25 situações congeladas.
2. `scripts/build_sft_corpus.py` — monta o corpus com 93 exemplos de treino e 7 de validação.
3. `training_policy.py` — política de treino separada do runtime atual, com oralidade PT-BR e escassez.
4. `scripts/train_lora_qwen3.py` — primeiro QLoRA em `Qwen/Qwen3-4B`.
5. `notebooks/AGCN_Presenter_v0_1_Colab.ipynb` — fluxo pronto para Google Colab com GPU e salvamento no Drive.
6. `scripts/run_lora_frozen_eval.py` — roda o adapter treinado nas mesmas 25 situações.
7. `scripts/compare_models.py` — gera comparação Qwen atual vs AGCN Presenter v0.1.

### Por que a política de treino está separada?

O prompt/runtime atual precisa continuar intacto enquanto fazemos o baseline "antes".
A nova política de oralidade/escassez fica no laboratório até o modelo treinado passar na avaliação.
Só depois as mudanças necessárias entram em `core/` e na `main`.

### Modelo-base

O primeiro experimento usa `Qwen/Qwen3-4B` como modelo de treinamento e mantém `enable_thinking=False`, porque o Presenter precisa de resposta curta e rápida, não raciocínio longo visível.
