# Leonardo Lagoa — Portfólio

Site estático publicado em https://portifolio-leonardo-lagoa.pages.dev.

## Páginas

- `/`: versão principal (`index.html`, `styles.css`, `main.js`).
- `/beta`: proposta de design (`beta.html`, `beta.css`, `beta.js`, `beta-form.js`). Não aparece na navegação da página principal e contém `noindex, nofollow`. A rota é pública para quem tem o endereço.

O Cloudflare Pages serve `beta.html` em `/beta` sem configurar um roteador.

## Estrutura

HTML semântico, CSS com tokens de identidade visual e JavaScript sem dependências. A beta tem estilos próprios para manter a página principal independente. Os filtros melhoram progressivamente a lista de projetos; os detalhes usam o elemento nativo `details`. Sem JavaScript, os projetos permanecem visíveis.

O `main.js` compartilha o relógio; na página principal também acompanha o embed HubSpot. Na beta, `beta-form.js` envia o formulário nativo diretamente à Forms API pública, sem token. O portal é `51906766` e o formulário é `c2ff372a-85ba-40e0-8f90-18badde87196`.

O mapeamento foi conferido na definição pública do formulário: `firstname`, `lastname`, `email` (obrigatório) e `origem_formulario_1`. As opções Recrutador e Gestor(a) de Marketing têm identificadores internos próprios. Não troque os valores pelo texto do rótulo. Se campos, opções, consentimento ou CAPTCHA forem alterados no HubSpot, atualize esta integração também. A interface oferece o formulário original como alternativa.

O envio apresenta sucesso apenas após resposta HTTP aceita, impede envios simultâneos e mantém os campos após falhas. Não há repetição automática, armazenamento local de contatos nem inscrição presumida em marketing. A página é enviada como contexto, sem query string. Cadastre o domínio no HubSpot para evitar classificação de spam. O teste com um contato real e a confirmação das automações devem ser feitos pelo proprietário.

## Publicação

Sem build. Publique os arquivos HTML, CSS e JavaScript na raiz do projeto Pages. O projeto utiliza upload direto; commits no GitHub não iniciam um deploy automático.

Para revisar localmente, use qualquer servidor HTTP estático que ofereça URLs de HTML sem extensão. Abrir o arquivo diretamente pelo protocolo `file:` não resolve os caminhos absolutos da beta.

## Verificação

Antes de publicar, confira as versões desktop e móvel, filtros, links de detalhes, navegação por teclado e carregamento do formulário. Valide o JavaScript com `node --check main.js` e `node --check beta.js` e `node --check beta-form.js`.

Não envie dados fictícios ao formulário de produção durante a revisão visual. Um teste real de contato é necessário para verificar o envio e as automações do CRM.
