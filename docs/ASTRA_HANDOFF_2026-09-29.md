# AGCN Live Voice — handoff para Astra 6 (29/09/2026)

## Decisão de produto congelada para o MVP

O MVP NÃO terá avatar/rosto IA. MuseTalk fica fora da rota crítica. A transmissão visual será um ou mais vídeos reais do produto, preferencialmente mãos demonstrando o produto, reproduzidos em loop/playlist. A inteligência e a voz continuam automáticas.

Objetivo: entregar um programa Windows que consiga acompanhar uma TikTok LIVE, receber comentários e métricas, falar continuamente sobre um produto cadastrado manualmente, responder comentários relevantes e retomar a venda sem silêncio longo.

## Arquitetura alvo

TikTok LIVE -> TikTokMonitor -> contexto da LIVE + produto -> memória -> inteligência de comentários -> Decision Engine -> Presenter Brain -> fila de falas -> TTS -> dispositivo de áudio selecionado -> microfone virtual -> TikTok LIVE Studio

Em paralelo:

Cadastro manual do produto -> ProductStore/ProductKnowledge
Vídeos do produto -> Media Playlist -> janela limpa 9:16 "AGCN Live Output" -> Captura de Janela no TikTok LIVE Studio

MVP não precisa criar driver de câmera virtual. O TikTok LIVE Studio captura a janela 9:16 do AGCN. O áudio sai para um dispositivo virtual selecionável (ex.: VB-CABLE). No TikTok LIVE Studio o usuário escolhe o dispositivo correspondente como microfone.

## O que já existe e deve ser reaproveitado

Branch base: `v0.5.2-product-research`, commit de referência `608f840f96d00f0160910b1629ac30ccf13691c2`.

Core funcional já disponível:
- `core/tiktok_monitor.py`: monitoramento TikTok LIVE.
- `core/product_store.py`: cadastro/persistência de produto.
- `core/product_knowledge.py`: resolução factual do produto.
- `core/comment_intelligence.py`: classificação inicial de comentários.
- `core/comment_fusion.py`: fusão de comentários.
- `core/decision_engine.py`: prioridade/decisão.
- `core/memory_manager.py`: memória de fala, fatos e cadência.
- `core/silence_watchdog.py`: evita silêncio prolongado.
- `core/speech_planner.py`: planejamento de fala.
- `core/persuasion_engine.py`: realização atual baseada em regras.
- `core/presenter_v2.py`: orquestração do presenter.
- `core/runtime.py`: integração monitor + presenter.
- `backend/app_v054.py` e `test_web/index_v054.html`: ambiente web temporário de teste.

O monitor TikTok e o fluxo de produto já foram validados em LIVE real. Não reescrever do zero sem necessidade.

## O que NÃO deve consumir tempo agora

- MuseTalk, lip-sync, avatar, face animation ou talking head.
- Pesquisa automática de produto por URL/Lens/TikTok Shop.
- Driver próprio de câmera virtual.
- App mobile.
- Sistema de pagamento/licenciamento.
- Refazer o monitor TikTok que já funciona.
- Refazer o ProductStore sem necessidade.

Arquivos antigos de pesquisa automática de produto podem permanecer no repositório, mas não fazem parte do MVP.

## Cadastro de produto

Produto é cadastrado manualmente. Preservar os campos existentes:
- product_url opcional
- name, brand, model, category
- description
- key_benefits
- problems_solved
- differentials
- included_items
- compatibility
- size_info
- battery_info
- usage_info
- warranty
- limitations
- additional_info
- image_url

Condição de LIVE:
- regular_price
- current_price
- discount
- stock
- shipping_info
- coupon
- live_offer
- live_offer_text
- promotion_note

Adicionar ao desktop uma lista de arquivos de mídia do produto:
- 1..N vídeos locais
- ordem
- ativo/inativo
- loop
- duração opcional/trim futuro

## Brain

Primeira opção: Qwen local via Ollama. O programa deve funcionar sem API paga.

Segunda opção opcional: provider por API para maior qualidade. Deve ser configurável e desacoplado. Nunca embutir chave secreta no código/exe.

O Brain recebe:
- ficha factual do produto
- condição atual da LIVE
- comentário atual ou missão proativa
- últimos comentários relevantes
- últimas falas
- fatos usados recentemente
- último CTA
- compras/estoque/eventos recentes
- tópico de venda ativo

