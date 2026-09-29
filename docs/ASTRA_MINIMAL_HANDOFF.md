# Astra 6 Ultra — handoff mínimo e orientado a execução

Objetivo: gastar o mínimo possível de contexto/análise. NÃO reestude o projeto inteiro.

Repositório: adrse/AGCN-Live-Voice
Branch: astra-handoff-2026-09-29

## Estado já verificado antes do handoff

- suíte completa do repositório após os perfis de voz: **85 passed, 2 warnings**;
- smoke Windows real de TTS local: **Dora PT-BR OK + Alex PT-BR OK, sem API**;
- build Windows com Kokoro/Dora/Alex embarcados: **SUCCESS**;
- dependências Windows: OK;
- smoke imports: OK;
- smoke da UI PySide6: OK;
- PyInstaller: OK;
- executável encontrado: OK;
- executável abriu sem encerrar imediatamente: OK;
- ZIP Windows gerado e publicado como artifact;
- artifact validado: `AGCN-Live-Voice-Windows`;
- build validado no commit de produção `1654d8975bbf7559af8ad8655eff89666cf9e280`;
- mudanças posteriores ao commit acima são somente testes/workflow, sem alteração do código de produção.

## Regra de trabalho para economizar Ultra

1. NÃO reescreva módulos verdes.
2. NÃO faça revisão teórica do projeto inteiro.
3. Comece executando `scripts\ultra_preflight.ps1`.
4. Só abra arquivo relacionado a uma falha concreta.
5. Se teste + Doctor + teste manual de uma camada passarem, NÃO refatore por preferência.
6. Prioridade: validar hardware/serviços reais e entregar o programa.

## Um comando primeiro

No PowerShell, na raiz:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\ultra_preflight.ps1
```

O script:
- mostra branch/commit;
- instala dependências;
- roda pytest;
- roda Doctor;
- verifica Ollama/Qwen;
- testa Brain;
- lista áudio;
- compila o Windows;
- entrega um resumo objetivo.

## O que já está implementado

TikTokMonitor
-> Comment Intelligence/Fusion
-> Decision Engine
-> Speech Planner
-> BrainContext
-> PresenterPolicy única
-> Qwen/Ollama OU OpenAI/API
-> BrainResult JSON
-> validação factual
-> Runtime em background
-> VoiceService
-> TTS
-> dispositivo/VB-CABLE.

UI funcional:
- Dashboard;
- Produto;
- Configurações;
- Doctor do sistema.

Persistência:
- produtos em AppData;
- config em AppData;
- secrets fora do JSON;
- OpenAI key por ambiente ou Windows Credential Manager/keyring.

Produto ativo continua sendo a fonte da verdade.

## Perfis de voz obrigatórios

Existem dois perfis:
- `female_fast` — Feminina — Vendas rápidas;
- `male_fast` — Masculina — Vendas rápidas.

Os dois usam o mesmo Presenter Brain e a mesma PresenterPolicy. Só muda a vocalização.

Regras:
- ritmo rápido;
- energia de live commerce;
- pouca pausa;
- comentário respondido imediatamente;
- resposta curta e volta rápida à venda;
- nenhuma voz deve soar como conversa casual lenta.

A voz oficial principal é LOCAL e independente de API:
- motor principal: Qwen3-TTS 1.7B CustomVoice Q8 via qwentts.cpp/GGML;
- feminina: Vivian;
- masculina: Ryan;
- idioma: Portuguese;
- velocidade: slider 0,80x–1,60x, com ajuste pós-síntese preservando pitch;
- modelo permanece carregado em servidor localhost para evitar reload por frase.

Fallback local:
- Kokoro PT-BR Dora/Alex, apenas quando o Voice Pack HQ não existe ou falha.

Nenhuma API externa é necessária para gerar voz.

## Testes reais que ainda importam

No PC real, validar:
1. Ollama instalado.
2. `qwen3:4b` instalado.
3. Qwen responde com produto cadastrado.
4. API OpenAI real somente se for usada para melhorar a inteligência.
5. Dora local realmente toca sem API.
6. Alex local realmente toca sem API.
7. `CABLE Input` aparece e recebe o áudio.
8. TikTok LIVE Studio recebe o VB-CABLE.
9. TikTokMonitor conecta a uma LIVE real.
10. comentário de compra/preço entra na prioridade.
11. após responder, a venda continua.
12. troca de produto ativo reflete nos fatos.

## Arquivos: só abra se a camada falhar

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
- desktop/logging_setup.py

Produto:
- core/product_store.py
- core/product_profile.py

Diagnóstico:
- core/diagnostics.py
- scripts/doctor.py

## Decisões congeladas

- cadastro manual do produto é obrigatório e factual;
- sem avatar/MuseTalk;
- sem player de vídeo;
- Qwen local é padrão;
- API é opcional;
- mesma PresenterPolicy para todos os Brains;
- Qwen3-TTS 1.7B HQ é a voz principal local; Kokoro é somente fallback; nenhuma API é requisito de voz;
- resposta prioritária espera a frase atual terminar e entra antes de proativos pendentes;
- nenhum segredo em JSON/Git/exe;
- preço/estoque/frete/especificações nunca podem ser inventados.

## Saída esperada do Astra

Não entregar relatório longo. Entregar:
- executável/ZIP final;
- testes reais que passaram;
- dependências externas necessárias;
- somente pendências comprovadas.


## Separação obrigatória: inteligência x voz

**Inteligência**
- padrão: Qwen/Ollama local;
- opcional: API para aumentar qualidade de interpretação/conversação.

**Voz**
- principal: Qwen3-TTS 1.7B CustomVoice Q8 local;
- feminina: Vivian;
- masculina: Ryan;
- fallback: Kokoro Dora/Alex;
- Voice Pack HQ faz parte da distribuição HQ;
- API não deve ser exigida nem oferecida como dependência para a voz principal.


## Importante sobre código legado de voz

Pode haver arquivos/classes experimentais antigos de TTS por API no histórico/árvore.
Eles NÃO fazem parte da arquitetura oficial do MVP.

Não gastar tokens integrando OpenAI TTS/ElevenLabs TTS.
A API OpenAI só interessa ao Presenter Brain.

Provider oficial: `qwen3_hq_auto` (Qwen3-TTS HQ -> fallback Kokoro).


## Build offline final validado

Workflow Windows validado:
- dependências Kokoro/ONNX: OK;
- download de modelo/vozes: OK;
- Dora PT-BR offline: OK;
- Alex PT-BR offline: OK;
- UI: OK;
- PyInstaller: OK;
- modelo e voices dentro do pacote: OK;
- executável abriu sem crash imediato: OK;
- ZIP gerado: OK.

Artifact: `AGCN-Live-Voice-Windows`
Workflow run: `36506324783`
Build SHA: `cd7c7747f0457b60d9dbfb2595bdc58a5a9af38c`


## Voice Pack HQ

Arquivos principais:
- `voice_hq/bin/tts-server.exe`;
- `voice_hq/models/qwen-talker-1.7b-customvoice-Q8_0.gguf`;
- `voice_hq/models/qwen-tokenizer-12hz-Q8_0.gguf`.

O workflow `Build Windows HQ Voice` deve:
1. compilar qwentts.cpp;
2. baixar os pesos Q8;
3. sintetizar Vivian em Português;
4. sintetizar Ryan em Português;
5. adicionar o pack à distribuição;
6. publicar `AGCN-Live-Voice-Windows-HQ`.

Se esse workflow estiver verde, não reimplementar voz.
