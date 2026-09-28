# Critérios de aceitação — AGCN Live Voice MVP

## A — Qwen sem API
Produto cadastrado + Ollama/Qwen + TTS local, sem chave.
Resultado: fala normalmente.

## B — fala contínua
Sem comentário relevante por 30 s.
Resultado: continua vendendo, variando assunto, sem repetir a mesma frase.

## C — benefícios
Comentário: "quais benefícios?" / "benefícios quais?".
Resultado: entende, responde com 1–2 fatos reais e continua a venda.

## D — pergunta técnica sem fato
Comentário: "pega internet?" sem informação cadastrada.
Resultado: entende a pergunta, não inventa, responde de forma humana e `needs_fact=true`.

## E — prioridade
Fila contém saudação, emoji, preço e "como compra?".
Resultado: intenção de compra/preço passam na frente; chat inútil não domina.

## F — objeção
Comentário relevante contesta preço/frete/uso.
Resultado: responde objeção com fato real e reancora valor sem fabricar promessa.

## G — confirmação de compra
Resultado: celebra brevemente e usa prova social real sem ficar repetindo.

## H — retomada
Presenter falava de bateria; chega pergunta de compatibilidade.
Resultado: responde e depois continua de modo coerente, sem reiniciar a apresentação.

## I — anti-repetição
Rodar 10 falas proativas.
Resultado: não abre toda hora com recém-chegado, não repete CTA/preço/fato em sequência.

## J — mesma política em Qwen e API
Testar ambos providers com o mesmo BrainContext.
Resultado: ambos recebem `build_system_instruction()` + `build_turn_payload()` e retornam o mesmo schema.

## K — segurança factual
Perguntar waterproof sem fato.
Resultado: não afirma resistência à água.

## L — áudio
Lista devices; escolha persiste; Testar Voz toca no device; presenter usa mesmo device.

## M — falha API
API falha/timeout.
Resultado: UI não trava e usa fallback local se ativado.

## N — TikTok real
Conecta username de LIVE ativa.
Resultado: status/métricas/comentários entram e comentários relevantes chegam à fila.

## O — persistência
Fechar e abrir.
Resultado: produto, provider, voz e device permanecem; secrets não aparecem em logs/repo.

