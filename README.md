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

O GitHub Actions valida e publica automaticamente mudanças do front-end na branch `main` no projeto `portifolio-leonardo-lagoa`. Pull requests executam a validação sem publicar. O pacote inclui somente os sete arquivos públicos do site. Após o deploy, o pipeline verifica o conteúdo publicado e a rota `/beta`.

Para revisar localmente, use qualquer servidor HTTP estático que ofereça URLs de HTML sem extensão. Abrir o arquivo diretamente pelo protocolo `file:` não resolve os caminhos absolutos da beta.

## Verificação

Antes de publicar, confira as versões desktop e móvel, filtros, links de detalhes, navegação por teclado e carregamento do formulário. Valide o JavaScript com `node --check main.js` e `node --check beta.js` e `node --check beta-form.js`.

Não envie dados fictícios ao formulário de produção durante a revisão visual. Um teste real de contato é necessário para verificar o envio e as automações do CRM.

## Aplicativo Windows de teste

O [HubSpot Lotes](tools/hubspot-lotes/README.md) gera contatos sintéticos por segmento e demonstra o primeiro envio no navegador. O código fica em `tools/hubspot-lotes/`, separado dos arquivos do site. Ele não é carregado pela página nem faz parte do pacote de deploy do Cloudflare.

[Baixar o aplicativo para Windows x64](https://github.com/HDBenosx10/lorek-kkkkk/releases/latest). O executável inclui Python e dependências. A aba Config permite alterar URL, IDs, modos e sincronizar a definição do formulário. Modos em tela usam Edge/Chrome; Todos via API dispensa navegador. A prévia não cria contatos. O envio de lote cria contatos de teste no formulário deste portfólio.

## CI/CD

Workflows em `.github/workflows/`: **Portfolio - Cloudflare Pages** e **HubSpot Lotes - Windows**. Ambos também oferecem **Run workflow** na aba Actions.

O workflow Windows executa os testes com formulários locais, compila com Python 3.14/PyInstaller e abre o executável em teste para conferir interface, Config e navegador. Cada alteração no app gera artefatos para download (retenção de 30 dias). Nenhum teste envia contatos ao CRM.

Para publicar uma nova versão, atualize `VERSION` em `tools/hubspot-lotes/engine.py`, faça commit e envie uma tag correspondente, como `hubspot-lotes-v1.2.0`. A release recebe automaticamente o `.exe`, o ZIP para o cliente e hashes SHA-256. Pelo botão Run workflow, `release_tag` vazio só gera artefatos; preenchido publica a versão correspondente. Reexecutar uma release substitui os assets de mesmo nome.

O deploy usa os secrets `CLOUDFLARE_ACCOUNT_ID` e `CLOUDFLARE_API_TOKEN`, já configurados no repositório. O token exclusivo `github-lorek-pages-deploy` tem somente Pages Write nesta conta. Para trocar a credencial, atualize o secret no GitHub; nunca coloque tokens no código. Permissão de escrita no GitHub fica restrita ao job de release.

Para verificar o site localmente: `node scripts/site.mjs`. Para conferir o deploy: `node scripts/site.mjs verify https://portifolio-leonardo-lagoa.pages.dev`. Se uma validação falhar, o workflow interrompe a publicação e deixa o erro na aba Actions.
