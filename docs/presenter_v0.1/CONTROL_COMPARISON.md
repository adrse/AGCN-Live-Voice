# Controle do efeito do adapter

Qwen/Qwen3-4B sem adapter e AGCN v0.1: mesmo prompt, NF4, T4, FP16, thinking desligado, amostragem e semente independente por caso. As saídas são brutas, sem validators de produção. Este controle complementa o baseline oficial GGUF; não o substitui.

## eval-001

**Gold:** Vai minizero, shaver, cabeçote de corte, cabo USB e vassourinha. É o kit completinho.

**Qwen sem adapter:** Vem na caixa tudo de praia! Minizero, shaver, cabeçote de corte, cabo USB e vassourinha. Ó, não vai ter pra todo mundo, restam 9 só pra gente!

**AGCN v0.1:** Vem o minizero, o shaver, o cabeçote de corte, o cabo USB e a vassourinha.

**Latência:** controle 16.532 s; adapter 16.663 s.

## eval-002

**Gold:** IGNORAR

**Qwen sem adapter:** Ó, Leo, aí sim! Aí sim, é a prova da água! Tá com a prova da água, tá com a garantia! Aí sim, é a prova da água, tá com a garantia! Aí sim, é a prova da água, tá com a garantia!

**AGCN v0.1:** IGNORAR

**Latência:** controle 14.109 s; adapter 7.776 s.

## eval-003

**Gold:** Ó, se cê tá de olho nesse kit, não enrola. Tá nas últimas unidades da LIVE e pode acabar rápido.

**Qwen sem adapter:** Ó, gente! Essa é a cara do que você precisa! Aparador multifuncional 3 em 1, que faz tudo que você precisa em uma só mão!

**AGCN v0.1:** Pra quem já pensou em colocar no carrinho, não deixa pra depois. São poucas unidades na LIVE e não vai ter pra todo mundo.

**Latência:** controle 9.598 s; adapter 12.712 s.

## eval-004

**Gold:** Muda o tamanho: o 1 tem quarenta e dois e o 2 cinquenta e dois centímetros. A rotação é a mesma nos dois.

**Qwen sem adapter:** Aí sim, Julia! Parabéns pela compra. O tamanho do item 2 é 52 cm, mais alto, pra quem quer mais espaço. O que tá aí é o modelo 2, tá disponivel pra gente.

**AGCN v0.1:** O tamanho: o Item 1 é 42 cm e o Item 2 é 52 cm. Ambos têm 1000 RPM.

**Latência:** controle 15.25 s; adapter 18.241 s.

## eval-005

**Gold:** Ele foi apresentado como silencioso. Ó, aqui o melhor é demonstrar pra você ouvir de verdade.

**Qwen sem adapter:** Cê acha que é barulhento? Vai ver, o ventilador é silencioso, tá certo? A gente não quer barulho, né? A gente quer frescor sem o barulho do vento! A gente quer frescor com calma, sem stress! Vai ver, é silencioso, tá certo! A gente não quer barulho, né? A gente quer frescor com calma, sem stress!

**AGCN v0.1:** Não, o ventilador é silencioso. Foi o principal benefício que colocamos no produto.

**Latência:** controle 18.217 s; adapter 12.385 s.

## eval-006

**Gold:** Pra quem chegou agora: cê controla a velocidade e a luz pelo controle, sem ter que levantar toda hora.

**Qwen sem adapter:** Ó, gente! Esse ventilador de teto LED é um must-have! Tá ai pra resfriar o ambiente e ainda tem controle remoto! Vai lá, pega na opção A!

**AGCN v0.1:** Ó, e cê já consegue escolher a velocidade e a cor da luz pelo controle.

**Latência:** controle 12.421 s; adapter 13.947 s.

## eval-007

**Gold:** Restam 4 unidades. Se cê já decidiu, finaliza agora pra não ficar sem.

**Qwen sem adapter:** Ó, gente! Esse ventilador de teto LED 60W é um verdadeiro must-have pra quem quer frescor na casa! Restam só 4 unidades, então não deixa pra depois! Vai lá, pega na opção A, é um presente pra você!

**AGCN v0.1:** Agora restam quatro unidades, então se cê colocar no carrinho e finalizar, não deixa pra depois.

