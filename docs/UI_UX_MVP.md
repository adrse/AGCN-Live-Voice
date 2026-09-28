# AGCN Live Voice — UI/UX MVP

## Direção
Azul #0061FF, preto #0A0A0B, grafite #6B7280, cinza #F3F5F9.

Navegação:
1. Dashboard
2. Produto
3. Configurações

## Dashboard

Header:
- TikTok
- Brain
- Voz
- Áudio

TikTok LIVE:
- username
- Conectar/Desconectar
- status
- viewers
- likes
- comentários

Produto ativo:
- imagem
- nome
- preço
- estoque
- Editar produto

Presenter:
- ON/OFF
- Pausar
- Testar fala
- Brain
- Voz

Falando agora:
- texto
- tópico
- origem Proativo/Comentário
- username quando houver

Fila:
- prioridade
- username
- comentário
- intenção
- status

Comentários:
- timestamp
- username
- texto
- badge de intenção/relevância

Métricas:
- viewers
- likes
- comentários
- falas
- respostas
- tempo desde última fala

Não há controles de vídeo no MVP.

## Produto

Dados:
- nome, marca, modelo, categoria, link opcional, imagem

Comercial:
- preço regular, preço atual, desconto, estoque, frete, cupom, oferta LIVE, observação

Fatos itemizados:
- benefícios
- problemas resolvidos
- diferenciais
- itens inclusos
- compatibilidade
- tamanho
- bateria
- uso
- limitações
- informações adicionais

Simples:
- descrição
- garantia

Não cadastrar vídeos no AGCN nesta fase.

## Configurações

Brain:
- Qwen Local / API
- endpoint/modelo
- chave mascarada quando API
- Testar
- status

Voz:
- Local / Premium
- voz/modelo
- velocidade
- Testar

Áudio:
- device
- atualizar
- volume
- testar

Presenter:
- silêncio alvo 8 s
- hard limit 10 s
- cooldown CTA
- cooldown fato
- usar nome automaticamente
- resposta direta primeiro
- fallback local

Dados:
- pasta
- exportar/importar config
- logs

## Fluxo

1. Cadastrar produto.
2. Configurar Brain/voz/device.
3. No TikTok LIVE Studio, preparar o vídeo do produto separadamente.
4. No AGCN, conectar username.
5. Ativar Presenter.
6. IA vende continuamente.
7. Comentário relevante entra na prioridade.
8. IA responde.
9. IA retoma a venda.

Erros devem ser humanos e acionáveis; nunca traceback cru.
