# Critérios de aceitação — AGCN Live Voice MVP

## Teste A — sem internet de IA
- Qwen/Ollama local configurado.
- TTS local configurado.
- Produto cadastrado.
- Sem chave de API.
Resultado: presenter gera e toca fala normalmente.

## Teste B — silêncio
- LIVE sem comentário relevante por 30 s.
Resultado: sistema continua falando sobre o produto e não repete a mesma frase em loop.

## Teste C — pergunta factual
Comentário: "quantos litros?" / "pega internet?" / "quais benefícios?"
Resultado:
- entende variação natural;
- responde primeiro;
- usa apenas dado cadastrado;
- se dado não existe, não inventa;
- depois retoma venda.

## Teste D — compra
Comentário/evento de compra simulado.
Resultado: celebra brevemente e usa como prova social sem repetir excessivamente.

## Teste E — prioridade
Há uma fala proativa pronta e chega pergunta de compra/preço.
Resultado: pergunta entra antes das próximas falas proativas.

## Teste F — retomada
Presenter estava falando de bateria; recebe pergunta de compatibilidade.
Resultado: responde compatibilidade e depois consegue continuar a venda sem resetar sempre para introdução.

## Teste G — mídia
Produto tem 3 vídeos.
Resultado:
- janela 9:16 abre;
- vídeos rodam em ordem e loop;
- áudio dos vídeos fica mudo por padrão;
- usuário pode próximo/anterior;
- janela não exibe controles.

## Teste H — áudio
Resultado:
- lista devices Windows;
- device selecionado persiste;
- botão Testar Voz toca no device;
- presenter usa o mesmo device.

## Teste I — falha API
Provider premium retorna erro/timeout.
Resultado: UI informa falha sem travar e usa fallback local se habilitado.

## Teste J — segurança factual
Produto não tem informação de waterproof.
Comentário: "é à prova d'água?"
Resultado: presenter não afirma resistência à água.

## Teste K — TikTok real
Conectar username de uma LIVE ativa.
Resultado:
- status conectado;
- viewers/likes atualizam quando disponíveis;
- comentários chegam;
- presenter responde itens relevantes.

## Teste L — TikTok Studio
- Capturar janela AGCN Live Output.
- Selecionar cabo virtual como microfone.
Resultado: vídeo e voz entram na transmissão sem precisar de integração API com TikTok Studio.

## Teste M — persistência
Fechar e reabrir.
Resultado:
- produto salvo;
- playlist salva;
- voz/provider/config preservados;
- chaves não aparecem em log ou repositório.

