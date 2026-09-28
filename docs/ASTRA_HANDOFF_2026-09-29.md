# AGCN Live Voice — handoff para Astra 6 (29/09/2026)

## Decisão de produto congelada para o MVP

O AGCN Live Voice é o cérebro e a voz da LIVE.

O MVP NÃO terá:
- avatar/rosto IA;
- MuseTalk/lip-sync;
- player/playlist/loop de vídeo dentro do programa;
- janela 9:16 própria;
- pesquisa automática de produto;
- câmera virtual própria.

O vídeo do produto será preparado e exibido manualmente no TikTok LIVE Studio/OBS ou por outra fonte externa. O AGCN não gerencia vídeo nesta fase.

Objetivo: entregar um programa Windows que acompanhe uma TikTok LIVE, receba comentários/métricas, conduza a venda continuamente, escolha comentários relevantes, responda com naturalidade e envie a voz para o dispositivo de áudio selecionado.

## Arquitetura alvo

TikTok LIVE
-> TikTokMonitor
-> Comment Intelligence / Fusion
-> Decision Engine
-> Speech Planner
-> BrainContext factual
-> PresenterPolicy compartilhada
-> Qwen local OU provider API
-> validação factual
-> fila de fala
-> TTS local OU premium
-> dispositivo de áudio / cabo virtual
-> TikTok LIVE Studio

Produto manual -> ProductStore/ProductKnowledge -> fatos permitidos ao Brain

## O que já existe e deve ser reaproveitado

Branch base histórica: `v0.5.2-product-research`
Commit de referência: `608f840f96d00f0160910b1629ac30ccf13691c2`.

Core funcional:
- `core/tiktok_monitor.py`
- `core/product_store.py`
- `core/product_knowledge.py`
- `core/comment_intelligence.py`
- `core/comment_fusion.py`
- `core/decision_engine.py`
- `core/memory_manager.py`
- `core/silence_watchdog.py`
- `core/speech_planner.py`
- `core/persuasion_engine.py`
- `core/presenter_v2.py`
- `core/runtime.py`

Novo contrato para desktop/providers:
- `core/integration_contracts.py`
- `core/presenter_policy.py`
- `docs/PRESENTER_BRAIN_SPEC.md`

O monitor TikTok e o fluxo de produto já foram testados em LIVE real. Não reescrever do zero.

## Parte mais importante: Presenter Brain

A inteligência de fala NÃO é simplesmente "mandar comentário para uma IA".

Qwen local e qualquer provider por API devem receber a MESMA `PresenterPolicy`. O provider só troca o motor; as regras de condução da LIVE pertencem ao AGCN.

Ler obrigatoriamente:
- `docs/PRESENTER_BRAIN_SPEC.md`
- `data/presenter_dataset/behavior_v3.json`
- `core/presenter_policy.py`

A PresenterPolicy define:
- como falar;
- o que nunca inventar;
- como responder comentário;
- quais comentários têm prioridade;
- como falar proativamente;
- como evitar repetição;
- como retomar o assunto depois de interrupção;
- como usar memória;
- formato JSON de saída.

O Decision Engine continua responsável por escolher a fila/prioridade. O LLM é responsável por interpretação natural e realização da fala, não por criar fatos.

## Prioridade comercial de comentários

Ordem geral:
1. intenção clara de compra / como comprar;
2. preço, desconto, cupom, frete, disponibilidade/estoque;
3. objeção que pode impedir a compra;
4. pergunta técnica, compatibilidade e uso;
5. benefícios/diferenciais;
6. confirmação de compra;
7. comentário geral relevante;
8. saudação/emoji/conversa paralela: normalmente ignorar.

## Comportamento da fala

Pergunta:
**resposta direta -> expansão curta -> ponte para venda**

Sem comentários:
- continuar falando;
- variar fatos/tópicos;
- não repetir CTA;
- não repetir "pra quem chegou agora";
- usar normalmente um fato principal por segmento;
- respeitar memória e cooldowns.

Depois de responder:
- preservar `sales_thread`;
- continuar de onde fazia sentido;
- não reiniciar a apresentação.

## Fatos e segurança

Somente `ProductKnowledge`, `LIVE_CONDITIONS` e `ALLOWED_FACTS` são fonte da verdade.

Nunca inventar:
- função;
- compatibilidade;
- especificação;
- preço;
- desconto;
- estoque;
- frete;
- cupom;
- garantia;
- promoção;
- prazo.

Se faltar informação: assumir de forma natural que o dado não está confirmado.

## Cadastro de produto

Preservar os campos já existentes:
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

Condição da LIVE:
- regular_price
- current_price
- discount
- stock
- shipping_info
- coupon
- live_offer
- live_offer_text
- promotion_note

Não adicionar gerenciamento de vídeo ao cadastro do MVP.

## Voz/TTS

Dois providers:
1. Local/offline para funcionar sem API paga.
2. Premium/API opcional.

Requisitos:
- fila de áudio;
- prefetch;
- dispositivo de saída selecionável;
- botão testar voz;
- volume;
- fallback local;
- nenhuma chave embutida no exe.

## Desktop

Framework: Python + PySide6.

Telas:
- Dashboard
- Produto
- Configurações

Dashboard:
- status TikTok;
- produto ativo;
- presenter ON/OFF;
- comentários;
- fila/decisão;
- "Falando agora";
- Brain escolhido;
- voz escolhida;
- dispositivo de áudio.

Não implementar player de vídeo.

## Definição de pronto

Em Windows:
1. abre sem terminal para uso normal;
2. cadastra produto;
3. conecta a LIVE pelo username;
4. mostra métricas/comentários;
5. inicia presenter automático;
6. Qwen local usa PresenterPolicy e fatos reais;
7. provider API opcional usa EXATAMENTE a mesma política;
8. TTS toca no device escolhido;
9. comentário prioritário é respondido;
10. após resposta a venda continua;
11. sem comentários a IA continua falando;
12. não inventa informação ausente;
13. fallback local funciona sem API;
14. build do exe fica pronto.

