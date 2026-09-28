# Especificação técnica — MVP Desktop AGCN Live Voice

## Estados

Presenter: STOPPED | STARTING | RUNNING | PAUSED | ERROR
TikTok: DISCONNECTED | CONNECTING | LIVE | ENDED | ERROR
Brain: LOCAL_QWEN | API
TTS: LOCAL | PREMIUM_API

## Pipeline

1. TikTok Monitor recebe eventos.
2. Comentários são deduplicados/normalizados.
3. Comment Intelligence estima intenção/relevância.
4. Comment Fusion agrupa quando necessário.
5. Decision Engine escolhe prioridade.
6. Speech Planner cria missão e tópico.
7. ProductKnowledge/SalesGuard monta fatos permitidos.
8. BrainContext é criado.
9. `PresenterPolicy` + BrainContext vão para Qwen ou API.
10. Saída JSON é parseada.
11. Validator/SalesGuard confere alegações sensíveis.
12. Speech Queue agenda fala.
13. TTS gera áudio.
14. AudioSink toca no device escolhido.
15. Memory registra fala/fatos/tópico/CTA.
16. Após resposta, retoma `sales_thread`.

## Regra arquitetural crítica

Nenhum provider pode ter comportamento próprio solto.

Qwen e API devem usar:
- `core/presenter_policy.build_system_instruction()`
- `core/presenter_policy.build_turn_payload(context)`
- o mesmo schema de `BrainResult`

Assim, trocar provider NÃO muda a forma como a LIVE é conduzida.

## Scheduler

Workers/async:
- TikTok;
- Brain;
- TTS;
- playback.

Duas filas:
- `priority_queue`: compra/preço/objeção/pergunta relevante;
- `proactive_queue`: fala preparada para evitar silêncio.

Quando chega prioridade:
- descartar/cancelar proativos ainda não iniciados;
- terminar o segmento atual;
- responder;
- retomar `sales_thread`.

## BrainContext

```json
{
  "mode": "comment_reply|proactive",
  "product": {},
  "live_conditions": {},
  "comment": {"id":"","username":"","text":""},
  "decision": {"intent":"","priority":0},
  "recent_comments": [],
  "recent_speeches": [],
  "recent_facts": [],
  "sales_thread": "",
  "planner_topic": "",
  "allowed_facts": []
}
```

## BrainResult

```json
{
  "speech": "...",
  "topic": "...",
  "used_facts": ["..."],
  "needs_fact": false,
  "next_sales_thread": "..."
}
```

Texto livre direto do LLM para o TTS é proibido.

## Validação factual

Regras reforçadas:
- números/preço devem existir no contexto;
- escassez exige estoque real;
- desconto/promoção exige condição real;
- garantia exige warranty;
- compatibilidade exige dado correspondente;
- se faltou fato: responder sem inventar e marcar `needs_fact=true`.

Falha:
1. retry curto;
2. fallback seguro/determinístico.

## Qwen local

- Ollama local;
- endpoint/modelo configurável;
- botão Testar Qwen;
- timeout;
- mesma PresenterPolicy;
- streaming opcional.

## API

- provider/modelo configurável;
- chave fora do Git;
- mesma PresenterPolicy;
- saída estruturada;
- timeout/fallback;
- nenhuma chave no exe.

## TTS

Local:
- offline;
- WAV/PCM;
- voz configurável.

Premium:
- opcional;
- provider/voz configurável;
- fallback local.

## Áudio Windows

- listar devices;
- selecionar;
- persistir escolha;
- botão teste;
- pensado para VB-CABLE/virtual cable;
- AGCN não precisa criar driver.

## Persistência

`%APPDATA%/AGCN Live Voice/config.json`
`%APPDATA%/AGCN Live Voice/data/`

## Empacotamento

PyInstaller:
- Windows;
- sem console;
- ícone/assets;
- sem secrets;
- script de build no repositório.

