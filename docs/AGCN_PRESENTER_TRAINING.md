# Plano — AGCN Presenter Model

Status: laboratório em branch isolada `research/agcn-presenter-training-v1`.

## Visão

O AGCN Presenter Model será uma especialização do modelo-base local, focada em condução de LIVE commerce. O alvo não é conhecimento geral: é comportamento de venda em fluxo contínuo.

Caminho:
1. dataset ouro humano e de LIVEs reais;
2. desduplicação e normalização;
3. conjunto de teste congelado;
4. expansão sintética revisada;
5. SFT/LoRA;
6. avaliação cega contra o modelo-base;
7. preference tuning se houver ganho;
8. conversão para o formato local do runtime;
9. teste em LIVE;
10. integração na `main` somente após aprovação.

## Competências centrais

- responder intenção de compra rapidamente;
- transformar pergunta técnica em benefício quando fizer sentido;
- tratar objeções sem travar a LIVE;
- conduzir a apresentação quando ninguém comenta;
- escassez e fechamento como técnicas prioritárias;
- CTA guiado quando o comprador demonstra intenção;
- celebração curta de compra e prova social;
- retomada natural;
- anti-repetição;
- linguagem oral adequada ao TTS;
- honestidade sobre limitações reais do produto.

## Regra operacional de escassez

A aplicação poderá informar uma regra comercial de sessão:

- `live_inventory_limited=true`: a LIVE trabalha com inventário limitado;
- `generic_scarcity_enabled=true`: permite linguagem genérica de escassez mesmo sem contagem;
- `stock_quantity=N`: quando existir, permite dizer a quantidade exata.

Assim o modelo não decide sozinho se uma LIVE é limitada: o sistema estabelece a regra. Se houver número, o Presenter usa o número; sem número, trabalha pressão genérica e fechamento.

Exemplos de repertório genérico:
- poucas unidades;
- últimas unidades;
- não vai ter pra todo mundo;
- não deixa pra depois;
- finaliza agora;
- aproveita enquanto tem;
- aproveita enquanto está disponível;
- quem deixar pra depois pode ficar sem.

## Dados observados em LIVEs

Os relatórios já mostram padrões recorrentes:
- contagem regressiva de unidades;
- respostas nominais a dúvidas;
- CTA passo a passo;
- feature -> benefício;
- dor -> solução;
- prova social por compras;
- visualização de uso;
- demonstração física/sonora;
- retomada após comentário;
- erros úteis como exemplos negativos: repetição, preço inconsistente, ignorar intenção de compra e se prender a suporte.

## Fase atual

Marco atual concluído: **100 exemplos Gold derivados/revisados das LIVEs + 25 situações de teste congeladas**.

O conjunto congelado não pode ser usado em SFT, LoRA ou expansão sintética. Ele existe para medir o ganho real do modelo.

### Linguagem alvo

O Presenter deve falar como vendedor brasileiro em LIVE. Preferir oralidade natural:

- "tá" em vez de "está";
- "tô" em vez de "estou";
- "pra" em vez de "para" na fala;
- "ó", "bora" e "cê" quando soarem naturais.

Não transformar isso em caricatura: clareza continua sendo prioridade.

Depois:
- 500–1.000 Gold;
- 10k–30k exemplos revisados/expandidos;
- primeiro LoRA;
- comparação objetiva.

## Voz

Brain e voz continuam separados.
O dataset preserva `voice_style` e observações de prosódia para, no futuro, treinar/ajustar:
- energia;
- pausa;
- respiração;
- ênfase;
- ritmo;
- tom de confiança;
- celebração de compra.

## Critério de integração

O novo modelo só entra na `main` quando superar o atual em teste congelado sem comprometer estabilidade, latência e controle do runtime.
