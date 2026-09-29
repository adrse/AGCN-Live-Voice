# Prompt para Astra 6 Ultra — finalizar AGCN Live Voice

Repositório privado: `adrse/AGCN-Live-Voice`
Branch: `astra-handoff-2026-09-29`

## PRIMEIRO PASSO — economize contexto

Leia SOMENTE:
1. `docs/ASTRA_MINIMAL_HANDOFF.md`
2. rode `powershell -ExecutionPolicy Bypass -File scripts\ultra_preflight.ps1`

Não reestude o projeto inteiro.
Não reescreva módulos verdes.
Abra outros arquivos somente quando um teste real apontar falha concreta.

## O que já está resolvido

Brain:
- Qwen/Ollama local;
- API opcional;
- mesma PresenterPolicy;
- BrainContext baseado no produto ativo;
- BrainResult JSON;
- validação factual;
- fallback local.

Voz:
- principal: Qwen3-TTS 1.7B CustomVoice Q8 LOCAL;
- feminina: Vivian;
- masculina: Ryan;
- instruções de estilo Brazilian Portuguese/live commerce;
- slider 0,80x–1,60x;
- fallback: Kokoro Dora/Alex;
- nenhuma API de voz necessária;
- Dashboard mostra qual motor realmente falou.

Build HQ já validado:
- workflow: `Build Windows HQ Voice`;
- run: `36510038423`;
- artifact: `AGCN-Live-Voice-Windows-HQ`;
- Vivian sintetizou Português sem API: OK;
- Ryan sintetizou Português sem API: OK;
- .exe abriu: OK;
- suíte: 85 passed, 2 warnings.

Cadastro manual do produto continua obrigatório e é a fonte da verdade.

## Arquitetura congelada

TikTok LIVE
-> comentários/métricas
-> Comment Intelligence/Fusion
-> Decision Engine
-> Speech Planner
-> produto ativo + memória
-> PresenterPolicy
-> Qwen local OU API
-> BrainResult JSON
-> validação factual
-> VoiceService
-> Qwen3-TTS HQ local
-> fallback Kokoro
-> dispositivo/VB-CABLE
-> TikTok LIVE Studio.

## Não alterar

- sem avatar/MuseTalk;
- sem player de vídeo no AGCN;
- vídeo fica no TikTok LIVE Studio/OBS;
- não usar OpenAI/ElevenLabs para voz principal;
- API serve apenas para melhorar a inteligência;
- Qwen e API usam a mesma política;
- não inventar preço, estoque, frete, cupom, garantia, compatibilidade ou especificações;
- não colocar secrets no repo/exe/config público.

## Missão de amanhã

Não desenvolver novamente o que já está verde.

Validar no PC real:
1. Ollama + `qwen3:4b`;
2. produto cadastrado;
3. Qwen fala usando fatos do produto;
4. Vivian e Ryan HQ realmente tocam;
5. medir latência do Qwen3-TTS no hardware alvo;
6. confirmar que Dashboard mostra Qwen HQ, não fallback;
7. selecionar VB-CABLE;
8. confirmar áudio chegando ao TikTok LIVE Studio;
9. conectar a uma LIVE real;
10. validar comentários prioritários;
11. validar retomada da venda após resposta;
12. testar API opcional apenas como Brain;
13. corrigir somente falhas concretas;
14. entregar o programa final.

Se o hardware não sustentar Qwen3-TTS 1.7B em latência aceitável, NÃO remova a arquitetura HQ. Documente a limitação e use o fallback automático já existente.

## Saída

Entregar somente:
- executável/pacote final;
- testes reais que passaram;
- latência observada;
- dependências externas necessárias;
- pendências comprovadas.

Não produzir revisão teórica longa.
