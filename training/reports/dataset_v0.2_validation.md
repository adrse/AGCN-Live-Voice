# AGCN Presenter — Validação do Dataset v0.2

Data: 2026-09-30  
Branch: `research/agcn-presenter-training-v1`  
Status: pesquisa — **não integrado à main**

## Snapshot fechado

O snapshot v0.2 passa a usar três fontes Gold, sem apagar os arquivos históricos:

- `training/datasets/real_live_gold_v0.2.jsonl` — 28 Gold Real
- `training/datasets/gold_expansion_v0.3.jsonl` — 72 Gold Synthetic já existentes
- `training/datasets/gold_synthetic_v0.2.jsonl` — 400 novos Gold Synthetic revisados

Total: **500 Gold**
- Gold Real: **28**
- Gold Synthetic: **472**
- Train: **458**
- Validation: **42**

Os 25 casos de `training/evaluation/frozen_eval_v0.1.jsonl` permanecem fora do treinamento.

## Validação dos 400 novos exemplos

Resultado: **APROVADO para compor o corpus v0.2**.

Checagens executadas sobre o arquivo persistido no GitHub:

- 400/400 linhas JSON válidas
- 365 train / 35 validation
- 235 `comment_reply`
- 165 `proactive`
- 77 produtos diferentes
- 0 IDs duplicados
- 0 inputs exatamente duplicados dentro do novo arquivo
- 0 sobreposição de ID ou input com os 100 Gold anteriores
- 0 sobreposição de ID ou input com os 25 casos congelados
- 0 `used_facts` fora de `allowed_facts`
- 0 marcadores principais de formalidade detectados pelo padrão de `lint_oral_style.py`
- 0 respostas que verbalizam "não sei", "não posso confirmar" ou "não está cadastrado"
- 41 exemplos com ação interna `IGNORAR`
  - 33 por falta de fato necessário
  - 8 por comentário irrelevante
- 15 casos com contexto de quantidade/estoque
  - 14 verbalizam uma quantidade e todas batem com `stock_quantity`
  - 1 representa estoque esgotado e faz a transição sem inventar quantidade

## Regra de IGNORAR

Foi preservada a regra definida para o Presenter:

- se uma pergunta factual não tem resposta nos dados permitidos: `speech="IGNORAR"`, `needs_fact=true`, sem explicar ao público que falta cadastro;
- `IGNORAR` é comando interno e nunca deve ir ao TTS;
- comentário irrelevante também pode ser ignorado, mas nesse caso `needs_fact=false`, porque não há falta de fato: a decisão é não deixar o comentário sequestrar a LIVE.

Por isso o validador da branch de pesquisa foi ajustado para aceitar `IGNORAR` com `needs_fact=false` **somente** quando o exemplo estiver marcado com `irrelevant_comment`. O comportamento histórico dos exemplos de falta de fato foi mantido.

## Oralidade

O novo lote preserva o estilo oral PT-BR do projeto:
- `tá`, `tô`, `pra`, `ó`, `bora`;
- respostas curtas;
- CTA direto;
- sem linguagem de SAC/chatbot;
- escassez forte dentro das regras comerciais.

## Escassez e fatos

- Escassez genérica depende de `live_inventory_limited=true` e `generic_scarcity_enabled=true`.
- Quantidade numérica só vem de `stock_quantity`.
- Nenhuma contagem de estoque nova foi autorizada por criatividade do modelo.
- Perguntas sem dado objetivo não recebem resposta improvisada.

## Corpus v0.2

Foi criado `training/scripts/build_sft_corpus_v0_2.py` separado do builder histórico do v0.1.

Ele combina os três datasets Gold do snapshot v0.2 e continua bloqueando:
- IDs duplicados;
- inputs que coincidam com a avaliação congelada;
- casos de teste congelados entrando no SFT.

Arquivos históricos do v0.1 continuam intactos.

## Próximo passo

Rodar o builder v0.2, treinar o **AGCN Presenter v0.2** com QLoRA e depois avaliar:
1. os mesmos 25 casos congelados;
2. comparação v0.1 x v0.2;
3. revisão qualitativa de naturalidade, escassez, CTA, intenção de compra, objeções e fidelidade aos fatos.

Nenhuma integração com a `main` deve ser feita antes dessa avaliação.
