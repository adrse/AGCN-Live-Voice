# Presenter Brain — especificação obrigatória

Esta é a parte mais importante do AGCN Live Voice.

## Princípio

Qwen local e qualquer IA por API NÃO recebem um prompt genérico. Todos usam a mesma política central do produto, definida em `core/presenter_policy.py`.

O provider é intercambiável. O comportamento da apresentadora pertence ao AGCN.

```
TikTok -> Comment Intelligence -> Decision Engine -> Speech Planner
                                              |
                                              v
                                      BrainContext factual
                                              |
                  +---------------------------+--------------------------+
                  |                                                      |
             Qwen/Ollama                                           Provider API
                  |                                                      |
                  +---------------------- mesma PresenterPolicy ----------+
                                              |
                                         BrainResult
                                              |
                                       SalesGuard/validator
                                              |
                                             TTS
```

## Separação de responsabilidades

### Código determinístico
Responsável por:
- capturar/deduplicar comentários;
- estimar intenção e prioridade;
- escolher qual comentário merece resposta;
- controlar fila;
- memória;
- watchdog de silêncio;
- cooldown de CTA/fato/tópico;
- fornecer fatos permitidos;
- bloquear afirmação não suportada;
- decidir quando retomar fala proativa.

### Modelo de linguagem
Responsável por:
- entender linguagem natural, gíria, erro de digitação e pergunta implícita;
- transformar decisão + fatos em fala humana;
- responder de forma natural;
- ligar resposta a benefício/uso quando apropriado;
- manter continuidade de assunto;
- variar formulação sem repetir bordões.

O LLM não vira a autoridade sobre fatos nem sobre a fila.

## Prioridade de comentários

Ordem geral:
1. intenção de compra / como comprar;
2. preço, desconto, cupom, frete, disponibilidade/estoque;
3. objeção que pode impedir compra;
4. pergunta técnica, compatibilidade e uso;
5. benefícios/diferenciais;
6. confirmação de compra;
7. comentário geral relevante;
8. saudação, emoji e conversa paralela: normalmente ignorar.

Decision Engine pode ajustar a ordem por contexto, mas nunca deve deixar comentário irrelevante dominar a LIVE.

## Padrão de resposta

Pergunta:
**resposta direta -> expansão curta -> ponte para venda**

Exemplo abstrato:
"Maria, sim, [fato confirmado]. E isso é bom principalmente pra [uso/benefício confirmado]. Agora olha esse outro ponto..."

Não usar:
"Maria, eu entendo sua dúvida..."
"Segundo as informações cadastradas..."
"Valor de referência cadastrado..."

## Proatividade

Sem comentários relevantes a apresentadora continua falando.

A fala não pode se resumir a:
- "pra quem chegou agora";
- "quem tava esperando preço";
- "se você acabou de entrar";
- CTA repetido.

Ela deve realmente explorar o produto, usando fatos individuais, memória e sequência comercial.

## Continuidade

Antes de interrupção:
"sales_thread = bateria"

Chega pergunta de compatibilidade:
- responder compatibilidade;
- next_sales_thread preserva/atualiza a linha;
- depois voltar a bateria ou avançar naturalmente.

Não reiniciar a LIVE a cada comentário.

## Anti-alucinação

ALLOWED_FACTS é a fronteira factual.

Se alguém pergunta "pega internet?" e isso não está nos fatos:
- entender perfeitamente a pergunta;
- NÃO inferir pela categoria do produto;
- dizer de forma humana que essa informação não está confirmada no cadastro.

Preço, estoque, promoção, frete, garantia e compatibilidade têm proteção reforçada.

## Contexto enviado por turno

O modelo recebe:
- MODE;
- PRODUCT;
- LIVE_CONDITIONS;
- COMMENT selecionado;
- DECISION;
- RECENT_COMMENTS;
- RECENT_SPEECHES;
- RECENT_FACTS;
- SALES_THREAD;
- PLANNER_TOPIC;
- ALLOWED_FACTS.

Histórico deve ser curto e útil. Não enviar transcrição infinita da LIVE.

## Saída estruturada

```json
{
  "speech": "...",
  "topic": "...",
  "used_facts": ["..."],
  "needs_fact": false,
  "next_sales_thread": "..."
}
```

Nenhum provider pode devolver texto livre direto para o TTS sem parse/validação.

## API premium

A API não recebe liberdade total. Ela recebe:
1. `build_system_instruction()`;
2. `build_turn_payload(context)`;
3. schema JSON;
4. temperatura/configuração apropriada para fala consistente;
5. validação factual depois da resposta.

A mesma regra vale para OpenAI ou outro fornecedor.

## Qwen local

O Qwen recebe a mesma PresenterPolicy e o mesmo BrainContext.

A qualidade pode ser menor que um provider premium, mas o comportamento e os limites devem ser equivalentes.

## Critério de qualidade

Uma implementação não está pronta se:
- responde todos os comentários;
- ignora intenção de compra;
- repete abertura de recém-chegado;
- fala preço/estoque sem dado;
- perde o assunto após interrupção;
- fica esperando chat para falar;
- despeja toda a ficha do produto;
- usa frases robóticas;
- manda saída do LLM direto para voz sem validação.

## Implementação já preparada na branch de handoff

- `core/presenter_policy.py`: instrução central compartilhada por Qwen e API.
- `core/comment_selection_policy.py`: filtro de ruído, prioridade comercial e contrato para roteamento semântico de comentários ambíguos.
- `core/brain_orchestrator.py`: força todo provider a passar pela mesma PresenterPolicy, exige JSON estruturado, permite retry e validações antes do TTS.
- `tests/test_presenter_policy.py`, `tests/test_comment_selection_policy.py` e `tests/test_brain_orchestrator.py`: testes preparados para a camada de inteligência.

Regra: provider de modelo é transporte. Nenhum provider pode ter prompt comercial próprio ou enviar texto direto ao TTS.