Saída ideal estruturada:
- speech: texto pronto para TTS
- topic
- used_facts
- answered_comment_id opcional
- needs_fact boolean
- next_sales_thread opcional

Regras invioláveis:
- não inventar informação técnica, preço, estoque, promoção, frete, garantia ou compatibilidade;
- escassez só se houver dado real;
- se não houver informação, assumir que não sabe;
- responder primeiro, depois expandir;
- português brasileiro natural e de live commerce;
- evitar frases robóticas;
- não repetir o mesmo benefício/CTA em sequência;
- não fazer recap de "quem chegou agora" repetidamente.

## Voz/TTS

Dois providers:
1. Local/offline: usar uma opção Windows simples e estável (Piper é aceitável para MVP).
2. Premium/API: adapter configurável para TTS externo/OpenAI.

Requisitos:
- fila de áudio;
- prefetch da próxima fala enquanto a atual toca;
- saída para dispositivo de áudio selecionável;
- botão testar voz;
- volume;
- velocidade se suportada;
- se provider premium falhar, cair para local quando configurado.

## Fala contínua e interrupção por comentário

O sistema não deve esperar comentário para falar.

Cadência:
- watchdog atual: alvo ~8 s, hard limit ~10 s sem nova fala;
- gerar segmentos curtos para manter naturalidade;
- enquanto TTS toca, Brain já pode preparar o próximo segmento;
- comentário prioritário entra na frente das falas proativas ainda não reproduzidas;
- de preferência terminar a frase/segmento atual e responder em seguida;
- depois retomar o tópico de venda anterior.

## Vídeo do produto

Criar janela separada e limpa, 9:16, sem controles, destinada a captura pelo TikTok LIVE Studio.

Comportamento MVP:
- reproduzir MP4/H.264 locais;
- loop contínuo;
- playlist de vários clipes;
- transição simples/corte;
- botão próximo/anterior;
- selecionar clipe ativo;
- mutar áudio original dos vídeos por padrão;
- manter reprodução mesmo quando a IA estiver respondendo comentários.

Fase posterior: o Brain pode escolher o clipe por tag (ex.: bateria, tamanho, acessórios, uso).

## Desktop

Framework definido: Python + PySide6. Evitar Electron.

Estrutura sugerida:
- `desktop/main.py`
- `desktop/main_window.py`
- `desktop/output_window.py`
- `desktop/pages/dashboard.py`
- `desktop/pages/product.py`
- `desktop/pages/settings.py`
- `desktop/widgets/live_status.py`
- `desktop/widgets/comment_feed.py`
- `desktop/widgets/speech_now.py`
- `desktop/services/audio_output.py`
- `desktop/services/media_playlist.py`
- `desktop/services/brain_service.py`
- `desktop/services/tts_service.py`

UI:
- identidade AGCN Live Voice;
- azul #0061FF, preto #0A0A0B, grafite #6B7280, cinza claro #F3F5F9;
- Dashboard;
- Produto;
- Configurações;
- status TikTok;
- produto ativo;
- presenter ON/OFF;
- comentários;
- "Falando agora";
- fila/decisão;
- seletor Brain;
- seletor voz;
- seletor dispositivo de saída;
- controle de playlist;
- botão abrir janela 9:16.

## Segurança e dados

- API keys apenas em config local segura/.env fora do Git.
- Nunca commitar chaves.
- Produto e configurações persistidos localmente.
- Logs sem tokens/chaves.
- Exe final deve poder funcionar com Qwen local + TTS local sem custo de API.

## Definição de pronto do MVP

O MVP está pronto quando, em um PC Windows:
1. abre sem terminal para uso normal;
2. cadastra produto e vídeos;
3. conecta a uma LIVE TikTok pelo username;
4. mostra viewers/likes/comentários;
5. inicia apresentação automática;
6. Qwen produz fala usando apenas fatos cadastrados;
7. TTS toca no dispositivo escolhido;
8. comentário relevante interrompe a fila proativa e é respondido;
9. após resposta, a venda continua;
10. janela 9:16 reproduz vídeos em loop;
11. TikTok LIVE Studio consegue capturar essa janela e usar o áudio pelo dispositivo virtual;
12. se não houver comentários, a IA continua falando;
13. se uma informação não existir, a IA não inventa;
14. existe fallback local sem API.

