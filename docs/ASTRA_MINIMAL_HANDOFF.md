# Astra 6 Ultra — handoff mínimo e orientado a execução

Objetivo: gastar o mínimo possível de contexto/análise. NÃO reestude o projeto inteiro.

Repositório: adrse/AGCN-Live-Voice
Branch: astra-handoff-2026-09-29

## Regra de trabalho

1. NÃO reescreva módulos que já estão verdes.
2. NÃO faça revisão teórica do projeto inteiro.
3. Comece pelos comandos/testes abaixo.
4. Só abra o arquivo diretamente relacionado a um teste/erro.
5. Preserve as decisões arquiteturais existentes.
6. Prioridade final: programa Windows executável e testado.

## Primeiro: verificar GitHub Actions

Workflows:
- Presenter Brain Core
- Build Windows Desktop

Se ambos estiverem verdes no HEAD atual:
- considere Brain/core/UI/imports/build básico previamente validados;
- não gaste tokens relendo esses módulos sem motivo.

## Segundo: no Windows real

Instalar/confirmar:
- Ollama;
- qwen3:4b;
- VB-CABLE;
- TikTok LIVE Studio.

Executar:

```bat
python scripts\doctor.py
python scripts\test_brain.py --provider qwen_local --proactive
python scripts\test_brain.py --provider qwen_local --comment "quanto custa?"
python scripts\test_voice.py --list-devices
python scripts\test_voice.py --device "CABLE Input" --text "Teste AGCN"
```

Se algum comando falhar, investigue SOMENTE a camada correspondente.

## Arquitetura que já existe

TikTokMonitor
-> Comment Intelligence/Fusion
-> Decision Engine
-> Speech Planner
-> BrainContext
-> PresenterPolicy única
-> Qwen/Ollama OU API
-> BrainResult JSON
-> validação factual
-> VoiceService
-> TTS
-> dispositivo/VB-CABLE.

Produto ativo é a fonte da verdade.

## Arquivos que só devem ser abertos se a camada falhar

Brain:
- core/model_transports.py
- core/brain_factory.py
- core/brain_orchestrator.py
- core/brain_context_builder.py
- core/presenter_policy.py
- core/presenter_v3.py

Áudio:
- core/tts_providers.py
- core/audio_output.py
- core/voice_service.py
- core/voice_factory.py

Runtime:
- core/runtime.py

UI:
- desktop/main_window.py
- desktop/app_controller.py
- desktop/config_store.py

Produto:
- core/product_store.py
- core/product_profile.py

## Decisões congeladas

- cadastro manual de produto obrigatório;
- sem avatar/MuseTalk;
- sem player de vídeo;
- Qwen local padrão;
- API opcional;
- mesma PresenterPolicy para todos os Brains;
- TTS local padrão e premium opcional;
- resposta prioritária espera a frase atual terminar e entra antes de proativos pendentes;
- nenhum segredo em JSON/Git/exe;
- chave pode vir do ambiente ou Windows Credential Manager;
- produto/preço/estoque/frete/etc. nunca podem ser inventados.

## Só depois dos testes

1. Corrija falhas reais.
2. Teste LIVE real.
3. Teste VB-CABLE -> TikTok LIVE Studio.
4. Faça pequenos ajustes de UI necessários.
5. Gere o build final.
6. Entregue o ZIP/exe e lista objetiva de pendências.

## Critério para NÃO mexer

Se uma camada:
- tem teste verde;
- passa no Doctor;
- passa no teste manual correspondente;

não refatore apenas por preferência.

## Saída final esperada

- executável Windows;
- caminho/ZIP;
- testes que passaram;
- dependências externas necessárias;
- somente pendências comprovadas.
