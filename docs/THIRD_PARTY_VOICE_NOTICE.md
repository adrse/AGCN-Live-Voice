# Componentes de terceiros — voz local AGCN

A implementação local de voz usa componentes de terceiros.

## Kokoro-82M
- função: modelo neural TTS;
- modelo original: hexgrad/Kokoro-82M;
- licença indicada pelo projeto: Apache-2.0.

## kokoro-onnx
- função: inferência ONNX do Kokoro;
- projeto: thewh1teagle/kokoro-onnx;
- licença indicada pelo projeto: MIT.

## ONNX Runtime
- função: execução do modelo neural local;
- licença do projeto: MIT.

## eSpeak NG / phonemizer
- função: fonemização local necessária para PT-BR;
- são componentes distribuídos como dependências do stack Kokoro;
- possuem obrigações de licença próprias, incluindo componentes GPL.

## Antes de distribuição comercial

Antes de distribuir o AGCN Live Voice comercialmente/fechado:
1. revisar as obrigações das licenças de todos os componentes;
2. incluir avisos/licenças exigidos no instalador/pacote;
3. confirmar a forma adequada de distribuição dos componentes GPL;
4. não remover avisos de copyright/licença.

Esta pendência jurídica não impede testes técnicos do MVP, mas deve ser resolvida antes de distribuição comercial.
