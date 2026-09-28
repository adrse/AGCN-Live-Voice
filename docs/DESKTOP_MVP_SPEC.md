# Especificação técnica — MVP Desktop AGCN Live Voice

## Estados principais

Presenter: STOPPED | STARTING | RUNNING | PAUSED | ERROR
TikTok: DISCONNECTED | CONNECTING | LIVE | ENDED | ERROR
Brain: LOCAL_QWEN | API
TTS: LOCAL | PREMIUM_API
Media: STOPPED | PLAYING | PAUSED

## Pipeline de fala

1. Evento TikTok entra no monitor.
2. Comentário é normalizado/deduplicado.
3. Inteligência classifica relevância e prioridade.
4. Decision Engine decide COMMENT_REPLY ou PROACTIVE.
5. Speech Planner cria missão e pacote factual.
6. Brain gera texto natural.
7. Validador confere afirmações sensíveis contra ProductKnowledge.
8. Speech Queue agenda o segmento.
9. TTS renderiza.
10. Audio Output reproduz no device configurado.
11. Memory registra tópico, fatos e CTA usados.
12. Se era resposta, retoma sales_thread anterior.

## Scheduler recomendado

Não bloquear a UI. Usar workers/asyncio para:
- TikTok monitor;
- brain generation;
- TTS generation;
- playback;
- media playback.

A UI só observa estados e envia comandos.

Manter duas filas:
- priority_queue: comentários relevantes/compra/objeção/pergunta;
- proactive_queue: fala preparada para evitar silêncio.

Ao chegar item prioritário:
- cancelar falas proativas ainda não iniciadas;
- não cortar áudio no meio da palavra;
- responder após o segmento atual;
- retomar contexto.

## Contrato Brain

Entrada mínima:
```json
{
  "mode": "comment_reply|proactive",
  "product": {},
  "live_conditions": {},
  "comment": {"id":"","username":"","text":""},
  "recent_comments": [],
  "recent_speeches": [],
  "recent_facts": [],
  "sales_thread": "",
  "planner_topic": "",
  "allowed_facts": []
}
```

Saída:
```json
{
  "speech": "...",
  "topic": "...",
  "used_facts": ["..."],
  "needs_fact": false,
  "next_sales_thread": "..."
}
```

O provider local Qwen e o provider API implementam o mesmo contrato.

## Prompt comportamental do Brain

Você é uma pessoa apresentadora brasileira de live commerce. Fale como alguém ao vivo, de forma rápida, natural, comercial e sem linguagem de sistema. Quando houver pergunta, responda a dúvida logo no começo e depois conecte a resposta a um benefício ou uso real do produto. Quando não houver pergunta, continue vendendo o produto variando benefícios, uso, diferenciais, itens inclusos, preço/valor, confiança e CTA. Não repita a mesma ideia continuamente. Só use fatos presentes em ALLOWED_FACTS/LIVE_CONDITIONS. Nunca invente função, compatibilidade, estoque, preço, desconto, frete, garantia ou promoção. Se faltar uma informação, diga naturalmente que essa informação não está cadastrada. Escassez somente com estoque/oferta real fornecida. Entregue somente o JSON solicitado.

## Validação factual

Antes do TTS:
- números e preço devem existir no pacote;
- palavras de escassez ("últimas", "acabando", "só restam") exigem stock;
- promoção/desconto exigem current_price/discount/live_offer;
- garantia exige warranty;
- compatibilidade técnica exige compatibility ou additional_info correspondente.

Em caso de saída inválida:
1. retry curto com motivo;
2. se falhar, usar resposta segura/determinística do ProductKnowledge.

## Qwen local

Provider recomendado para MVP: Ollama local.
- endpoint configurável, default localhost;
- nome do modelo configurável;
- não assumir modelo instalado;
- botão "Testar Qwen";
- timeout e fallback;
- streaming opcional, não obrigatório para primeira versão.

## TTS local

Provider offline deve:
- aceitar texto;
- gerar WAV/PCM;
- funcionar sem internet;
- permitir escolher voz instalada/modelo;
- expor erro claro se voz não estiver instalada.

## TTS premium

Provider API deve ser opcional.
- chave fora do repo;
- modelo/voz configuráveis;
- teste de voz;
- timeout;
- fallback opcional para local.

## Saída de áudio

Windows:
- listar devices de saída;
- permitir escolher device;
- salvar seleção;
- recomendado usar VB-CABLE no MVP;
- não exigir driver criado pelo AGCN.

## Media player

Para reduzir dependências, usar Qt Multimedia/QMediaPlayer quando estável no ambiente final. Se codec gerar problema, usar mpv/ffmpeg backend.

OutputWindow:
- frameless;
- sempre 9:16;
- background preto;
- vídeo com aspect fill/fit configurável;
- sem botões;
- tecla Esc fecha;
- janela nomeada de modo estável para captura no TikTok Studio.

## Persistência

Config local sugerida:
`%APPDATA%/AGCN Live Voice/config.json`

Dados:
`%APPDATA%/AGCN Live Voice/data/`

Mídia pode permanecer na origem e ser referenciada por path; oferecer opção futura de copiar para biblioteca interna.

## Empacotamento

MVP: PyInstaller.
- build Windows;
- ícone AGCN;
- sem console;
- incluir assets;
- não incluir API keys;
- documentação simples de instalação de Ollama e VB-CABLE como dependências externas opcionais/recomendadas.

