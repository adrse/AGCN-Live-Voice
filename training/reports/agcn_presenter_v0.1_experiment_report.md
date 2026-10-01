# AGCN Presenter v0.1 — primeiro experimento

Baseline, treino e avaliação concluídos em Tesla T4 no Colab. Todo o trabalho ficou na branch `research/agcn-presenter-training-v1`; aplicativo de produção e `main` não foram alterados. Adapter e checkpoints ficaram no Google Drive. Os 25 casos congelados não entraram no treino e seu SHA256 permaneceu `09f7f0cb0e9fb2847a37c93ea58a5724460a88af4d5b2cf469d493feb6083bae`.

## Execução

- **Baseline oficial:** Qwen3-4B-Q4_K_M.gguf, llama.cpp CUDA, 37/37 camadas descarregadas na GPU, PresenterBrain, prompt e validators atuais. 25 casos tentados, 15 saídas aceitas, 10 rejeições pelos validators, zero timeouts. Média 3,092 s; mediana 3,396 s; máximo 5,033 s. Latência medida com runtime aquecido, sem carregamento inicial.
- **Treino:** QLoRA sobre Qwen/Qwen3-4B, 93 exemplos de treino e 7 de validação, thinking desligado, 4 épocas/48 passos, aproximadamente 46 minutos. Melhor validação: loss 0,551506 na época 3 (`checkpoint-36`), recarregado para o adapter final. A época 4 piorou para 0,581704. Amostra de validação pequena: não demonstra generalização sozinha.
- **Avaliação AGCN:** 25/25 casos, zero falhas de execução/parse JSON. Média 12,417 s; mediana 12,290 s; máximo 18,553 s.
- **Controle adicional:** Qwen sem adapter, mesmo prompt de treino, NF4, FP16, T4, thinking, amostragem e sementes por caso. 25/25 casos; média 12,332 s. Este controle ajuda a separar o efeito do adapter das mudanças de prompt e engine.

O baseline usa GGUF Q4_K_M e a pilha de produção; adapter e controle usam Transformers NF4 e saídas brutas, sem retries/validators de produção. Portanto, 3,092 s versus 12,417 s não mede exclusivamente o custo do fine-tuning, nem prevê a latência de um eventual GGUF treinado.

## Resultados

| Critério | Baseline oficial | AGCN v0.1 | Controle sem adapter |
|---|---|---|---|
| Intenção de compra | 3/3 saídas aceitas; orientação automática 2/3; leitura das falas não encontrou instrução explícita de onde comprar nos 3 casos | 3/3 com orientação ao produto fixado | Check automático 2/3, mas comemora compras que ainda não ocorreram |
| Escassez, 6 casos previstos | Detector 0/6; leitura qualitativa 1/6 ("apenas 4 unidades") | 6/6 | Detector 1/6; outros casos perdem a intenção ou inventam estoque |
| Quantidade de estoque, 3 casos | 1/3 correto e aceito | Detector 2/3; leitura das falas 3/3: quatro, quarenta e cinco, três | Detector 1/3 |
| Casos que pedem IGNORAR | 0/2 respostas explícitas: um bloqueado, um respondido indevidamente | 2/2 corretos | 0/2 |
| Linguagem | Formalidade e expressões pouco naturais, como "arrefecer" | Mais curta, informal e adequada a TTS; ainda há frases estranhas | Repetição intensa, nomes/celebrações indevidos e "must-have" |
| Informação inventada | Há falhas semânticas aceitas, incluindo resposta sobre lavagem/centrifugação em conjunto de panelas | Melhor aderência, mas há inferências sem suporte | Inventa resistência à água, garantia, números de estoque e confirma pagamentos por aproximação apesar de ausência de NFC |

Os checks automáticos são apoio e não equivalem a aprovação semântica. `oral_style_ok` passa 25/25 tanto no adapter quanto no controle, apesar da má qualidade clara do controle. `reported_facts_ok` verifica os fatos declarados, não se todas as afirmações são sustentadas ou se todos os fatos usados foram declarados. O detector de quantidades não reconhece 45 por extenso; seu resultado original foi preservado, sem reescrever scores.

