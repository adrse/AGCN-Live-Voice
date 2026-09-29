# AGCN Live Voice — handoff para Astra 6 (29/09/2026)

## Decisão final do MVP

O AGCN Live Voice é o cérebro e a voz da LIVE.

Fora do MVP:
- avatar/rosto IA e MuseTalk;
- player/playlist/loop de vídeo dentro do AGCN;
- janela 9:16 própria;
- câmera virtual;
- pesquisa automática de produto.

O vídeo do produto fica no TikTok LIVE Studio/OBS. O AGCN acompanha a LIVE, recebe comentários/métricas, conduz a venda continuamente e envia a voz para o dispositivo de áudio escolhido.

## Arquitetura congelada

TikTok LIVE
-> TikTokMonitor
-> Comment Intelligence / Fusion
-> Decision Engine
-> Speech Planner
-> BrainContext factual
-> PresenterPolicy compartilhada
-> Qwen/Ollama local OU API
-> BrainResult JSON
-> validação factual
-> VoiceService
-> TTS local OU premium
-> SoundDeviceAudioSink
-> VB-CABLE/dispositivo
-> TikTok LIVE Studio

Produto manual -> ProductStore -> BrainContext -> ALLOWED_FACTS.

## Implementado em 28/09

### Brain real

- `core/model_transports.py`
  - `OllamaTransport` para Qwen local em `/api/chat`;
  - JSON Schema/Structured Output;
  - `OpenAIResponsesTransport` para Responses API;
  - `OpenAICompatibleChatTransport` para outros providers compatíveis.

- `core/brain_factory.py`
  - escolhe provider por configuração;
  - Qwen local é padrão;
  - API pode cair automaticamente para Qwen local;
  - secrets vêm de variável de ambiente.

- `core/brain_context_builder.py`
  - separa PRODUCT e LIVE_CONDITIONS;
  - transforma somente campos cadastrados em `ALLOWED_FACTS`;
  - cadastro do produto é a fonte factual da LIVE.

- `core/presenter_v3.py`
  - reaproveita Comment Intelligence, Fusion, Decision Engine, Speech Planner, Memory e Watchdog;
  - usa Brain real para respostas e fala proativa;
  - registra fatos usados e continuidade.

- `core/brain_orchestrator.py`
  - exige BrainResult JSON;
  - valida `used_facts`;
  - bloqueia preço, desconto, estoque, frete, cupom, garantia, resistência à água e números explícitos sem suporte no cadastro;
  - faz retry quando a saída é rejeitada.

### Voz e áudio

- `core/tts_providers.py`
  - TTS local offline via pyttsx3/SAPI;
  - TTS OpenAI opcional;
  - fallback premium -> local;
  - saída normalizada em `AudioChunk`.

- `core/audio_output.py`
  - lista dispositivos de saída;
  - seleciona device;
  - volume;
  - playback PCM;
  - preparado para selecionar VB-CABLE.

- `core/voice_service.py`
  - fila prioritária de voz;
  - worker TTS/playback;
  - permite remover falas proativas ainda não iniciadas quando chega resposta prioritária.

- `core/voice_factory.py`
  - monta TTS + AudioSink + VoiceService a partir da configuração.

### Runtime

`core/runtime.py` aceita:
- `brain_provider` ou `brain_config`;
- `voice_service` ou `voice_config`.

Com ambos configurados, o fluxo chega a:
TikTok -> comentário/decisão -> PresenterV3 -> Brain -> fala validada -> VoiceService -> TTS -> dispositivo.

A resposta prioritária não corta a frase de áudio no meio. Ela remove proativos pendentes e entra como próxima fala.

### Laboratórios

Brain:
```
python scripts/test_brain.py --provider qwen_local --proactive
python scripts/test_brain.py --provider qwen_local --comment "quanto custa?"
python scripts/test_brain.py --provider openai --comment "pega internet?"
```

Voz:
```
python scripts/test_voice.py --list-devices
python scripts/test_voice.py --device "CABLE Input" --text "Teste da voz AGCN"
python scripts/test_voice.py --provider openai --device "CABLE Input"
```

## Cadastro do produto — regra essencial

O programa não pode iniciar a apresentação sem produto ativo.

Campos permanentes preservados:
- product_url;
- name, brand, model, category;
- description;
- key_benefits;
- problems_solved;
- differentials;
- included_items;
- compatibility;
- size_info;
- battery_info;
- usage_info;
- warranty;
- limitations;
- additional_info;
- image_url.

