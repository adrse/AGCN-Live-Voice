# Comparação — Qwen atual vs AGCN Presenter v0.1

Casos comparáveis: **25**

A comparação automática é só apoio. A decisão final vem da revisão humana cega.
O baseline oficial usa GGUF Q4_K_M + prompt/validators de produção. O adapter usa Transformers NF4 + política de treinamento, sem os mesmos validators. Diferenças de latência e comportamento também incluem essas mudanças; não são atribuíveis apenas ao treino.

## eval-001

**Alvo de referência:** Vai minizero, shaver, cabeçote de corte, cabo USB e vassourinha. É o kit completinho.

**Qwen atual:** Vem tudo nessa caixa: minizero, shaver, cabeçote de corte, cabo USB e vassourinha. É um aparatador super completo!

**AGCN v0.1:** Vem o minizero, o shaver, o cabeçote de corte, o cabo USB e a vassourinha.

**Latência:** Qwen atual 3.818s; AGCN v0.1 16.663s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": null}

## eval-002

**Alvo de referência:** IGNORAR

**Qwen atual:** BrainOutputError: Brain falhou após 2 tentativa(s): used_fact não autorizado: resistente a água

**AGCN v0.1:** IGNORAR

**Latência:** Qwen atual 4.293s; AGCN v0.1 7.776s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": null}

## eval-003

**Alvo de referência:** Ó, se cê tá de olho nesse kit, não enrola. Tá nas últimas unidades da LIVE e pode acabar rápido.

**Qwen atual:** BrainOutputError: Brain falhou após 2 tentativa(s): número não autorizado na fala: 3

**AGCN v0.1:** Pra quem já pensou em colocar no carrinho, não deixa pra depois. São poucas unidades na LIVE e não vai ter pra todo mundo.

**Latência:** Qwen atual 3.396s; AGCN v0.1 12.712s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": true, "quantity_ok": null, "buying_guidance_ok": null}

## eval-004

**Alvo de referência:** Muda o tamanho: o 1 tem quarenta e dois e o 2 cinquenta e dois centímetros. A rotação é a mesma nos dois.

**Qwen atual:** O modelo 2 é um pouco maior, com 52 cm de diâmetro, enquanto o modelo 1 é 42 cm. Ambos têm 1000 RPM.

**AGCN v0.1:** O tamanho: o Item 1 é 42 cm e o Item 2 é 52 cm. Ambos têm 1000 RPM.

**Latência:** Qwen atual 2.634s; AGCN v0.1 18.241s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": null}

## eval-005

**Alvo de referência:** Ele foi apresentado como silencioso. Ó, aqui o melhor é demonstrar pra você ouvir de verdade.

**Qwen atual:** Não, o ventilador é silencioso! O problema é com o ventilador tradicional, não com esse. Confira o produto!

**AGCN v0.1:** Não, o ventilador é silencioso. Foi o principal benefício que colocamos no produto.

**Latência:** Qwen atual 1.741s; AGCN v0.1 12.385s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": null}

## eval-006

**Alvo de referência:** Pra quem chegou agora: cê controla a velocidade e a luz pelo controle, sem ter que levantar toda hora.

**Qwen atual:** Olha esse ventilador de teto LED com controle remoto e 3 velocidades. Vai ser perfeito para arrefecer o ambiente com estilo.

**AGCN v0.1:** Ó, e cê já consegue escolher a velocidade e a cor da luz pelo controle.

**Latência:** Qwen atual 4.314s; AGCN v0.1 13.947s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": null}

## eval-007

**Alvo de referência:** Restam 4 unidades. Se cê já decidiu, finaliza agora pra não ficar sem.

**Qwen atual:** Estamos com apenas 4 unidades disponíveis! Não perca essa oportunidade única!

**AGCN v0.1:** Agora restam quatro unidades, então se cê colocar no carrinho e finalizar, não deixa pra depois.

**Latência:** Qwen atual 3.423s; AGCN v0.1 12.808s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": true, "quantity_ok": true, "buying_guidance_ok": null}

## eval-008

**Alvo de referência:** Quatorze litros, Rosa.

**Qwen atual:** É de 14 litros, cara! Essa capacidade é super importante para limpar grandes áreas sem precisar parar e recarregar tanto.

**AGCN v0.1:** É de quatorze litros, Rosa.

