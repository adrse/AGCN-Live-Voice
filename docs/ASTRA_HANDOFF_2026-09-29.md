# AGCN Live Voice — handoff para Astra 6 (29/09/2026)

## Decisão final do MVP

O AGCN Live Voice é o cérebro e a voz da LIVE.

Fora do MVP:
- avatar/rosto IA e MuseTalk;
- player/playlist/loop de vídeo dentro do AGCN;
- janela 9:16 própria;
- câmera virtual;
- pesquisa automática de produto.

O vídeo do produto fica no TikTok LIVE Studio/OBS. O AGCN acompanha a LIVE, recebe comentários/métricas, conduz a venda continuamente e envia a voz para o dispositivo de áudio escolhido.

## Arquitetura congelada

TikTok LIVE
-> TikTokMonitor
-> Comment Intelligence / Fusion
-> Decision Engine
-> Speech Planner
-> BrainContext factual
-> PresenterPolicy compartilhada
-> Qwen/Ollama local OU API
-> BrainResult JSON
-> validação factual
-> fila
-> TTS
-> dispositivo/VB-CABLE
-> TikTok LIVE Studio

Produto manual -> ProductStore -> BrainContext -> ALLOWED_FACTS.

## Implementado em 28/09

Além do core histórico, agora existem:

- `core/model_transports.py`
  - `OllamaTransport` para Qwen local em `/api/chat`;
  - JSON Schema/Structured Output;
  - `OpenAIResponsesTransport` para Responses API;
  - `OpenAICompatibleChatTransport` para outros providers compatíveis.

- `core/brain_factory.py`
  - escolhe provider por configuração;
  - Qwen local é padrão;
  - API pode cair automaticamente para Qwen local;
  - secrets vêm de variável de ambiente, nunca do exe/repo.

- `core/brain_context_builder.py`
  - separa PRODUCT e LIVE_CONDITIONS;
  - transforma somente campos realmente cadastrados em `ALLOWED_FACTS`;
  - cadastro do produto é a fonte factual da LIVE.

- `core/presenter_v3.py`
  - reaproveita Comment Intelligence, Fusion, Decision Engine, Speech Planner, Memory e Watchdog;
  - chama o Brain real para resposta e fala proativa;
  - registra fatos usados e continuidade;
  - comentário relevante vira missão para o Brain, não prompt solto.

- `core/runtime.py`
  - aceita `brain_provider` ou `brain_config`;
  - sem configuração mantém V2 para compatibilidade;
  - com configuração usa PresenterV3/Qwen/API.

- `scripts/test_brain.py`
  - laboratório manual sem precisar iniciar uma LIVE;
  - usa produto ativo do ProductStore.

- testes novos:
  - `tests/test_model_transports.py`
  - `tests/test_brain_context_builder.py`
  - `tests/test_brain_factory.py`
  - `tests/test_presenter_v3.py`

## Regra central da inteligência

Qwen e API recebem a MESMA `PresenterPolicy`.

O modelo NÃO escolhe livremente os fatos. O cadastro do produto fornece:
- nome, marca, modelo, categoria;
- descrição;
- benefícios;
- problemas resolvidos;
- diferenciais;
- itens inclusos;
- compatibilidade;
- tamanho;
- bateria;
- uso;
- garantia;
- limitações;
- informações adicionais.

Condições da LIVE:
- preço regular;
- preço atual;
- desconto;
- estoque;
- frete;
- cupom;
- oferta;
- texto da oferta;
- observação promocional.

`ALLOWED_FACTS` é gerado desses campos. Se o Brain disser que usou um fato, `used_facts` deve copiar exatamente o item correspondente. O orquestrador rejeita `used_facts` não autorizados.

## Comportamento obrigatório

Pergunta:
resposta direta -> expansão curta -> ponte para venda.

Sem comentário:
- continuar vendendo;
- variar tópico;
- usar produto ativo;
- respeitar memória;
- evitar repetição de fato/CTA;
- não depender do chat para continuar.

Depois de comentário:
- responder;
- não reiniciar apresentação;
- manter/atualizar `next_sales_thread`;
- voltar naturalmente à venda.

Nunca inventar preço, estoque, frete, cupom, garantia, função, compatibilidade ou especificação.

## Configuração

`desktop/config.example.json` agora contém:
- provider do Brain;
- Ollama URL/model/timeout/temperatura;
- API URL/model/variável de ambiente;
- fallback local;
- retries.

OpenAI: chave esperada em `OPENAI_API_KEY`.
Nenhuma chave deve ser gravada no repositório.

## Teste manual de Brain

Com produto ativo:

```
python scripts/test_brain.py --provider qwen_local --proactive
python scripts/test_brain.py --provider qwen_local --comment "quanto custa?"
python scripts/test_brain.py --provider openai --comment "pega internet?"
```

Para OpenAI, definir `OPENAI_API_KEY` antes.

## O que Astra 6 deve fazer amanhã

Prioridade 1:
- auditar o novo Brain;
- rodar toda a suíte de testes;
- corrigir incompatibilidades reais;
- testar Ollama/Qwen de ponta a ponta em Windows;
- testar API real;
- integrar PresenterV3 como modo principal do desktop.

Prioridade 2:
- implementar TTS local;
- implementar TTS premium/API opcional;
- fila/prefetch de áudio;
- saída de áudio selecionável;
- VB-CABLE;
- Testar Voz;
- fallback TTS local.

Prioridade 3:
- terminar telas Dashboard, Produto e Configurações;
- ligar produto real, TikTok, Brain e áudio;
- testar LIVE real;
- empacotar .exe com PyInstaller.

## Pronto significa

1. programa Windows abre sem terminal;
2. produto é cadastrado/ativado;
3. conecta TikTok por username;
4. recebe métricas/comentários;
5. PresenterV3 fala continuamente;
6. Qwen local funciona sem chave;
7. API usa exatamente a mesma PresenterPolicy;
8. pergunta relevante interrompe a sequência no momento apropriado;
9. resposta usa apenas fatos cadastrados;
10. após resposta a venda continua;
11. TTS toca no device escolhido;
12. VB-CABLE entrega áudio ao TikTok LIVE Studio;
13. falha da API cai para local;
14. secrets não entram no exe/repo;
15. build Windows fica pronto.
