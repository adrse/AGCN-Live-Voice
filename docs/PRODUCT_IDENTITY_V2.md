# Product Identity V2 — TikTok + Google Lens local

## Objetivo

Identificar o produto antes de aceitar qualquer informação externa.

O TikTok continua sendo a fonte inicial de identidade. O Google Lens é usado
somente para descobrir páginas visualmente relacionadas. O processamento roda
no computador do usuário; não existe backend AGCN obrigatório.

## Fluxo

1. Recebe o link do TikTok Shop.
2. Extrai título, imagem, Product ID e metadados disponíveis.
3. Salva uma cópia temporária da imagem no computador.
4. Abre a interface web oficial do Google Lens com Playwright.
5. Faz upload da imagem e, quando disponível, adiciona o título do TikTok como
   refinamento textual.
6. Coleta links externos encontrados pelo Lens.
7. Mantém principalmente marketplaces públicos conhecidos.
8. Pesquisa também por texto como fallback.
9. Abre cada candidato e coleta título, imagem principal, marca, modelo,
   descrição e especificações.
10. Compara localmente a imagem original com a imagem do candidato usando
    pHash + dHash.
11. Classifica a identidade:
    - CONFIRMED: marca+modelo conferidos ou mesma foto de catálogo.
    - NEEDS_CONFIRMATION: Lens encontrou candidato visualmente relacionado,
      mas faltou evidência forte.
12. Somente fontes CONFIRMED podem preencher automaticamente a ficha.
13. Candidatos NEEDS_CONFIRMATION serão mostrados para o usuário escolher.
14. Preço, desconto e estoque encontrados fora do TikTok nunca substituem a
    condição da LIVE.

## Privacidade / arquitetura

- Google Lens roda pelo navegador local.
- A imagem temporária é apagada depois da pesquisa.
- Não há conta TikTok central do AGCN.
- Não há servidor AGCN obrigatório para Product Identity.
- O computador precisa de conexão com a internet.
- No Railway, Google Lens fica desativado por padrão.
- No aplicativo Windows, Lens fica ativado por padrão.

## Fallbacks

Se Lens não estiver disponível:
1. busca textual restrita;
2. comparação de marca/modelo/características;
3. produto genérico não é enriquecido automaticamente sem confirmação forte.

## Próxima camada

Uma camada futura de embeddings visuais locais pode reconhecer o mesmo produto
em ângulos/fotos diferentes. O hash perceptual atual é deliberadamente forte
para a mesma foto ou foto de catálogo quase idêntica, evitando falsos positivos.
