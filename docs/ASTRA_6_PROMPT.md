# Prompt para Astra 6 — construir o programa

Você está assumindo o repositório privado `adrse/AGCN-Live-Voice`.

Trabalhe na branch `astra-handoff-2026-09-29`.

Leia obrigatoriamente, nesta ordem:
1. `docs/ASTRA_HANDOFF_2026-09-29.md`
2. `docs/PRESENTER_BRAIN_SPEC.md`
3. `core/presenter_policy.py`
4. `core/comment_selection_policy.py`
5. `core/brain_orchestrator.py`
6. `data/presenter_dataset/behavior_v3.json`
7. `docs/DESKTOP_MVP_SPEC.md`
8. `docs/ACCEPTANCE_TESTS_MVP.md`
9. core existente.

MISSÃO: entregar o programa Windows funcional **AGCN Live Voice — Sua voz inteligente para vender ao vivo.**

A prioridade máxima NÃO é a interface. É a qualidade e segurança da inteligência de fala.

Decisão final:
- sem avatar;
- sem MuseTalk;
- sem player/playlist/loop de vídeo no AGCN;
- o vídeo é responsabilidade externa do TikTok LIVE Studio/OBS;
- Qwen local é o Brain padrão;
- provider API é opcional;
- Qwen e API usam a MESMA PresenterPolicy;
- TTS local padrão;
- TTS premium/API opcional;
- TikTok Monitor atual deve ser reaproveitado;
- produto manual;
- PySide6;
- áudio sai no dispositivo selecionado/VB-CABLE;
- nenhum secret embutido.

Implementação obrigatória do Brain:
1. Comment Intelligence + Decision Engine decidem o que merece resposta.
2. ProductKnowledge/SalesGuard montam fatos permitidos.
3. Speech Planner cria missão/tópico.
4. BrainContext é enviado a `PresenterPolicy`.
5. Qwen/API geram JSON `BrainResult`.
6. Validator checa fatos antes do TTS.
7. Memory registra fala/fatos/tópico.
8. Após comentário, retomar `sales_thread`.
9. Sem comentário, gerar fala proativa variada.
10. Nunca mandar texto bruto de LLM direto ao TTS.

O Brain deve:
- entender linguagem natural, gírias e erros;
- priorizar compra/preço/objeção/pergunta relevante;
- ignorar chat inútil;
- responder direto primeiro;
- continuar vendendo;
- não repetir "pra quem chegou agora";
- não repetir CTA/fato;
- não inventar nada;
- manter continuidade depois de interrupção.

Não gaste tempo com vídeo, avatar, mobile, pagamentos ou pesquisa automática.

Faça testes de ponta a ponta, incluindo Qwen local, provider API mockado, fila, fallback, segurança factual e retomada.

Ao terminar entregue:
- arquivos alterados;
- como rodar;
- dependências externas;
- testes executados;
- pendências reais;
- comando/caminho de build do exe.

