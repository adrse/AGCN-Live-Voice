# AGCN Live Voice — plano de 3 níveis de voz

Estado: decisão de produto registrada em 29/09/2026.

## Objetivo

Oferecer três experiências de voz sem mudar as regras comerciais do AGCN.
O Presenter continua sendo o maestro da LIVE: decide se a próxima ação é
responder comentário, falar do produto, ancorar preço, usar escassez real,
retomar tópico, fazer CTA etc.

A interface deve sempre conseguir mostrar:
- ação atual;
- próxima ação planejada;
- comentário escolhido, quando houver;
- tópico/tática;
- estilo vocal;
- provider de voz ativo.

Nenhum provider recebe autonomia para ignorar a fila/scheduler do AGCN.

## Nível 1 — Local HQ / Qwen3-TTS

Uso:
- padrão sem custo por API;
- Vivian ou Ryan;
- funciona offline depois de instalado;
- fallback Kokoro.

Fluxo:
Presenter -> BrainResult validado -> VoiceJob -> direção expressiva -> Qwen3-TTS.

A direção expressiva é dinâmica por fala e vem de `core/voice_expression.py`.
Velocidade continua configurável separadamente.

## Nível 2 — Gemini Premium TTS

Planejado:
- Gemini TTS via API;
- foco em interpretação, emoção, sotaque e baixa latência;
- recebe o MESMO texto aprovado pelo Presenter;
- recebe também o estilo vocal planejado pelo AGCN;
- se API falhar, pode cair para Qwen local.

Fluxo recomendado:
Presenter -> BrainResult validado -> VoiceJob -> direção expressiva -> Gemini TTS -> AudioSink.

A API key deve ficar em secret store/ambiente, nunca no Git/config distribuído.

## Nível 3 — OpenAI Live / Realtime

Este nível é diferente de um TTS comum porque o modelo de voz também possui
capacidade conversacional.

Mesmo assim, a arquitetura do AGCN deve permanecer externa e visível.

### Regra

O modelo OpenAI NÃO conduz a LIVE sozinho.

O AGCN continua decidindo:
1. qual comentário merece resposta;
2. quando entrar em modo produto;
3. qual fato é permitido;
4. qual tática comercial usar;
5. qual é a próxima ação;
6. quando deve falar.

A sessão de voz recebe um TurnPlan estruturado com:
- action;
- approved_speech ou missão restrita;
- allowed_facts;
- comment;
- topic;
- tactic;
- voice_style;
- priority;
- sales_thread.

### Modo recomendado para produção

`strict_speech`:
- AGCN/Brain gera e valida o texto;
- OpenAI Live apenas interpreta/fala o texto;
- máxima previsibilidade factual;
- fila e próxima ação continuam totalmente visíveis.

### Modo experimental

`guided_agent`:
- AGCN fornece missão + fatos permitidos;
- o modelo pode formular a resposta dentro desse limite;
- exige monitoramento de transcript/tool calls e guardrails adicionais;
- não deve ser o padrão inicial porque o áudio pode começar antes de uma
  validação textual completa.

## Fallback sugerido

Quando o usuário escolher provider por API:

Gemini Premium -> Qwen HQ -> Kokoro

ou

OpenAI Live -> Qwen HQ -> Kokoro

A LIVE não deve ficar muda por indisponibilidade de uma API.

## Próximo trabalho

1. Finalizar/validar Qwen expressivo.
2. Criar contrato provider-neutro de VoiceTurn/TurnPlan.
3. Implementar Gemini Premium TTS.
4. Implementar OpenAI Live/Realtime em strict_speech.
5. Só depois avaliar guided_agent.
6. Expor no Windows as três opções e o estado atual/próximo da fila.
