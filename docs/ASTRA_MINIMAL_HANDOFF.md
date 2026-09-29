# Astra 6 Ultra — handoff mínimo e orientado a execução

Objetivo: gastar o mínimo possível de contexto/análise. NÃO reestude o projeto inteiro.

Repositório: adrse/AGCN-Live-Voice
Branch: astra-handoff-2026-09-29

## Estado já verificado antes do handoff

- suíte completa do repositório após os perfis de voz: **80 passed, 2 warnings**;
- build Windows via GitHub Actions: **SUCCESS**;
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

As duas vozes oficiais são LOCAIS e ficam dentro do pacote do AGCN:
- feminina: Kokoro PT-BR `pf_dora`;
- masculina: Kokoro PT-BR `pm_alex`.

O modelo ONNX e o arquivo de vozes são empacotados no ZIP/instalador. Nenhuma API é usada para gerar voz. A velocidade é controlada por slider na UI.

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
- TTS Kokoro PT-BR local é obrigatório e vem empacotado; nenhuma API é requisito de voz;
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
- sempre disponível localmente;
- Kokoro-82M PT-BR;
- Dora (feminina) e Alex (masculina);
- modelo + vozes fazem parte do pacote Windows;
- API não deve ser exigida nem oferecida como dependência para a voz principal.


## Importante sobre código legado de voz

Pode haver arquivos/classes experimentais antigos de TTS por API no histórico/árvore.
Eles NÃO fazem parte da arquitetura oficial do MVP.

Não gastar tokens integrando OpenAI TTS/ElevenLabs TTS.
A API OpenAI só interessa ao Presenter Brain.

Provider oficial de voz: `kokoro_local`.
