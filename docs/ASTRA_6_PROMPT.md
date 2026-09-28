# Prompt pronto para Astra 6 — construir o programa

Você está assumindo o projeto privado `adrse/AGCN-Live-Voice`.

Trabalhe na branch `astra-handoff-2026-09-29`. Leia primeiro:
1. `docs/ASTRA_HANDOFF_2026-09-29.md`
2. `docs/DESKTOP_MVP_SPEC.md`
3. `docs/ACCEPTANCE_TESTS_MVP.md`
4. código atual de `core/`

MISSÃO: transformar o projeto atual em um programa Windows funcional chamado **AGCN Live Voice — Sua voz inteligente para vender ao vivo.**

Não faça uma demo superficial. Entregue a aplicação desktop funcional, reaproveitando o core que já existe.

Decisão final do MVP:
- sem avatar/rosto IA;
- vídeo real do produto em loop/playlist;
- Qwen local como cérebro padrão;
- provider API opcional;
- voz local/offline padrão;
- voz premium por API opcional;
- TikTok LIVE monitorado pelo core atual;
- produto cadastrado manualmente;
- PySide6;
- janela vertical 9:16 limpa para o TikTok LIVE Studio capturar;
- áudio enviado ao dispositivo de saída selecionado, pensado para VB-CABLE;
- nenhuma chave de API embutida.

Prioridade absoluta:
1. Desktop PySide6.
2. Produto + playlist.
3. Conexão TikTok usando monitor atual.
4. Brain Provider local Qwen/Ollama.
5. TTS local.
6. Audio device routing.
7. Fala contínua + resposta a comentário + retomada.
8. Janela 9:16.
9. Provider premium/API.
10. Empacotamento Windows.

Não perca tempo com MuseTalk, pesquisa automática de produto, mobile, pagamentos ou avatar.

Antes de alterar o core, rode os testes existentes e preserve comportamento já validado. Faça adapters ao redor do core quando possível.

A aplicação deve manter o modo atual de segurança factual: nunca inventar informação de produto. O LLM serve para entendimento e naturalidade, não para criar fatos.

Implemente e teste de ponta a ponta. Crie testes para providers, queue/scheduler e fallback. Deixe instruções de build/execução e gere um executável Windows se o ambiente permitir; se não permitir gerar .exe no ambiente atual, deixe o build script pronto e validado por estrutura.

Ao terminar, entregue um resumo objetivo de:
- arquivos criados/alterados;
- como rodar;
- dependências externas;
- o que foi testado;
- pendências reais;
- caminho exato para build do .exe.

