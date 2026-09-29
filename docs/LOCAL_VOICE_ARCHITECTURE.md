# AGCN Live Voice — arquitetura oficial de voz local

## Regra de produto

A voz NÃO depende da API de inteligência.

O AGCN precisa falar mesmo quando:
- não existe OPENAI_API_KEY;
- não existe ELEVENLABS_API_KEY;
- a internet está indisponível;
- o Windows não possui vozes SAPI adicionais.

## Motor

Kokoro-82M v1.0 via kokoro-onnx/ONNX Runtime.

Arquivos empacotados:
- models/kokoro/kokoro-v1.0.onnx
- models/kokoro/voices-v1.0.bin

O build baixa versões fixas antes do PyInstaller e inclui os dois arquivos no pacote Windows.

## Perfis oficiais PT-BR

- female_fast -> pf_dora
- male_fast -> pm_alex

Alternativa masculina existente no modelo: pm_santa. Não é o padrão do MVP.

## Velocidade

UI:
- mínimo: 0.80x
- padrão: 1.28x
- máximo: 1.60x

O Kokoro aceita faixa maior internamente; a UI restringe para uma faixa útil para LIVE commerce.

Além da velocidade do áudio, PresenterPolicy exige:
- respostas curtas;
- resposta ao comentário na primeira frase;
- pouca pausa;
- retorno imediato à venda;
- discurso proativo.

## Runtime

Brain local:
Qwen/Ollama -> BrainResult validado -> Kokoro local -> AudioSink.

Brain API:
API -> BrainResult validado -> Kokoro local -> AudioSink.

Portanto trocar o Brain NÃO troca a voz.

## Build

O workflow Windows:
1. instala kokoro-onnx;
2. baixa model/voices;
3. faz smoke import;
4. sintetiza uma frase PT-BR com Dora;
5. sintetiza uma frase PT-BR com Alex;
6. só então executa PyInstaller;
7. verifica se model/voices ficaram dentro do build;
8. abre o exe;
9. gera ZIP.

Se Dora ou Alex não sintetizarem localmente, o build deve falhar.

## Internet

Internet é necessária durante desenvolvimento/build para baixar dependências/modelo.

Depois que o usuário recebe o pacote completo:
- inferência de voz é local;
- não há request HTTP para gerar áudio.

A API permanece opcional apenas para a inteligência do Presenter Brain.

## Licenças

Antes de distribuição comercial, ler:
docs/THIRD_PARTY_VOICE_NOTICE.md
