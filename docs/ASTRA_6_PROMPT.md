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
9. `core/comment_selection_policy.py`
10. `core/runtime.py`
11. `desktop/config.example.json`
12. `docs/DESKTOP_MVP_SPEC.md`
13. `docs/ACCEPTANCE_TESTS_MVP.md`
14. testes existentes.

MISSÃO: entregar o programa Windows funcional **AGCN Live Voice — Sua voz inteligente para vender ao vivo.**

## Decisões que NÃO devem ser revertidas

- sem avatar/MuseTalk;
- sem player/playlist de vídeo no AGCN;
- vídeo fica no TikTok LIVE Studio/OBS;
- cadastro manual do produto é essencial;
- Qwen/Ollama local é o Brain padrão;
- API é alternativa opcional;
- Qwen e API usam a MESMA PresenterPolicy;
- nenhum provider pode ter prompt comercial próprio;
- nenhum texto bruto de LLM vai direto ao TTS;
- nenhum secret embutido;
- TTS local padrão + premium opcional;
- áudio sai no device escolhido/VB-CABLE.

## O que já foi implementado e deve ser auditado, não refeito do zero

- Ollama/Qwen real em `core/model_transports.py`;
- OpenAI Responses API com Structured Output;
- provider genérico OpenAI-compatible;
- factory/fallback em `core/brain_factory.py`;
- fatos canônicos derivados do cadastro em `core/brain_context_builder.py`;
- Presenter V3 com comentários, proatividade, memória e continuidade;
- runtime capaz de receber Brain real;
- script `scripts/test_brain.py`;
- testes dos transportes/contexto/fallback/Presenter V3.

## Regras funcionais

Fluxo:
TikTok -> filtro/prioridade -> decisão -> Speech Planner -> produto ativo + memória -> PresenterPolicy -> Qwen/API -> BrainResult JSON -> validação -> TTS -> áudio.

O Brain deve:
- falar continuamente;
- responder comentários prioritários;
- responder direto antes de expandir;
- usar apenas o produto ativo e condições da LIVE;
- não inventar;
- variar assunto;
- evitar repetição;
- preservar `sales_thread`;
- retomar venda depois da resposta.

`used_facts` deve copiar exatamente fatos de `ALLOWED_FACTS`.

## Trabalho de amanhã

1. Rode toda a suíte e corrija qualquer regressão.
2. Teste Qwen/Ollama real no Windows, incluindo JSON estruturado.
3. Teste OpenAI Responses API real e fallback.
4. Faça testes de factualidade e comentários.
5. Integre PresenterV3 definitivamente ao desktop.
6. Implemente TTS local funcional.
7. Implemente TTS/API premium opcional.
8. Implemente fila/prefetch/playback e device de áudio.
9. Integre VB-CABLE.
10. Termine UI real de Dashboard/Produto/Configurações.
11. Teste com TikTokMonitor real.
12. Gere e valide o .exe.

Não gaste tempo com vídeo, avatar, mobile, pagamentos ou pesquisa automática.

Ao terminar entregue:
- arquivos alterados;
- testes executados e resultados;
- Qwen testado;
- API testada;
- TTS/device testados;
- pendências reais;
- comando/caminho de build do exe.
