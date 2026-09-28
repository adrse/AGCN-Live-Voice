# AGCN Live Voice — UI/UX congelada para o MVP Desktop

## Direção visual

Produto: **AGCN Live Voice**
Tagline: **Sua voz inteligente para vender ao vivo.**

Paleta:
- Azul principal: #0061FF
- Preto: #0A0A0B
- Grafite: #6B7280
- Cinza claro: #F3F5F9
- Branco: #FFFFFF

Estilo:
- desktop moderno, limpo, profissional;
- bordas suaves;
- sem visual gamer;
- informações críticas sempre visíveis;
- uso pensado para notebook/monitor 1366x768 ou maior;
- tema claro como padrão; escuro pode ser fase posterior.

## Navegação

Sidebar fixa à esquerda:
1. Dashboard
2. Produto
3. Configurações

Rodapé da sidebar:
- versão
- status geral
- botão sair/fechar não é necessário; usar janela padrão.

## Tela 1 — Dashboard

### Header
Esquerda:
- logo AGCN
- “AGCN Live Voice”
- subtítulo curto

Direita:
- TikTok: Conectado/Desconectado
- Brain: Qwen Local/API
- Voz: Local/Premium
- indicador de saída de áudio

### Card “TikTok LIVE”
- campo username
- botão Conectar / Desconectar
- status da LIVE
- room id opcional em detalhe
- viewers
- likes
- comentários recebidos

### Card “Produto ativo”
- imagem
- nome
- preço atual
- preço regular quando houver
- estoque quando cadastrado
- botão “Editar produto”
- badge “Sales Coach ativo”

### Card “Apresentadora”
- toggle Presenter ON/OFF
- estado: Parada / Preparando / Falando / Pausada / Erro
- botão Pausar
- botão Testar fala
- seletor rápido de Brain
- seletor rápido de Voz

### Card “Falando agora”
- texto exato que está sendo enviado ao TTS
- tópico atual
- origem: Proativo / Comentário
- usuário do comentário, se houver
- barra/waveform simples enquanto áudio toca

### Card “Fila de decisão”
Mostrar próximos itens:
- prioridade
- username
- comentário
- intenção
- status: aguardando / preparado / respondido

### Feed “Comentários”
- timestamp
- username
- texto
- ícone/badge para relevante, compra, pergunta, preço, objeção
- destacar comentário em resposta

### Métricas compactas
- viewers
- likes
- comentários
- falas geradas
- respostas a comentários
- tempo desde última fala

### Controles inferiores
- “Abrir saída 9:16”
- “Próximo vídeo”
- “Vídeo anterior”
- status da playlist

## Tela 2 — Produto

### Cabeçalho
- nome do produto
- status “Ativo na LIVE”
- salvar
- duplicar produto
- excluir produto

### Dados principais
Campos:
- Nome
- Marca
- Modelo
- Categoria
- Link opcional
- Imagem

### Informações comerciais
- Preço regular
- Preço atual
- Desconto
- Estoque
- Frete
- Cupom
- Oferta da LIVE
- Texto da oferta
- Observação promocional

### Fatos do produto
Cada grupo deve usar input + botão “Adicionar” e chips/caixas removíveis:
- Benefícios
- Problemas que resolve
- Diferenciais
- Itens inclusos
- Compatibilidade
- Tamanho
- Bateria
- Como usar
- Limitações
- Informações adicionais

Campos simples:
- Descrição
- Garantia

Os itens continuam persistidos de modo compatível com ProductStore atual.

### Vídeos do produto
Área de playlist:
- botão “Adicionar vídeo”
- cards com thumbnail, nome, duração
- reorder por drag ou setas
- toggle ativo/inativo
- botão remover
- botão visualizar
- mute do áudio original ligado por padrão

Config:
- loop da playlist ON por padrão
- modo de enquadramento: preencher / ajustar
- transição: corte simples no MVP

## Tela 3 — Configurações

### Cérebro da IA
Provider:
- Qwen Local (padrão)
- API Premium

Qwen:
- endpoint Ollama
- nome do modelo
- timeout
- botão Testar Qwen
- status

API:
- provider
- modelo
- chave API mascarada
- botão Testar
- chave nunca aparece inteira e nunca entra em log

### Voz
Provider:
- Local
- Premium/API

Local:
- engine/modelo
- voz
- velocidade
- botão Testar voz

Premium:
- provider
- modelo
- voz
- chave/credencial se necessária
- botão Testar voz

### Áudio
- dispositivo de saída
- atualizar lista
- volume
- botão “Testar no dispositivo”
- texto de ajuda: selecionar VB-CABLE/virtual cable para enviar ao TikTok LIVE Studio

### Presenter
- silêncio alvo: 8 s
- hard limit: 10 s
- cooldown CTA
- cooldown repetição de fato
- usar nome do comentarista: automático
- resposta direta primeiro: sempre ligado
- fallback local: ligado

### Dados
- pasta de dados
- abrir pasta
- exportar configuração
- importar configuração
- limpar logs

## Janela separada — AGCN Live Output

Objetivo: ser capturada pelo TikTok LIVE Studio.

Regras:
- janela independente;
- 9:16;
- nome fixo “AGCN Live Output”;
- sem barra/controles dentro da área capturada;
- fundo preto;
- vídeo ocupa toda área;
- áudio original do vídeo mudo por padrão;
- playlist continua mesmo com Dashboard minimizado;
- modo tela cheia opcional;
- Esc sai de tela cheia, não fecha aplicação.

Não mostrar:
- comentários;
- botões;
- status;
- logo grande;
- texto técnico;
- bordas de debug.

## Fluxo operacional do usuário

1. Abrir AGCN Live Voice.
2. Produto -> cadastrar/selecionar produto e vídeos.
3. Configurações -> escolher Qwen/API, voz e saída de áudio.
4. Dashboard -> digitar username TikTok.
5. Conectar.
6. Abrir “AGCN Live Output”.
7. No TikTok LIVE Studio, capturar a janela “AGCN Live Output”.
8. No TikTok LIVE Studio, escolher o cabo virtual como microfone.
9. Ativar Presenter.
10. Vídeos ficam em loop e a IA começa a vender.
11. Comentário relevante chega -> entra na prioridade -> IA responde -> retoma venda.

## Estados e feedback

Nenhuma ação longa deve parecer travada.
Mostrar estados:
- Conectando TikTok…
- Qwen pensando…
- Preparando fala…
- Gerando voz…
- Falando…
- Sem comentários — apresentação proativa ativa
- API indisponível — usando fallback local
- Nenhum produto ativo
- Nenhum vídeo cadastrado

Erros devem ser humanos e acionáveis, nunca traceback cru na UI.

## Fora do MVP

Não implementar agora:
- avatar;
- lip sync;
- câmera virtual própria;
- edição de vídeo;
- geração automática de vídeo;
- pesquisa automática de produto;
- pagamentos;
- contas multiusuário;
- app mobile.
