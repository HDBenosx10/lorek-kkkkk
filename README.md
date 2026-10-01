# Leonardo Lagoa — Portfólio

Site estático publicado em https://portifolio-leonardo-lagoa.pages.dev.

## Páginas

- `/`: versão principal (`index.html`, `styles.css`, `main.js`).
- `/beta`: proposta de design (`beta.html`, `beta.css`, `beta.js`). Não aparece na navegação da página principal e contém `noindex, nofollow`. A rota é pública para quem tem o endereço.

O Cloudflare Pages serve `beta.html` em `/beta` sem configurar um roteador.

## Estrutura

HTML semântico, CSS com tokens de identidade visual e JavaScript sem dependências. A beta tem estilos próprios para manter a página principal independente. Os filtros melhoram progressivamente a lista de projetos; os detalhes usam o elemento nativo `details`. Sem JavaScript, os projetos permanecem visíveis.

O `main.js` compartilha o relógio e o acompanhamento do carregamento do formulário HubSpot. O embed utiliza o portal e o formulário fornecidos pelo proprietário do site. As regras, os campos e as automações do formulário são gerenciados no HubSpot.

## Publicação

Sem build. Publique os arquivos HTML, CSS e JavaScript na raiz do projeto Pages. O projeto utiliza upload direto; commits no GitHub não iniciam um deploy automático.

Para revisar localmente, use qualquer servidor HTTP estático que ofereça URLs de HTML sem extensão. Abrir o arquivo diretamente pelo protocolo `file:` não resolve os caminhos absolutos da beta.

## Verificação

Antes de publicar, confira as versões desktop e móvel, filtros, links de detalhes, navegação por teclado e carregamento do formulário. Valide o JavaScript com `node --check main.js` e `node --check beta.js`.

Não envie dados fictícios ao formulário de produção durante a revisão visual. Um teste real de contato é necessário para verificar o envio e as automações do CRM.
