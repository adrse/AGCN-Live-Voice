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
- `datasets/real_live_gold_v0.2.jsonl`: primeira curadoria de situações observadas em LIVEs reais.
- `datasets/preferences_v0.1.jsonl`: pares melhor/pior para treinamento por preferência futuro.
- `datasets/source_manifest_v0.2.json`: origem, produto e grupos de duplicidade dos relatórios analisados.
- `evaluation/README.md`: regras de avaliação e critérios de aprovação.
- `policies/SCARCITY_POLICY.md`: regra operacional de escassez do AGCN.
- `scripts/validate_dataset.py`: validação estrutural e de escassez.
- `scripts/export_sft.py`: exporta exemplos aprovados para formato de chat SFT.
- `scripts/dataset_stats.py`: estatísticas de cobertura.
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

## Estado atual

Esta branch é um laboratório. Nada daqui é enviado automaticamente para a aplicação de produção.
