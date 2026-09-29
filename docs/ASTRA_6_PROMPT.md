# Prompt para Astra 6 — auditar, integrar e finalizar o AGCN Live Voice

Você está assumindo o repositório privado `adrse/AGCN-Live-Voice`.

Trabalhe na branch `astra-handoff-2026-09-29`.

Leia nesta ordem:
1. `docs/ASTRA_HANDOFF_2026-09-29.md`
2. `docs/PRESENTER_BRAIN_SPEC.md`
3. `core/presenter_policy.py`
4. `core/brain_context_builder.py`
5. `core/model_transports.py`
6. `core/brain_orchestrator.py`
7. `core/brain_factory.py`
8. `core/presenter_v3.py`
9. `core/tts_providers.py`
10. `core/audio_output.py`
11. `core/voice_service.py`
12. `core/voice_factory.py`
13. `core/runtime.py`
14. `core/comment_selection_policy.py`
15. `desktop/config.example.json`
16. `docs/DESKTOP_MVP_SPEC.md`
17. `docs/ACCEPTANCE_TESTS_MVP.md`
18. testes existentes.

MISSÃO: entregar o programa Windows funcional **AGCN Live Voice — Sua voz inteligente para vender ao vivo.**

## Decisões que NÃO devem ser revertidas

- sem avatar/MuseTalk;
- sem player/playlist de vídeo no AGCN;
- vídeo fica no TikTok LIVE Studio/OBS;
- cadastro manual do produto é essencial e é a fonte da verdade;
- Qwen/Ollama local é o Brain padrão;
- API é alternativa opcional;
- Qwen e API usam a MESMA PresenterPolicy;
- nenhum provider pode ter prompt comercial próprio;
- nenhum texto bruto de LLM vai direto ao TTS;
- TTS local padrão + premium opcional;
- áudio sai no device escolhido/VB-CABLE;
- nenhum secret embutido.

## Já implementado — audite antes de alterar

Brain:
- Ollama/Qwen real;
- OpenAI Responses API;
- provider OpenAI-compatible;
- JSON Schema;
- factory e fallback;
- BrainContext derivado do produto ativo;
- PresenterV3;
- validação de fatos e alegações sensíveis.

Voz:
- TTS local pyttsx3/SAPI;
- TTS OpenAI opcional;
- fallback TTS;
- SoundDeviceAudioSink;
- listagem/seleção de device;
- VoiceService com fila prioritária;
- VoiceFactory.

Runtime:
- pode receber Brain e Voice reais;
- fala aprovada é enfileirada para TTS;
- resposta prioritária remove proativos pendentes;
- frase que já está tocando termina antes da resposta;
- TikTokMonitor e ProductStore antigos são preservados.

Laboratórios:
- `scripts/test_brain.py`;
- `scripts/test_voice.py`.

Testes:
- `tests/test_brain_orchestrator.py`;
- `tests/test_model_transports.py`;
- `tests/test_brain_context_builder.py`;
- `tests/test_brain_factory.py`;
- `tests/test_presenter_v3.py`;
- `tests/test_tts_voice_service.py`;
- demais testes históricos;
- CI `.github/workflows/test-presenter-brain.yml`.

## Fluxo final esperado

TikTok LIVE
-> comentário/métricas
-> filtro + prioridade
-> Decision Engine
-> Speech Planner
-> produto ativo + memória
-> PresenterPolicy
-> Qwen/API
-> BrainResult JSON
-> validação factual
-> VoiceService
-> TTS
-> dispositivo/VB-CABLE
-> TikTok LIVE Studio.

Sem comentário relevante, o sistema continua falando do produto.
Com comentário prioritário, responde e retoma a venda.
Produto e condições comerciais são a única fonte de fatos.

## Trabalho de amanhã

1. Rode toda a suíte e corrija qualquer regressão.
2. Teste Qwen/Ollama real no Windows.
3. Teste OpenAI Responses API real e fallback.
4. Faça testes agressivos de factualidade/alucinação.
5. Teste TTS local e TTS premium reais.
6. Teste SoundDevice + VB-CABLE.
7. Integre o runtime às telas reais.
8. Termine Dashboard, Produto e Configurações.
9. Faça Configurações permitir escolher Brain, modelo, TTS, voz, device e testar cada item.
10. Garanta persistência local segura.
11. Teste cadastro/ativação/troca de produto.
12. Teste TikTokMonitor real e fala contínua.
13. Valide resposta a comentários + retomada.
14. Gere e teste o .exe.

Não gaste tempo com vídeo, avatar, mobile, pagamentos ou pesquisa automática.

Ao terminar entregue:
- arquivos alterados;
- testes e resultados;
- Qwen real testado;
- API real testada;
- TTS/device/VB-CABLE testados;
- pendências reais;
- caminho do .exe;
- instruções mínimas para instalar Ollama/Qwen e VB-CABLE.