Condições da LIVE:
- regular_price;
- current_price;
- discount;
- stock;
- shipping_info;
- coupon;
- live_offer;
- live_offer_text;
- promotion_note.

Qwen e API recebem exatamente a mesma PresenterPolicy e os mesmos fatos do produto ativo.

## Configuração e secrets

`desktop/config.example.json` contém Brain, TTS, áudio e Presenter.

- OpenAI usa `OPENAI_API_KEY`.
- Provider compatível pode usar `AGCN_LLM_API_KEY`.
- nenhuma chave deve entrar no Git, config distribuído ou exe.

## Testes adicionados

- `tests/test_model_transports.py`
- `tests/test_brain_context_builder.py`
- `tests/test_brain_factory.py`
- `tests/test_presenter_v3.py`
- `tests/test_tts_voice_service.py`
- testes reforçados em `tests/test_brain_orchestrator.py`
- workflow `.github/workflows/test-presenter-brain.yml`.

## O que Astra 6 deve fazer amanhã

Não reescrever a arquitetura. Primeiro auditar e executar.

1. Rodar toda a suíte e corrigir regressões.
2. Testar Ollama/Qwen real em Windows.
3. Testar API real e fallback para local.
4. Testar TTS local real no Windows.
5. Testar TTS premium.
6. Testar listagem/seleção de device e VB-CABLE.
7. Ligar PresenterV3 + VoiceService definitivamente às telas.
8. Completar Dashboard, Produto e Configurações.
9. Garantir persistência das configurações e secrets fora do arquivo público.
10. Testar TikTokMonitor + comentários + fala contínua em LIVE real.
11. Testar troca de produto ativo durante execução.
12. Empacotar e validar o .exe com PyInstaller.

## Pronto significa

1. programa Windows abre sem terminal;
2. produto é cadastrado/ativado;
3. conecta TikTok por username;
4. recebe métricas/comentários;
5. PresenterV3 fala continuamente;
6. Qwen local funciona sem chave;
7. API usa exatamente a mesma PresenterPolicy;
8. pergunta relevante entra na frente de proativos pendentes;
9. resposta usa apenas fatos cadastrados;
10. após resposta a venda continua;
11. TTS toca no device escolhido;
12. VB-CABLE entrega áudio ao TikTok LIVE Studio;
13. falha de API/TTS premium cai para local quando habilitado;
14. secrets não entram no exe/repo;
15. build Windows fica pronto.


---

## Atualização final desta preparação

Após o handoff inicial, também foram concluídos:

- Dashboard, Produto e Configurações deixaram de ser placeholders e estão ligados ao core;
- `desktop/app_controller.py` liga UI, Runtime, ProductStore, Brain, voz e config;
- `desktop/config_store.py` persiste configuração em AppData;
- `core/secret_store.py` usa variável de ambiente ou keyring/Windows Credential Manager;
- `core/runtime.py` passou a executar Presenter em worker de background; `snapshot()` é somente leitura e não consome LLM;
- restart do Presenter/VoiceService após Stop foi corrigido;
- `core/diagnostics.py` + `scripts/doctor.py` verificam produto, Brain, TTS, devices e VB-CABLE;
- `scripts/setup_qwen_windows.ps1` prepara Ollama/qwen3:4b;
- `scripts/ultra_preflight.ps1` concentra os testes de amanhã;
- logging/crash report fica em AppData;
- ProductStore também grava em AppData, adequado para executável Windows;
- build Windows automático com smoke da UI e do executável;
- suíte completa do repositório validada: **75 passed, 2 warnings**.

### Build Windows comprovado

Workflow `Build Windows Desktop` validou com sucesso:
- instalação de dependências;
- imports;
- criação da UI;
- PyInstaller;
- presença do `.exe`;
- abertura do próprio executável sem crash imediato;
- criação e upload do ZIP.

Artifact: `AGCN-Live-Voice-Windows`
Build de produção verificado: `1654d8975bbf7559af8ad8655eff89666cf9e280`.

### Portanto, amanhã NÃO é mais necessário

- desenhar arquitetura do Brain;
- implementar integração Qwen;
- implementar transporte OpenAI;
- criar validação factual;
- criar TTS base;
- criar saída de áudio;
- criar fila de voz;
- criar telas base;
- descobrir como usar PyInstaller;
- descobrir como persistir configuração;
- criar sistema de logs;
- escrever testes unitários do zero.

O foco de amanhã é somente ambiente real/hardware/serviços:
Ollama + qwen3:4b, API real opcional, áudio real, VB-CABLE, TikTok LIVE Studio, LIVE real e ajustes concretos encontrados nesses testes.
