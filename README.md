# AGCN Live Voice

Aplicativo Windows para LIVE commerce com Presenter inteligente, monitoramento de TikTok LIVE, produto ativo e voz.

## Estado atual

A `main` é a versão funcional do programa Windows.

Ela já contém:
- aplicativo desktop em PySide6;
- conexão e monitoramento de TikTok LIVE;
- comentários, fila, prioridade e retomada da venda;
- Product Store e produto ativo;
- Brain local com Qwen3-4B via llama.cpp;
- suporte ao AGCN Presenter v0.1 por LoRA GGUF;
- Qwen3-TTS HQ com Kokoro como fallback;
- opções de provedores por API;
- build e instalador Windows;
- testes automatizados.

## AGCN Presenter v0.1

O primeiro treino especializado foi concluído e o snapshot essencial está preservado na própria `main` em:

- `data/training/presenter_v0.1/`
- `docs/presenter_v0.1/`

Esse experimento usou 100 exemplos Gold, com 93 de treino e 7 de validação, e foi avaliado em 25 casos congelados.

O runtime procura o adapter convertido como:

`AGCN-Presenter-v0.1-F16.gguf`

Ele pode ficar no pacote em `brain_local/models/` ou, no Windows, em:

`%LOCALAPPDATA%\AGCN Live Voice\models\`

Quando o adapter está presente, o Brain local inicia com o AGCN Presenter v0.1. Sem ele, o programa continua usando o Qwen3-4B base como fallback.

## Regra para pergunta sem resposta

Se a informação necessária não estiver nos fatos permitidos do produto, o Presenter não inventa e não fala que o dado está ausente. A pergunta é ignorada internamente e a LIVE continua.

## Estrutura

```text
core/        lógica do Presenter, Brain, TikTok, produto e voz
desktop/     aplicativo Windows
installer/   instalador
data/        dados locais e snapshots essenciais
docs/        documentação
scripts/     utilitários
tests/       testes automatizados
.github/     pipelines de teste e build
```

## Executar em desenvolvimento

```bash
python -m pip install -r requirements.txt
python -m pip install -r requirements-desktop.txt
python -m desktop.main
```

No Windows também existe:

```bat
scripts\run_desktop.bat
```

## Build principal

Use o workflow **Build Windows Complete Offline Installer** para gerar o pacote completo do aplicativo.

## Estado da pesquisa

Novos treinos estão pausados. O próximo passo é testar manualmente o AGCN Presenter v0.1 no programa Windows antes de decidir qualquer nova rodada de treinamento.
