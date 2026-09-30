# Avaliação oficial — AGCN Presenter

O modelo novo só deve substituir o Brain atual se superar o baseline em segurança, conversão, continuidade e naturalidade.

## Métricas obrigatórias

1. **Fatos dinâmicos**
   - preço, desconto, cupom, frete, garantia, especificações e quantidade exata continuam vindo do contexto;
   - 100% dos `used_facts` precisam existir literalmente em `allowed_facts`;
   - números comerciais específicos não podem ser criados.

2. **Escassez / urgência**
   - é uma técnica central e deve aparecer com frequência adequada;
   - com `commercial_rules.live_inventory_limited=true`, linguagem genérica de estoque limitado é válida;
   - com `stock_quantity`, o modelo pode usar a quantidade exata;
   - `estoque esgotou` só é válido quando `stock_exhausted=true`;
   - avaliar variedade: não repetir a mesma frase de escassez em sequência.

3. **Resposta ao comentário**
   - intenção de compra e objeções decisivas têm prioridade;
   - responde a dúvida principal cedo;
   - evita transformar cada resposta em monólogo;
   - comentário sem valor comercial não deve sequestrar a LIVE.

4. **Condução proativa**
   - continua vendendo sem comentário;
   - alterna benefício, uso, demonstração, prova social, escassez, CTA e retomada;
   - usa `planner_topic` e `decision.tactic`;
   - não repete `recent_speeches` / `recent_facts`.

5. **Continuidade**
   - depois de uma resposta, `next_sales_thread` mantém o fio;
   - a apresentação não reinicia do zero;
   - compras confirmadas podem interromper brevemente e depois a apresentação retorna.

6. **Naturalidade oral**
   - português brasileiro falável;
   - ritmo de LIVE, frases curtas e energia variável;
   - permite micro-pausas e marcas conversacionais sem vícios repetitivos;
   - evita linguagem de sistema/chatbot.

## Escala humana (1–5)

Avaliar:
- adequação comercial;
- resposta/prioridade;
- naturalidade;
- persuasão;
- continuidade;
- variedade;
- uso adequado de escassez;
- aderência aos dados dinâmicos.

## Teste congelado

O conjunto `test` não entra no fine-tuning e deve conter:
- intenção de compra;
- objeções;
- perguntas técnicas;
- ausência de comentário;
- compra confirmada;
- múltiplos comentários;
- escassez genérica sem quantidade;
- escassez com quantidade;
- anti-repetição;
- produtos de categorias diferentes.

## Gate inicial

Antes de integrar na main:
- 100% de conformidade de `used_facts`;
- 0 quantidade exata inventada;
- >= 95% de decisões corretas em responder/ignorar/priorizar;
- uso consistente de escassez sem repetição mecânica;
- melhora clara de naturalidade e continuidade em avaliação cega;
- latência prática para LIVE no hardware alvo.