**Latência:** Qwen atual 2.09s; AGCN v0.1 10.284s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": null}

## eval-009

**Alvo de referência:** Pode variar por região, Ana. Confere o valor que apareceu aí pra você antes de finalizar.

**Qwen atual:** BrainOutputError: Brain falhou após 2 tentativa(s): alegação de frete sem used_fact correspondente

**AGCN v0.1:** O valor mudou, Ana. E o frete pode variar conforme a região.

**Latência:** Qwen atual 3.482s; AGCN v0.1 12.724s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": null}

## eval-010

**Alvo de referência:** Quem já colocou no carrinho, finaliza. São poucas unidades e não vai ter pra todo mundo.

**Qwen atual:** BrainOutputError: Brain falhou após 2 tentativa(s): número não autorizado na fala: 14

**AGCN v0.1:** Ó, não deixa pra depois. São poucas unidades nessa LIVE, então se cê já decidiu, finaliza agora.

**Latência:** Qwen atual 3.83s; AGCN v0.1 12.05s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": true, "quantity_ok": null, "buying_guidance_ok": null}

## eval-011

**Alvo de referência:** Aguenta até cento e noventa e cinco quilos.

**Qwen atual:** A capacidade do sofá é de até 195 kg, então sim, você pode usar com segurança. Agora é a hora de aproveitar!

**AGCN v0.1:** A Thi, consegue sim. Esse modelo aguenta até cento e noventa e cinco quilos.

**Latência:** Qwen atual 1.757s; AGCN v0.1 12.556s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": null}

## eval-012

**Alvo de referência:** Com unha afiada tem risco sim. Eu colocaria uma manta por cima pra proteger melhor.

**Qwen atual:** A gente entende, o gato pode causar problema. Mas com a manta, a proteção é efetiva. Vamos garantir que o produto está bem protegido!

**AGCN v0.1:** Se cê tem gato, cuidado com unha afiada. Uma manta ajuda a proteger.

**Latência:** Qwen atual 2.387s; AGCN v0.1 16.119s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": null}

## eval-013

**Alvo de referência:** Então vai no Modelo A. Abre o produto fixado e escolhe a opção A, que vem com apoio de pé e inflador.

**Qwen atual:** Vamos por Modelo A, que inclui poltrona, apoio de pé e inflador. É a opção mais completa para quem quer com apoio!

**AGCN v0.1:** Então abre o produto fixado e escolhe a opção A. É a que vem com a poltrona, o apoio de pé e o inflador.

**Latência:** Qwen atual 2.718s; AGCN v0.1 18.553s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": true}

## eval-014

**Alvo de referência:** Tá nas últimas unidades, então se cê gostou desse modelo já aproveita e finaliza enquanto tem.

**Qwen atual:** BrainOutputError: Brain falhou após 2 tentativa(s): número não autorizado na fala: 3

**AGCN v0.1:** Ó, eu não deixo pra depois. São poucas unidades e não vai ter pra todo mundo. Finaliza enquanto tem.

**Latência:** Qwen atual 3.884s; AGCN v0.1 11.26s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": true, "quantity_ok": null, "buying_guidance_ok": null}

## eval-015

**Alvo de referência:** Tô com 45 poltronas agora. Quem já decidiu, não deixa pra depois porque em LIVE isso gira rápido.

**Qwen atual:** BrainOutputError: Brain falhou após 2 tentativa(s): alegação de escassez/estoque sem used_fact correspondente

**AGCN v0.1:** Agora restam quarenta e cinco poltronas. Quem já colocou no carrinho, finaliza e não deixa pra depois.

**Latência:** Qwen atual 3.921s; AGCN v0.1 13.808s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": true, "quantity_ok": false, "buying_guidance_ok": null}

## eval-016

**Alvo de referência:** Pega sim. Vai na indução e também em gás, elétrico, vitrocerâmico, lenha e forno.

**Qwen atual:** BrainOutputError: Brain falhou após 2 tentativa(s): número não autorizado na fala: 13

**AGCN v0.1:** Pega sim. É pra indução, gás, elétrico, vitrocerâmico, lenha e forno.

**Latência:** Qwen atual 5.033s; AGCN v0.1 14.865s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": null}

## eval-017

