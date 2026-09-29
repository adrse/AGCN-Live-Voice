# AGCN Live Voice — instalador completo offline

## Regra de distribuição

O cliente final não instala Ollama, Python, Qwen ou o motor de voz manualmente.

O pacote completo do Windows instala, em uma única experiência:

- aplicativo AGCN Live Voice;
- Presenter Brain local Qwen3-4B Q4_K_M;
- runtime llama.cpp privado do AGCN;
- Qwen3-TTS HQ com Vivian e Ryan;
- Kokoro PT-BR como fallback;
- Microsoft Visual C++ Runtime necessário aos motores nativos;
- atalhos e desinstalador.

Depois de instalado, Brain e voz local funcionam sem API e sem download adicional.

## Brain local

Fluxo:

TikTok LIVE -> Presenter -> AGCN Local Brain -> llama.cpp -> Qwen3-4B -> validação factual -> voz.

Arquivos esperados dentro da distribuição:

`_internal/brain_local/bin/llama-server.exe`
`_internal/brain_local/models/Qwen3-4B-Q4_K_M.gguf`

O AGCN inicia e encerra o servidor local automaticamente. O serviço escuta apenas em `127.0.0.1`, porta padrão `18766`.

Provider padrão: `agcn_local`.

Configurações antigas com `qwen_local` continuam compatíveis e passam a apontar para o Brain embutido. `ollama` permanece apenas como compatibilidade técnica legada, não como requisito do cliente.

## Voz local

O mesmo instalador contém:

- Qwen3-TTS 1.7B CustomVoice Q8;
- Vivian;
- Ryan;
- Kokoro Dora/Alex como fallback.

Nenhum motor de voz precisa ser instalado separadamente.

## Build

Workflow:

`.github/workflows/build-windows-complete.yml`

O workflow:

1. executa a suíte;
2. prepara Kokoro;
3. compila qwentts.cpp;
4. baixa os pesos HQ;
5. obtém o runtime Windows x64 do llama.cpp;
6. baixa o Qwen3-4B Q4_K_M;
7. inicializa o Brain local e executa uma geração real;
8. sintetiza Vivian e Ryan;
9. gera o aplicativo PyInstaller;
10. embute Brain e Voice Pack;
11. testa o executável;
12. compila o instalador Inno Setup;
13. publica `AGCN-Live-Voice-Complete-Installer`.

Como o pacote é grande, o Inno Setup pode gerar `AGCN-Live-Voice-Setup.exe` acompanhado de partes `.bin`. Todas ficam no mesmo pacote baixado. O cliente apenas executa o Setup; não executa as partes manualmente.

## Componentes externos que não fazem parte do aplicativo

TikTok LIVE Studio/OBS e drivers de áudio virtual são integrações do ambiente do usuário. Eles não são silenciosamente redistribuídos dentro do AGCN sem validação de licença/driver.

O Brain e as vozes do AGCN, por outro lado, fazem parte do pacote completo.
