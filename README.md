# AGCN Live Voice

Apresentador inteligente por voz para TikTok LIVE.

## Status atual

**Baseline V0.4.1 migrada do Colab para uma arquitetura reutilizável.**

Objetivo desta baseline: preservar o que já foi validado no Colab antes de iniciar a V0.5 Presenter Behavior.

### Já validado no Colab

- conexão com TikTok LIVE por `@username`;
- Room ID;
- viewers;
- likes;
- comentários;
- shares;
- Product Store;
- produto ativo;
- classificação básica de comentários;
- prioridade;
- fila;
- geração de fala sugerida;
- atualização automática da interface.

## Regra de arquitetura

O projeto é dividido para que o núcleo possa ser reaproveitado no aplicativo Windows final.

```text
core/        -> lógica definitiva/reutilizável
backend/     -> ponte temporária para o site de teste
test_web/    -> interface web temporária
data/        -> dados locais e dataset do Presenter
tests/       -> testes automáticos
desktop/     -> será criado na fase final com PySide6
```

O site e o Railway são apenas ferramentas temporárias de teste. O produto final será um programa Windows local.

## Executar localmente

```bash
python -m pip install -r requirements.txt
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Depois abra `http://localhost:8000`.

## Railway

Start command:

```bash
uvicorn backend.app:app --host 0.0.0.0 --port $PORT
```

## Próxima versão

**V0.5 — Presenter Behavior V1**

- Memory Manager
- Comment Intelligence
- Comment Fusion
- Decision Engine V2
- Silence Watchdog
- Speech Planner
- Sales Guard
- Anti-repetição
- AGCN Presenter Dataset V1


## Branch de desenvolvimento V0.5

A branch `v0.5-presenter-behavior` implementa o primeiro Presenter Behavior V1:
memória operacional, inteligência e fusão de comentários, Decision Engine V2,
Silence Watchdog, Speech Planner, Sales Guard e contexto comercial ampliado do produto.

Esta branch é testada em um serviço Railway separado antes de qualquer alteração da baseline `main`.


## V0.5.1 — Ficha Inteligente do Produto

A branch `v0.5.1-product-intelligence` separa dados permanentes do produto das condições temporárias da LIVE, registra origem/confiança dos campos e permite edição manual com prioridade sobre futuras pesquisas automáticas.

A análise automática do link será ativada na V0.5.2.


## V0.5.2 — Product Research

A branch `v0.5.2-product-research` ativa o botão **Analisar produto**.
O sistema resolve o link, tenta extrair dados estruturados, procura fontes públicas relacionadas,
monta um rascunho com origem/confiança e preserva qualquer campo travado manualmente pelo usuário.

A pesquisa é conservadora: não contorna login, CAPTCHA ou bloqueios de sites.


## V0.6.1 — Natural Presenter

A branch `v0.6.1-natural-presenter` ajusta o Presenter para se comportar como apresentadora de LIVE, e não como chatbot:

- pergunta sem resposta conhecida é ignorada silenciosamente;
- respostas conhecidas são curtas, informais e sem mencionar ficha/cadastro/sistema;
- no máximo 3 respostas consecutivas a comentários;
- após a 3ª resposta, 30 segundos obrigatórios falando do produto;
- comentários continuam sendo analisados e aguardam na fila durante esse intervalo;
- campos com vários itens (descrição, benefícios etc.) são tratados ponto por ponto;
- uma fala usa um ponto por vez, sem despejar o bloco inteiro;
- o teste web mostra o modo produto e o tempo restante para voltar aos comentários.

Essas regras ficam em `core/` e `core/runtime.py`, portanto são compartilhadas pelo protótipo web e pelo futuro aplicativo Windows. A interface Windows final ainda será construída sobre esse mesmo núcleo, sem duplicar a lógica do Presenter.
