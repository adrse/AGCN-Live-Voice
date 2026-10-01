# AGCN Presenter v0.2 — Estado da execução

Data UTC: 2026-10-01. Branch: `research/agcn-presenter-training-v1`.

## Bloqueio observado

Ao conectar o ambiente T4 do Colab existente, a interface retornou:

> You cannot currently connect to a GPU due to usage limits in Colab.

O treino v0.2 **não foi iniciado**. Não existem loss, tempo de treino, melhor checkpoint nem resultados v0.2 dos 25 casos nesta execução. Não foram compradas unidades de computação nem usada outra conta para contornar o limite. O ambiente local também não dispõe de GPU CUDA.

## Preparação verificada

- Manifesto, relatório de validação e builder v0.2 lidos.
- Validador: 28 Gold Real + 72 Gold Synthetic anteriores + 400 Gold Synthetic novos aprovados.
- Builder: 458 treino / 42 validação; total 500.
- Zero inputs duplicados entre as três fontes; zero sobreposição com os testes congelados (IDs e inputs).
- Os 25 casos permanecem com SHA256 `09f7f0cb0e9fb2847a37c93ea58a5724460a88af4d5b2cf469d493feb6083bae`.
- Corpus treino SHA256 `c60c85d1f266074cc680207d2c2025edf22c58cb1765801a8cfab6fcfeae6e5a`.
- Corpus validação SHA256 `3859b5096039d15a68eb4f80129ef4e7c10457c844608eaa473d7d9d71c5cf54`.
- Preflight e compilação Python dos scripts aprovados. Treino, equivalência numérica da loss e inferência em GPU ainda não verificados nesta execução.

## Fluxo preparado

Notebook: `training/notebooks/AGCN_Presenter_v0_2_Colab.ipynb`.

Runner: `training/scripts/run_presenter_v0_2_experiment.py`.

O runner verifica branch, corpus e hash dos testes; usa Qwen/Qwen3-4B na mesma revisão do v0.1; inicia um adapter novo, sem continuar os pesos do v0.1. Configuração: 4 épocas, learning rate 2e-4, r=16/alpha=32, batch 1, acumulação 8, NF4, FP16 na T4. Melhor checkpoint escolhido pela validation loss. Retomada preserva checkpoints no Drive e bloqueia mudanças de protocolo em uma execução existente.

Destinos planejados, **ainda não criados por esta execução**:

- `MyDrive/AGCN/Presenter/agcn-presenter-v0.2-lora/`: adapter, checkpoints e histórico de loss.
- `MyDrive/AGCN/Presenter/Results-v0.2/`: logs, tempos por tentativa/etapa, protocolo, saídas e resumos dos três modelos, comparação dos 25 casos e lista de revisão semântica.

Qwen original, AGCN v0.1 e AGCN v0.2 serão avaliados novamente com a mesma revisão base, prompt, NF4, dtype, parâmetros de geração e sementes por caso. O adapter v0.1 é somente lido e tem seu hash conferido. O baseline GGUF histórico não é misturado à comparação controlada.

O relatório gerado pelo runner separa falhas automáticas de revisão semântica pendente. Fatos inventados na fala não são descartados apenas porque `used_facts` é válido. Escassez, intenção de compra, objeção, IGNORAR, CTA, naturalidade e repetição exigem revisão das 75 saídas. Não há conclusão de ganho do v0.2 antes dessa execução e revisão.

## Próximo passo necessário

Disponibilizar novamente uma GPU no Colab e executar o notebook. O bloqueio é de disponibilidade/quota, não um erro corrigível no script. Nada foi integrado à main, e o programa desktop não foi alterado.

## Diagnóstico da tentativa iniciada manualmente — 2026-10-01

Leitura da interface e diagnóstico de arquivos, sem retomar o treino:

- T4 conectada; branch e commit `03a8367` confirmados.
- Preflight retornou código 0.
- A célula de execução terminou com `CalledProcessError`, código 1, após aproximadamente 8 segundos.
- `/content/drive/MyDrive` existe.
- `/content/drive/MyDrive/AGCN/Presenter/agcn-presenter-v0.1-lora/adapter_model.safetensors` não existe.
- `Results-v0.2/status.json` não existe nesse Drive.

O runner exige o adapter histórico e calcula seu hash antes de criar o status de execução e antes de iniciar o treino. A ausência do arquivo impede essa etapa. Foi adicionada mensagem explícita para o arquivo ausente, preservando a verificação do hash. O notebook passou a encaminhar stdout/stderr do subprocesso para a saída visível, evitando mostrar somente o `CalledProcessError` externo.

Não foi criado, copiado nem substituído adapter nesta tentativa. Não há loss, checkpoint ou resultados v0.2 confirmados.