**Alvo de referência:** Pode sim, Maria. Vai pro forno com a tampa.

**Qwen atual:** A compatibilidade é sim, pode ir ao forno com a tampa. Confirmando o uso seguro.

**AGCN v0.1:** Pode sim. Vai ao forno com a tampa.

**Latência:** Qwen atual 1.776s; AGCN v0.1 11.405s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": null}

## eval-018

**Alvo de referência:** IGNORAR

**Qwen atual:** A lavadora é perfeita para lavar louças, mas tem um sistema de centrifugação que deixa as pratas bem secas. Quer ver o vídeo de como funciona?

**AGCN v0.1:** IGNORAR

**Latência:** Qwen atual 1.953s; AGCN v0.1 7.644s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": null}

## eval-019

**Alvo de referência:** Não. Esse modelo não tem NFC pra pagamento.

**Qwen atual:** BrainOutputError: Brain falhou após 2 tentativa(s): número não autorizado na fala: 20

**AGCN v0.1:** Não, não tem NFC pra pagamento.

**Latência:** Qwen atual 3.317s; AGCN v0.1 9.11s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": null}

## eval-020

**Alvo de referência:** Dá sim. Cê consegue fazer e atender ligação pela telinha.

**Qwen atual:** BrainOutputError: Brain falhou após 2 tentativa(s): número não autorizado na fala: 20

**AGCN v0.1:** Sim, ele faz e atende as ligações.

**Latência:** Qwen atual 4.001s; AGCN v0.1 11.028s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": null}

## eval-021

**Alvo de referência:** Só restam 3 unidades agora. Quem tá com ele no carrinho, finaliza pra não ficar sem.

**Qwen atual:** BrainOutputError: Brain falhou após 2 tentativa(s): alegação de preço sem used_fact correspondente

**AGCN v0.1:** Agora restam três unidades. Quem já colocou no carrinho não deixa pra depois.

**Latência:** Qwen atual 3.924s; AGCN v0.1 12.075s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": true, "quantity_ok": true, "buying_guidance_ok": null}

## eval-022

**Alvo de referência:** Esse conjunto é pra fogão convencional a gás.

**Qwen atual:** A resposta é sim, mas preciso esclarecer: a frigideira é compatível com fogão convencional a gás, não com indução. Se você tem indução, talvez precise de um modelo específico. Vamos ver se tem interesse em outras opções?

**AGCN v0.1:** Não, Bia. Esse conjunto serve só para fogão convencional a gás.

**Latência:** Qwen atual 2.544s; AGCN v0.1 12.29s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": null}

## eval-023

**Alvo de referência:** Então abre o produto fixado aqui embaixo e finaliza por ali. Vai o jogo com três frigideiras e a espátula.

**Qwen atual:** Olá Rosa, você quer comprar esse conjunto de frigideiras? Temos 3 frigideiras mais uma espátula incluída no pacote. Vamos finalizar essa compra agora!

**AGCN v0.1:** Ó, abre o produto fixado e finaliza. Se tava em carrinho, finaliza agora.

**Latência:** Qwen atual 2.267s; AGCN v0.1 10.745s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": true}

## eval-024

**Alvo de referência:** Aí sim, Lalita! Parabéns pela compra. Depois volta pra me contar o que achou.

**Qwen atual:** Parabéns pela compra! Vamos celebrar essa decisão rápida e acertada.

**AGCN v0.1:** Aí sim, Lalita. Parabéns pela compra.

**Latência:** Qwen atual 1.382s; AGCN v0.1 8.9s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": null}

## eval-025

**Alvo de referência:** Davi, abre o produto fixado aqui embaixo e vai em comprar. Se aparecer opção do kit, pega o conjunto das três com a espátula.

**Qwen atual:** Quer comprar? A LIVE é exclusiva e o produto está fixado para compra agora. Vamos finalizar rápido!

**AGCN v0.1:** Ó, então abre o produto fixado e finaliza. Não vai ter pra todo mundo.

**Latência:** Qwen atual 3.411s; AGCN v0.1 10.486s.

**Checks AGCN:** {"valid_json": true, "failed": false, "reported_facts_ok": true, "numeric_claims_ok": true, "ignore_ok": true, "oral_style_ok": true, "scarcity_ok": null, "quantity_ok": null, "buying_guidance_ok": true}

