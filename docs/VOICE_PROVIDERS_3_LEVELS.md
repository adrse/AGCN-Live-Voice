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

## Nível 3 — OpenAI Live / GPT-Live 1

O motor principal desta opção é `gpt-live-1`, usado para a experiência vocal
mais natural/expressiva. A inteligência comercial continua fora dele.

### Regra

O modelo OpenAI NÃO conduz a LIVE sozinho.

O AGCN continua decidindo:
1. qual comentário merece resposta;
2. quando entrar em modo produto;
3. qual fato é permitido;
4. qual tática comercial usar;
5. qual é a próxima ação;
6. quando deve falar.

### Modo implementado — strict_speech

Fluxo:
Presenter -> BrainResult validado -> VoiceJob -> GPT-Live 1 -> transcript guard
-> AudioSink.

- AGCN/Brain gera e valida o texto;
- GPT-Live recebe uma instrução de atuação + o texto aprovado;
- o áudio é bufferizado antes de tocar;
- a transcrição devolvida pelo GPT-Live é normalizada e comparada ao texto
  aprovado;
- se o modelo alterar a fala, o áudio é bloqueado;
- erro ou divergência aciona fallback OpenAI Live -> Qwen HQ -> Kokoro;
- Marin é o perfil feminino padrão e Cedar o masculino;
- cada fala usa uma sessão curta e independente nesta primeira versão, evitando
  contaminação de contexto entre falas;
- fila, ação atual, próxima ação e estilo continuam pertencendo ao AGCN.

### Modo experimental — guided_agent

Ainda não implementado:
- AGCN fornece missão + fatos permitidos;
- GPT-Live pode formular a fala dentro desse limite;
- exige sessão persistente, transcript/tool monitoring e guardrails adicionais;
- só deve ser habilitado depois da validação do modo controlado.

## Fallback sugerido

Quando o usuário escolher provider por API:

Gemini Premium -> Qwen HQ -> Kokoro

ou

OpenAI Live -> Qwen HQ -> Kokoro

A LIVE não deve ficar muda por indisponibilidade de uma API.

## Próximo trabalho

1. Validar acusticamente Qwen expressivo no Windows.
2. Validar Gemini real com API key e comparar Flash-Lite vs Flash.
3. Validar GPT-Live 1 real com OPENAI_API_KEY no modo strict_speech.
4. Comparar Qwen vs Gemini vs GPT-Live usando o mesmo texto e estilo.
5. Só depois avaliar guided_agent/sessão persistente.
6. Refinar a interface com comparação A/B dos três motores.

## Organização da interface

A interface desktop separa operação de configuração:

- **Dashboard**: andamento da apresentação, fala atual, fila/decisão, comentários e resumo de voz;
- **Voz e áudio**: configuração completa dos três providers, perfil, velocidade, expressividade, estilo, chaves, teste e device;
- **Configurações**: Presenter Brain e diagnóstico geral.

O card de Voz e áudio do Dashboard é somente leitura operacional e possui `Ajustes avançados`, que navega para a página dedicada. Isso evita sobrecarregar o Dashboard sem esconder o provider/estilo que está ativo.