**Latência:** controle 12.861 s; adapter 12.808 s.

## eval-008

**Gold:** Quatorze litros, Rosa.

**Qwen sem adapter:** Aí sim, Maria! Parabéns pela compra.

**AGCN v0.1:** É de quatorze litros, Rosa.

**Latência:** controle 7.919 s; adapter 10.284 s.

## eval-009

**Gold:** Pode variar por região, Ana. Confere o valor que apareceu aí pra você antes de finalizar.

**Qwen sem adapter:** Aí sim, Ana! Parabéns pela compra. O novo valor tá aqui pra você. Vai na opção A, finaliza enquanto tem.

**AGCN v0.1:** O valor mudou, Ana. E o frete pode variar conforme a região.

**Latência:** controle 11.151 s; adapter 12.724 s.

## eval-010

**Gold:** Quem já colocou no carrinho, finaliza. São poucas unidades e não vai ter pra todo mundo.

**Qwen sem adapter:** Aí sim, Maria! Parabéns pela compra.

**AGCN v0.1:** Ó, não deixa pra depois. São poucas unidades nessa LIVE, então se cê já decidiu, finaliza agora.

**Latência:** controle 7.224 s; adapter 12.05 s.

## eval-011

**Gold:** Aguenta até cento e noventa e cinco quilos.

**Qwen sem adapter:** Tá cê pesado? Aí sim, a capacidade é até 195 kg. Não vai dar problema, tá certo! Aí sim, aí sim, aí sim, aí sim, aí sim, aí sim, aí sim, aí sim, aí sim, aí sim!

**AGCN v0.1:** A Thi, consegue sim. Esse modelo aguenta até cento e noventa e cinco quilos.

**Latência:** controle 16.95 s; adapter 12.556 s.

## eval-012

**Gold:** Com unha afiada tem risco sim. Eu colocaria uma manta por cima pra proteger melhor.

**Qwen sem adapter:** Ó, Bia! Tá tudo bem, a gente tem que cuidar do gato. Mas a gente tem a manta pra proteger o PVC. Vai ser só colocar a manta no chão, e o gato não vai danificar o produto. A gente tem que ser rápido, restam poucas unidades!

**AGCN v0.1:** Se cê tem gato, cuidado com unha afiada. Uma manta ajuda a proteger.

**Latência:** controle 16.843 s; adapter 16.119 s.

## eval-013

**Gold:** Então vai no Modelo A. Abre o produto fixado e escolhe a opção A, que vem com apoio de pé e inflador.

**Qwen sem adapter:** Cê quer com apoio? Tá no modelo A! Vai na opção A, tem apoio de pé e inflador. Aí sim, cê tem tudo pra se achar na praia!

**AGCN v0.1:** Então abre o produto fixado e escolhe a opção A. É a que vem com a poltrona, o apoio de pé e o inflador.

**Latência:** controle 15.917 s; adapter 18.553 s.

## eval-014

**Gold:** Tá nas últimas unidades, então se cê gostou desse modelo já aproveita e finaliza enquanto tem.

**Qwen sem adapter:** Ó, gente! Essa é a última unidade do sofá inflável 3 em 1! Tá aí pra aproveitar enquanto tem!

**AGCN v0.1:** Ó, eu não deixo pra depois. São poucas unidades e não vai ter pra todo mundo. Finaliza enquanto tem.

**Latência:** controle 10.012 s; adapter 11.26 s.

## eval-015

**Gold:** Tô com 45 poltronas agora. Quem já decidiu, não deixa pra depois porque em LIVE isso gira rápido.

**Qwen sem adapter:** Aí sim, Maria! Parabéns pela compra.

**AGCN v0.1:** Agora restam quarenta e cinco poltronas. Quem já colocou no carrinho, finaliza e não deixa pra depois.

**Latência:** controle 7.873 s; adapter 13.808 s.

## eval-016

**Gold:** Pega sim. Vai na indução e também em gás, elétrico, vitrocerâmico, lenha e forno.

**Qwen sem adapter:** Tá com indução? Aí sim, o Berlin é perfeito pra isso! Restam 9 unidades, gente! Não deixa pra depois, finaliza agora!

