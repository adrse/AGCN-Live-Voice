# AGCN Live Voice

Aplicativo Windows local para apresentação e apoio de vendas em LIVE commerce, com foco em TikTok LIVE.

## Estado atual

A `main` é a fonte canônica do projeto.

O programa já reúne:
- conexão e monitoramento de TikTok LIVE;
- comentários, likes, viewers e eventos;
- cadastro e contexto de produto;
- Presenter com continuidade comercial, fila e priorização de comentários;
- Brain local com Qwen3-4B via `llama.cpp`;
- suporte ao **AGCN Presenter v0.1** treinado por LoRA;
- voz local HQ com Qwen3-TTS e fallback Kokoro;
- aplicativo desktop PySide6;
- instalador Windows offline completo.

## AGCN Presenter v0.1

O primeiro treinamento especializado foi preservado na própria `main` em:

- `data/training/presenter_v0.1/`
- `docs/presenter_v0.1/`

O experimento usou **100 Gold (93 treino + 7 validação)** e foi avaliado em **25 casos congelados**.

O runtime local procura automaticamente o adapter convertido:

`AGCN-Presenter-v0.1-F16.gguf`

Ele pode ficar:
- em `brain_local/models/` dentro do pacote; ou
- em `%LOCALAPPDATA%\AGCN Live Voice\models\`.

Quando encontrado, o `llama-server` recebe `--lora` e usa o AGCN Presenter v0.1. Sem o arquivo, o aplicativo continua funcionando com o Qwen3-4B base.

Os pesos do adapter PEFT original não são versionados no repositório público. O snapshot registra configuração, hash, datasets e resultados para preservar o estado do treinamento.

## Estrutura

```text
core/        -> lógica principal, Presenter, Brain, voz e integrações
desktop/     -> aplicativo Windows PySide6
backend/     -> backend usado por ferramentas/testes web
data/        -> dados locais e snapshot de treinamento
docs/        -> documentação técnica e histórico essencial
tests/       -> testes automatizados
scripts/     -> utilitários de desenvolvimento e diagnóstico
installer/   -> instalador Windows
tools/       -> ferramentas auxiliares
```

## Desenvolvimento local

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-desktop.txt
python -m desktop.main
```

Para o backend de teste:

```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

## Builds Windows

Os workflows em `.github/workflows/` cobrem:
- build desktop;
- build com voz HQ;
- build do instalador offline completo;
- testes do Presenter Brain.

O instalador offline completo baixa e empacota o Qwen3-4B base e os runtimes locais durante o build.

## Regra de trabalho

Mudanças estáveis entram na `main`. Novos experimentos de treinamento estão pausados até o teste manual do AGCN Presenter v0.1 no programa Windows.
