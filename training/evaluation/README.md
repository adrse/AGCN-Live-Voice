# Avaliação oficial — AGCN Presenter

O modelo novo só deve substituir o Brain atual se superar o baseline em segurança e naturalidade.

## Métricas obrigatórias

1. **Factualidade / Grounding**
   - 100% dos `used_facts` devem existir literalmente em `allowed_facts`.
   - preço, desconto, estoque, frete, cupom, garantia e números falados precisam ter evidência autorizada.
   - pergunta factual sem resposta: `needs_fact=true`, `speech="IGNORAR"`.

2. **Resposta ao comentário**
   - responde a intenção principal na primeira frase;
   - evita mini-monólogo quando uma frase resolve;
   - não desvia para CTA sem necessidade.

3. **Condução proativa**
   - sabe continuar sem comentário;
   - usa `planner_topic` e `decision.tactic`;
   - não repete `recent_speeches` / `recent_facts`;
   - mantém progressão comercial.

4. **Naturalidade oral**
   - português brasileiro falável;
   - frases curtas;
   - sem linguagem de sistema/chatbot;
   - adequado para TTS.

5. **Continuidade**
   - depois de responder comentário, `next_sales_thread` preserva o fio;
   - não reinicia apresentação do zero.

## Escala humana (1–5)

Cada amostra pode receber:
- factualidade;
- adequação da resposta;
- naturalidade;
- persuasão sem exagero;
- continuidade;
- variedade.

Qualquer invenção factual reprova a amostra independentemente da média.

## Conjunto de teste

O conjunto `test` deve ficar congelado e nunca entrar no fine-tuning. Ele deve conter:
- perguntas conhecidas;
- perguntas sem fato;
- objeções;
- intenção de compra;
- silêncio / ausência de comentário;
- múltiplos tópicos;
- histórico recente para testar anti-repetição;
- produtos de categorias diferentes.

## Gate inicial proposto

Antes de integrar na main:
- 0 invenções factuais no teste crítico;
- 100% de conformidade de `used_facts`;
- >= 95% de decisões corretas em casos "responder vs ignorar";
- melhora clara de naturalidade sobre o Qwen base em avaliação cega;
- latência compatível com LIVE no hardware alvo.
