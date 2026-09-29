# AGCN Live Voice — arquitetura oficial de voz local

## Regra de produto

A voz é independente da API de inteligência.

Sem API externa:
- Qwen/Ollama continua sendo o Brain;
- Qwen3-TTS local gera a voz;
- o usuário escolhe feminina/masculina;
- o slider controla velocidade;
- áudio segue para speakers/VB-CABLE.

## Motor principal — Qualidade Máxima

Qwen3-TTS 1.7B CustomVoice, usando qwentts.cpp/GGML.

Distribuição HQ:
- talker: `qwen-talker-1.7b-customvoice-Q8_0.gguf`;
- codec: `qwen-tokenizer-12hz-Q8_0.gguf`;
- engine: `tts-server.exe`;
- idioma: `Portuguese`;
- servidor: somente localhost;
- nenhuma chamada à internet durante síntese.

Perfis:
- `female_fast` -> Vivian;
- `male_fast` -> Ryan.

O modelo fica residente no processo local para evitar recarregamento em cada fala.

## Por que 1.7B Q8

O checkpoint 1.7B oferece maior capacidade que 0.6B e o CustomVoice suporta speakers premium. O formato Q8 reduz bastante o tamanho em disco mantendo precisão maior que Q4.

## Velocidade

UI:
- 0,80x a 1,60x;
- padrão 1,28x.

A fala é sintetizada e depois ajustada por FFmpeg/atempo para a velocidade escolhida, preservando o pitch melhor que simples resampling.

A PresenterPolicy também exige frases curtas e ritmo comercial alto.


## Direção expressiva dinâmica

O Qwen3-TTS HQ não usa mais uma única atuação fixa para toda a LIVE.

Antes de cada fala, o runtime deriva um `voice_style` dos metadados já
aprovados pelo Presenter. A camada `core/voice_expression.py` não muda o
texto nem cria fatos; ela somente orienta a interpretação vocal.

Estilos atuais:
- `sales_energy`: venda energética padrão;
- `celebratory`: compra confirmada/prova social real;
- `urgent_grounded`: urgência somente quando a escassez é sustentada;
- `price_confident`: preço/ancoragem de valor;
- `reassuring`: objeção, garantia, confiança;
- `empathetic_solution`: dor -> solução;
- `vivid_desire`: descrição, uso e visualização;
- `clear_answer`: resposta curta a comentário;
- `welcoming`: recap/entrada de público.

A instrução final combina o perfil Vivian/Ryan com o estilo daquele job. A
intensidade é configurável em `tts.qwen3_hq.expression_strength` (0.0 a 1.5)
e pode ser desligada com `tts.qwen3_hq.expressive=false`.

O `voice_style` também é colocado no estado do runtime/metadata da fila para
a interface poder mostrar como a próxima fala será interpretada.

Essa camada foi desenhada para ser reaproveitada futuramente por motores de
voz via API (Gemini/OpenAI), mantendo o Presenter como fonte de decisão.

## Fallback

Kokoro-82M PT-BR continua embutido:
- feminina: Dora;
- masculina: Alex.

É usado somente quando o pack Qwen3 HQ está ausente ou falha.

## Runtime

Brain local:
Qwen/Ollama -> BrainResult validado -> Qwen3-TTS HQ -> AudioSink.

Brain API:
API -> BrainResult validado -> Qwen3-TTS HQ -> AudioSink.

Falha/ausência do pack HQ:
Brain -> Kokoro fallback -> AudioSink.

Trocar o Brain nunca troca a arquitetura de voz.

## Build HQ

Workflow: `.github/workflows/build-windows-hq.yml`.

Ele:
1. compila qwentts.cpp no Windows;
2. baixa talker/codec Q8;
3. testa assets;
4. sintetiza Vivian em Português;
5. sintetiza Ryan em Português;
6. compila o AGCN;
7. copia o Voice Pack HQ para `_internal/voice_hq`;
8. abre o executável;
9. publica a distribuição HQ.

## Hardware

Qwen3-TTS 1.7B é mais pesado que Kokoro. CPU é o backend universal; GPU pode reduzir muito a latência. A qualidade máxima não deve ser substituída por voz pior apenas para esconder uma limitação de hardware: o Doctor deve informar quando houver fallback.

## Internet

Internet é necessária no build/instalação do Voice Pack para baixar os arquivos.

Depois de instalado:
- Qwen3-TTS roda local;
- Kokoro roda local;
- nenhuma API de voz é necessária.

## Licenças

Ver `docs/THIRD_PARTY_VOICE_NOTICE.md` antes de distribuição comercial.