**AGCN v0.1:** Pega sim. É pra indução, gás, elétrico, vitrocerâmico, lenha e forno.

**Latência:** controle 12.656 s; adapter 14.865 s.

## eval-017

**Gold:** Pode sim, Maria. Vai pro forno com a tampa.

**Qwen sem adapter:** Aí sim, Maria! Parabéns pela compra. O conjunto Berlin 13 peças pode realmente ir ao forno com a tampa. Não vai ter pra todo mundo, então aproveita enquanto tem. Vai na opção A, confirma e finaliza rápido!

**AGCN v0.1:** Pode sim. Vai ao forno com a tampa.

**Latência:** controle 13.271 s; adapter 11.405 s.

## eval-018

**Gold:** IGNORAR

**Qwen sem adapter:** Ó Brenda, cê quer saber se é pra lavar louças? Tá na hora de mostrar pra cê!

**AGCN v0.1:** IGNORAR

**Latência:** controle 9.837 s; adapter 7.644 s.

## eval-019

**Gold:** Não. Esse modelo não tem NFC pra pagamento.

**Qwen sem adapter:** Lu, tá tudo certo! Não tem NFC, mas tá tudo em ordem pra você pagar por aproximação. Aí sim, é pra você aproveitar enquanto tem!

**AGCN v0.1:** Não, não tem NFC pra pagamento.

**Latência:** controle 12.112 s; adapter 9.11 s.

## eval-020

**Gold:** Dá sim. Cê consegue fazer e atender ligação pela telinha.

**Qwen sem adapter:** Cê sabe, a gente tem essa função de atender chamadas direto no smartwatch. É pra quem quer ficar conectado a qualquer momento. E aí, quer provar? A gente tem só 5 unidades pra hoje, não vai ter pra todo mundo!

**AGCN v0.1:** Sim, ele faz e atende as ligações.

**Latência:** controle 13.744 s; adapter 11.028 s.

## eval-021

**Gold:** Só restam 3 unidades agora. Quem tá com ele no carrinho, finaliza pra não ficar sem.

**Qwen sem adapter:** Aí sim, Maria! Parabéns pela compra.

**AGCN v0.1:** Agora restam três unidades. Quem já colocou no carrinho não deixa pra depois.

**Latência:** controle 7.634 s; adapter 12.075 s.

## eval-022

**Gold:** Esse conjunto é pra fogão convencional a gás.

**Qwen sem adapter:** Cê tá perguntando se serve indução? Não, só fogão convencional a gás. A gente tem poucas unidades aí, não vai ter pra todo mundo. Se cê tá pensando em usar no fogão que tem, tá na briga!

**AGCN v0.1:** Não, Bia. Esse conjunto serve só para fogão convencional a gás.

**Latência:** controle 12.849 s; adapter 12.29 s.

## eval-023

**Gold:** Então abre o produto fixado aqui embaixo e finaliza por ali. Vai o jogo com três frigideiras e a espátula.

**Qwen sem adapter:** Aí sim, Rosa! Parabéns pela compra. Vai na opção A, é o conjunto 3 frigideiras Alegrete com espátula. Aproveita enquanto tem!

**AGCN v0.1:** Ó, abre o produto fixado e finaliza. Se tava em carrinho, finaliza agora.

**Latência:** controle 12.906 s; adapter 10.745 s.

## eval-024

**Gold:** Aí sim, Lalita! Parabéns pela compra. Depois volta pra me contar o que achou.

**Qwen sem adapter:** Aí sim, Lalita! Parabéns pela compra.

**AGCN v0.1:** Aí sim, Lalita. Parabéns pela compra.

**Latência:** controle 7.584 s; adapter 8.9 s.

## eval-025

**Gold:** Davi, abre o produto fixado aqui embaixo e vai em comprar. Se aparecer opção do kit, pega o conjunto das três com a espátula.

**Qwen sem adapter:** Aí sim, Davi! Parabéns pela compra. Vai na opção A, é o produto fixado, disponível pra compra na LIVE.

**AGCN v0.1:** Ó, então abre o produto fixado e finaliza. Não vai ter pra todo mundo.

**Latência:** controle 12.828 s; adapter 10.486 s.
