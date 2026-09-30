# AGCN Presenter Training Lab

Laboratório isolado para desenvolver e avaliar um modelo especializado em LIVE commerce antes de qualquer integração com a `main`.

## Objetivo

Especializar o Brain local do AGCN para:
- responder comentários comerciais com naturalidade;
- continuar vendendo quando não houver comentário;
- usar somente fatos autorizados do produto/LIVE;
- ignorar perguntas factuais sem resposta disponível;
- variar abordagem e evitar repetição;
- escolher linguagem curta, oral e apropriada para TTS;
- preservar uma linha comercial depois de interrupções.

O laboratório **não altera o runtime atual**. O primeiro alvo é produzir dados, métricas e scripts reproduzíveis. Só depois de uma comparação objetiva com o Brain atual o modelo treinado poderá ser integrado.

## Estrutura

- `schema/presenter_example.schema.json`: contrato oficial de cada exemplo.
- `datasets/gold_seed_v0.1.jsonl`: primeiro lote ouro, pequeno e revisável.
- `evaluation/README.md`: regras de avaliação e critérios de aprovação.
- `scripts/validate_dataset.py`: validação estrutural e factual sem dependências externas.
- `../docs/AGCN_PRESENTER_TRAINING.md`: plano de evolução do modelo.

## Filosofia dos dados

O AGCN não precisa decorar conhecimento geral. O dataset ensina **comportamento**:

`situação -> intenção -> estratégia -> fala segura`

Cada exemplo espelha o contrato real do Presenter:
- entrada semelhante a `BrainContext`;
- saída semelhante a `BrainResult`;
- `ALLOWED_FACTS` como fonte canônica;
- `needs_fact=true` + `speech="IGNORAR"` quando faltar fato obrigatório.

## Regra de ouro

Persuasão pode variar. Fatos não.

Nenhuma resposta pode inventar preço, estoque, cupom, frete, garantia, compatibilidade, especificação, prazo, benefício ou promoção.
