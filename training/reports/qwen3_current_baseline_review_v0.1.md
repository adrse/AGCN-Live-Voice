# Baseline oficial Qwen3-4B atual — revisão v0.1

Execução em 30/09/2026, Tesla T4, Qwen3-4B-Q4_K_M.gguf e llama.cpp b11264. PresenterBrain, prompt e validators de produção preservados. CUDA confirmado nos logs: 37/37 camadas. Os 25 casos congelados foram executados; 15 respostas aceitas, 10 rejeições dos validators, zero timeout. Rejeições são resultados do sistema atual, não casos omitidos.

Latência por caso, incluindo tentativas do PresenterBrain: média 3,092 s, mediana 3,396 s, mínimo 1,382 s e máximo 5,033 s. Medição com runtime aquecido; inicialização/download/model loading não estão incluídos. A primeira execução exploratória foi interrompida e não é este baseline oficial.

| Critério | Resultado observado |
|---|---|
| Intenção de compra | 3/3 recebem fala. Nenhuma das três explica claramente o clique no produto fixado e a finalização; eval-013 escolhe corretamente o Modelo A. |
| Escassez genérica | 0/3 casos específicos entregam fala; eval-003, 010 e 014 são rejeitados. |
| Escassez com quantidade | 1/3 entregue corretamente: eval-007 fala 4 unidades. eval-015 (45) e 021 (3) são rejeitados. |
| Perguntas sem fato | 0/2 produzem IGNORAR correto. eval-002 é bloqueado por fato não autorizado; eval-018 inventa uma lavadora e centrifugação, apesar de o produto ser conjunto de panelas. |
| Oralidade | Fala ainda escrita: “arrefecer o ambiente”, “Não perca essa oportunidade única”, “Vamos celebrar essa decisão rápida e acertada”. O detector de formalidade marca só 2; subestima a avaliação de estilo. |
| Objeção | eval-005 acrescenta crítica não fundamentada ao ventilador tradicional. eval-012 transforma “manta pode ajudar” em proteção “efetiva”, exagerando certeza. |
| Especificações | Comparação de tamanho/rotação e forno com tampa estão sustentados (eval-004/017). eval-022 começa com “sim” à indução e em seguida diz “não”; também infere incompatibilidade definitiva a partir de apenas compatibilidade com gás. |
| Compra confirmada | eval-024 comemora, mas soa formal e não fornece retomada comercial concreta. |

O indicador automático de escassez do baseline mostra 0/6 por não reconhecer “apenas 4 unidades”; a revisão confirma 1/6, correspondente ao único caso de quantidade entregue. O indicador de orientação de compra usa palavras muito amplas: “compra/finaliza” não equivale a explicar onde clicar. Campos used_facts corretos não garantem que a fala não inventou informação: eval-018 tem lista vazia e ainda assim inventa.

Há 18 respostas a comentários e 7 falas proativas no conjunto. Nenhum caso contém RECENT_SPEECHES ou SALES_THREAD preenchido. Estes 25 casos não demonstram continuidade longa nem anti-repetição ao longo de uma LIVE. É preciso um teste separado de sequência e produto inédito, sem modificar estes casos congelados.

Frozen eval SHA256: `09f7f0cb0e9fb2847a37c93ea58a5724460a88af4d5b2cf469d493feb6083bae`.

Recomendação nesta etapa: concluir QLoRA e a comparação, incluindo um controle do Qwen base com o mesmo prompt/engine do adapter. A comparação oficial mistura mudança de prompt, quantização, engine e validators com o fine-tuning; o controle ajuda a distinguir esses efeitos. Não integrar à produção com base apenas em checks lexicais.
