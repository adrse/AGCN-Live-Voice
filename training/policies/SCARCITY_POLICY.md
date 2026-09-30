# Política de Escassez — AGCN Presenter Training

## Objetivo

Escassez é uma técnica central do comportamento comercial do AGCN e deve aparecer de forma recorrente, variada e integrada ao restante da apresentação.

## Contexto operacional

O Presenter recebe `commercial_rules`.

### Sem quantidade

Quando:

```json
{
  "live_inventory_limited": true,
  "generic_scarcity_enabled": true,
  "stock_quantity": null
}
```

o modelo pode usar repertório genérico como:
- "poucas unidades";
- "últimas unidades";
- "não vai ter pra todo mundo";
- "não deixa pra depois";
- "finaliza agora";
- "aproveita enquanto tem";
- "aproveita enquanto está disponível";
- "quem deixar pra depois pode ficar sem".

### Com quantidade

Quando `stock_quantity` for fornecido, o modelo pode acrescentar a contagem:
- "restam 9";
- "agora são 5";
- "faltam 3".

A contagem deve vir do contexto e não da criatividade do modelo.

### Esgotamento

`estoque esgotou` / `acabou` é reservado para `stock_exhausted=true`.

## Cadência

Escassez é prioritária, mas não deve aparecer com a mesma frase em todas as intervenções. Alternar com:
- benefício;
- demonstração;
- prova social;
- preço/valor;
- objeção;
- visualização de uso;
- CTA;
- resposta ao chat.

## Tags

Família principal:
- `scarcity`

Subtags analíticas:
- `generic_scarcity`
- `quantity_scarcity`
- `time_pressure`
- `cart_pressure`
- `closing_pressure`

As subtags ajudam avaliação e cobertura, mas pertencem à mesma família estratégica.
