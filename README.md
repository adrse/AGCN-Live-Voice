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
