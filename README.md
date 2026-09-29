# AGCN Live Voice

Apresentador inteligente por voz para TikTok LIVE.

## Status atual

**V0.5 Presenter Behavior: ritmo de LIVE, respostas naturais e prioridade contínua para o produto.**

Nesta versão, o apresentador deixa de se comportar como chatbot. Comentários continuam sendo analisados e priorizados, mas a LIVE mantém uma linha própria de apresentação e venda do produto.

### Regras de comportamento V0.5

- no máximo 3 respostas consecutivas a comentários;
- depois disso, 30 segundos obrigatórios de apresentação do produto;
- comentários continuam entrando na fila durante essa janela, sem interromper a fala;
- quando não há pergunta para responder, a apresentadora continua falando do produto;
- linguagem curta, informal e natural;
- perguntas sem resposta conhecida são ignoradas silenciosamente;
- descrição do produto pode ser cadastrada em vários pontos independentes;
- a apresentadora usa um ponto de descrição por vez, sem ler o bloco inteiro;
- nunca expõe termos internos como "cadastro", "base de dados" ou "contexto";
- quando uma informação não está disponível, responde naturalmente sem inventar;
- perguntas repetidas são filtradas e a fila de respostas é limitada;
- a mesma lógica de ritmo deve ser reaproveitada pelos futuros modos de voz local e por API.

### Já validado no Colab

- conexão com TikTok LIVE por `@username`;
- Room ID;
- viewers;
- likes;
- comentários;
- shares;
- Product Store;
- produto ativo;
- classificação básica de comentários;
- prioridade;
- fila;
- geração de fala sugerida;
- atualização automática da interface.

## Regra de arquitetura

O projeto é dividido para que o núcleo possa ser reaproveitado no aplicativo Windows final.

```text
core/        -> lógica definitiva/reutilizável
backend/     -> ponte temporária para o site de teste
test_web/    -> interface web temporária
data/        -> dados locais e dataset do Presenter
tests/       -> testes automáticos
desktop/     -> será criado na fase final com PySide6
```

O site e o Railway são apenas ferramentas temporárias de teste. O produto final será um programa Windows local.

## Executar localmente

```bash
python -m pip install -r requirements.txt
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Depois abra `http://localhost:8000`.

## Railway

Start command:

```bash
uvicorn backend.app:app --host 0.0.0.0 --port $PORT
```

## Próximas evoluções

- integração do planejador com voz local no aplicativo Windows;
- integração opcional com API de voz/modelo;
- a interface Windows deverá consumir o mesmo campo `description_points` usado pelo núcleo e pelo teste web;
- Memory Manager;
- Comment Fusion;
- Decision Engine V2;
- Sales Guard;
- anti-repetição semântica;
- AGCN Presenter Dataset V1.
