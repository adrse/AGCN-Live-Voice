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

Implementado:
- Gemini 3.8 Flash-Lite TTS como opção rápida/econômica;
- Gemini 3.8 Flash TTS como opção de máxima qualidade;
- integração via Gemini Interactions API;
- texto aprovado pelo Presenter é enviado como transcrição literal;
- estilo vocal vai em speech_metadata.style;
- Kore é o perfil feminino padrão e Puck o masculino padrão;
- velocidade final continua obedecendo ao slider do AGCN;
- falha/ausência de API cai automaticamente para Qwen HQ e depois Kokoro;
- GEMINI_API_KEY fica no secret store/ambiente, nunca no Git/config distribuído.

Fluxo:
Presenter -> BrainResult validado -> VoiceJob -> direção expressiva ->
Gemini 3.8 TTS -> AudioSink.

Fallback:
Gemini -> Qwen3-TTS HQ -> Kokoro.

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

1. Validar acusticamente Qwen expressivo no Windows.
2. Validar Gemini real com API key e comparar Flash-Lite vs Flash.
3. Criar/fechar contrato provider-neutro de VoiceTurn/TurnPlan.
4. Implementar OpenAI Live/Realtime em strict_speech.
5. Só depois avaliar guided_agent.
6. Refinar no Windows a comparação A/B dos três motores.