A comparação caso a caso inclui a resposta Gold esperada, a saída do Qwen atual e a do AGCN. Um segundo arquivo compara controle sem adapter versus AGCN, também com Gold. A análise qualitativa aqui foi feita pelo assistente, não é uma revisão humana cega.

## Pontos que ainda impedem recomendar produção

- **eval-022:** "serve só para fogão convencional a gás" afirma exclusividade e nega indução sem contexto suficiente. A referência Gold limita-se a informar uso a gás. O baseline também apresenta esse problema.
- **eval-011:** "consegue sim" garante adequação à pessoa sem conhecer seu peso, apesar de citar corretamente o limite de 195 kg. Deve informar o limite e condicionar a resposta ao peso.
- **eval-023/025:** orienta ao produto fixado, mas deixa `used_facts` vazio apesar de usar esse fato objetivo.
- **eval-005/014/023:** "benefício que colocamos no produto", "eu não deixo pra depois" e "se tava em carrinho" precisam de revisão de naturalidade. eval-006 troca "tipos de luz" por "cor da luz", interpretação que merece cautela.
- **Continuidade/anti-repetição:** as 25 entradas não têm histórico preenchido em `RECENT_SPEECHES` ou `SALES_THREAD`. O adapter retorna "retomar fechamento" em 8 casos e "retomar instalação" em 4, inclusive em contexto de poltrona/gato. Este teste isolado não comprova continuidade de uma LIVE longa.
- **Resposta a objeções:** há melhora em concisão, mas a resposta sobre barulho ainda não segue a demonstração cuidadosa sugerida pelo Gold; proteção com manta precisa preservar o caráter de possibilidade.

## Problemas técnicos resolvidos

A execução lenta inicial foi investigada: ativação real de CUDA/offload, logs e setup oficial do llama.cpp foram verificados. No treino, BF16 emulado na T4 elevava o tempo para cerca de 186 s por passo; o código passou a verificar suporte nativo e usar FP16. A perda foi limitada às posições supervisionadas da resposta, com equivalência de loss e gradientes verificada por teste; memória ficou em torno de 7 GB. Corrigidos também montagem do corpus, máscara da resposta, execução do avaliador e reprodutibilidade. Transformers foi fixado em 4.57.6. Nenhuma correção foi aplicada ao aplicativo de produção.

Uma tentativa adicional de ampliar o detector de números por extenso foi bloqueada nesta sessão. Não foi aplicada; os JSONs originais foram preservados e a divergência foi registrada nesta análise.

## Arquivos e armazenamento

- Baseline: `training/baselines/qwen3_4b_current_v0.1.jsonl`, `_summary.json`, `_runtime.json`.
- Resultados pequenos: `training/results/v0.1/`, incluindo avaliações JSONL, summaries, comparação com Gold, controle, log de treino, log de avaliação e proveniência.
- Revisão detalhada do baseline: `training/reports/qwen3_current_baseline_review_v0.1.md`.
- Drive: `MyDrive/AGCN/Presenter/Baseline-Qwen3-v0.1/`, `Results-v0.1/` e `agcn-presenter-v0.1-lora/`.
- Adapter final: 132.187.888 bytes; SHA256 `5652197ef5f1bc212822d071ed28cd5a9802fea62aa3f5f802e88896486a6524`. Pesos não enviados ao GitHub.

## Próximo passo recomendado

Manter v0.1 em pesquisa. Ampliar exemplos de incerteza técnica, compatibilidade não exclusiva, fatos usados no CTA e frases naturais. Criar uma avaliação separada com produtos inéditos e sequências de comentários/silêncio para medir continuidade e anti-repetição, mantendo os 25 casos atuais congelados. Depois, avaliar uma exportação GGUF do candidato com a mesma pilha de produção em ambiente de teste, incluindo latência e validators. Fazer revisão humana cega antes de qualquer decisão de integrar à `main`.
