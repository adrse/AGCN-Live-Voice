# Plano — AGCN Presenter Model

Status: laboratório em branch isolada.

## Visão

O AGCN Presenter Model será uma especialização do modelo-base local, focada em condução de LIVE commerce. O objetivo não é ensinar conhecimento geral, e sim comportamento comercial seguro e natural.

O primeiro caminho de treinamento será:
1. dataset ouro humano;
2. expansão sintética revisada;
3. SFT/LoRA;
4. avaliação cega contra o modelo-base;
5. preference tuning somente se houver ganho mensurável;
6. conversão para formato local compatível com o runtime;
7. teste de LIVE;
8. integração na main apenas após aprovação.

## O que entra no treino

- resposta a preço, cupom, frete, estoque e garantia;
- compatibilidade e perguntas técnicas;
- objeções;
- intenção de compra;
- confirmação de compra;
- comentários irrelevantes;
- pergunta sem fato autorizado;
- condução sem comentário;
- retomada depois de interrupção;
- anti-repetição;
- CTA intercalado;
- variação de ângulo comercial;
- uso de táticas como price_anchor, benefit_translation e grounded_scarcity.

## O que NÃO deve ser "memorizado" pelo modelo

Preço de produto específico, estoque, cupom, garantia, especificações e condições de LIVE não devem virar conhecimento permanente. Esses dados continuam chegando em tempo de execução por PRODUCT / LIVE_CONDITIONS / ALLOWED_FACTS.

## Estratégia de dados

### Fase 1 — Gold Seed
500–1.000 exemplos feitos/revisados por humanos.

### Fase 2 — Expansão
10k–30k exemplos com variações geradas e filtradas.

### Fase 3 — Diversidade
Produtos e categorias diferentes, gírias, erros de digitação, perguntas curtas, comentários simultâneos e mudanças de contexto.

### Fase 4 — Dados reais
Interações de LIVE revisadas e anonimizadas podem virar exemplos de alta qualidade.

## Papel do usuário/especialista de LIVE

O dado mais valioso é informação de comportamento real:
- "o que uma boa vendedora falaria aqui?";
- "o que ela não deveria falar?";
- "qual comentário merece resposta?";
- "quando é hora de ignorar e continuar?";
- "qual frase soa robótica?";
- "qual frase geraria desejo?";
- "como retomar o produto sem parecer repetitivo?".

Essas decisões viram exemplos ouro.

## Voz

O treinamento do Presenter e o treinamento/ajuste de voz ficam separados.
O Presenter decide o que dizer e a intenção; a camada de voz decide como entregar.
Tags como `voice_style` podem ser preservadas no dataset para estudos posteriores de prosódia.

## Critério de integração

Nenhuma integração na `main` ocorrerá só porque o fine-tuning terminou. A nova versão precisa:
- passar validação factual;
- superar baseline em teste congelado;
- manter latência prática;
- funcionar com o runtime local;
- preservar fallback e segurança existentes.
