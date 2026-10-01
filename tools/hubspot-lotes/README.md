# HubSpot Lotes — Windows

[Baixar a versão atual para Windows x64](https://github.com/HDBenosx10/lorek-kkkkk/releases/latest).

O `.exe` inclui Python e bibliotecas. Não precisa instalar Python, fazer login no GitHub/HubSpot ou informar token. Para modos em tela, tenha Edge ou Chrome; Todos via API funciona sem navegador instalado. Todos os modos precisam de internet quando usam uma página ou formulário remoto. Validado no Windows 11. O executável não tem assinatura digital; o Windows pode mostrar aviso de editor desconhecido. Confira os hashes SHA-256 anexos à release.

## Lotes e Config

Na aba **Lotes**, escolha segmentos e quantidade total (1 a 5.000). Os contatos têm nomes `TESTE`, sobrenomes com `LOTE-<identificador>` e e-mails únicos em `example.com`, sem destinatários reais.

A aba **Config** permite alterar:

- URL da página, Portal ID e Form ID HubSpot. **Identificar IDs pela URL** tenta ler os identificadores do embed ou de scripts locais com o endpoint da Forms API. Se houver vários formulários ou a integração não estiver exposta no HTML, informe os IDs manualmente.
- Modo: **Primeiro em tela + restantes via API**, **Todos em tela** ou **Todos via API**.
- Intervalo entre contatos (1 a 60 segundos), pausa por campo (0 a 10 segundos) e navegador.
- Sincronização antes de cada lote e parada em erros de validação.
- Propriedade de segmentação, valores adicionais e seletores CSS para páginas com HTML diferente.

Clique em **Salvar configuração**. As preferências e a última definição sincronizada ficam em `%APPDATA%/HubSpotLotes/config.json`, fora do executável. Não é necessário recompilar para mudar essas preferências.

**Prévia sem enviar** não faz POST de contatos. No modo Todos em tela, preenche cada contato em sequência sem enviar. No modo misto, apenas o primeiro aparece no navegador; os demais são validados e registrados no CSV. No modo Todos via API, valida os dados e gera o CSV sem abrir navegador. A leitura/sincronização da definição usa GET e pode ocorrer durante a prévia.

**Enviar lote** cria contatos de teste no destino configurado. O modo em tela preenche de verdade a página e observa a resposta do envio. O app bloqueia POSTs da página que apontem para IDs diferentes dos configurados; não os redireciona. Ele suporta o envio direto da Forms API e o envio do embed HubSpot. Um front-end com proxy próprio requer adaptação.

## Quando o formulário mudar

**Sincronizar campos e opções** lê a definição pública do formulário HubSpot. Com sincronização antes de cada lote ativada (padrão), as opções e os identificadores internos são atualizados antes de gerar os contatos.

- Rótulos ou valores de segmentos alterados aparecem após a sincronização. Se um segmento selecionado desaparecer, o lote para para você selecionar novamente.
- Campos removidos deixam de ser enviados. Campos opcionais novos ficam vazios por padrão.
- Campos obrigatórios novos impedem o envio até configurar um valor em **Valores adicionais**. Exemplo: `{"company":"TESTE Empresa"}`. Para escolhas, use o valor interno apresentado na definição sincronizada. O app não inventa valores de negócio.
- Consentimento, CAPTCHA, arquivos, pagamentos e regras condicionais detectados na definição bloqueiam o envio para revisão. Regras não expostas pela definição ainda podem ser recusadas pelo HubSpot; o app não ignora a validação do servidor.
- A definição pública precisa estar disponível para sincronização automática. Se o endpoint mudar, ficar indisponível ou o formulário não for compatível, a leitura falha e a configuração anterior é preservada. Com sincronização automática ativada, o lote não prossegue usando dados antigos.

A sincronização atualiza **o aplicativo**. Ela não reescreve o HTML nem o JavaScript de seu site. Na beta atual, os campos e opções do formulário nativo são definidos no código do front-end. Se mudar campos/valores no HubSpot, o site também precisa ser atualizado para os envios em tela refletirem essa mudança. Os envios pela API usam a definição recém-sincronizada.

## Seletores de páginas diferentes

Campos sem seletor explícito são encontrados pelos atributos `name="propriedade"` ou `name="0-1/propriedade"`. Isso acompanha mudanças de IDs e classes quando os nomes internos permanecem iguais. Se o HTML não tiver nomes correspondentes, ajuste o JSON de seletores na aba Config. Não precisa recompilar:

```json
{
  "frame": "",
  "form": "form",
  "firstname": "",
  "lastname": "",
  "email": "",
  "segment": "",
  "submit": "button[type=\"submit\"], input[type=\"submit\"]",
  "success": "#contact-success",
  "status": "#native-status"
}
```

`frame` é um seletor de iframe, quando necessário; vazio usa a página principal ou tenta um único iframe HubSpot com título Form. `form` precisa encontrar um único formulário dentro desse escopo. Para um campo adicional, adicione sua propriedade como chave e o seletor como valor. Páginas com controles personalizados podem precisar de adaptação de código; nem toda UI funciona como um input/select nativo.

## Relatórios e erros

O CSV fica em `Documentos/HubSpotLotes/lote-<identificador>.csv`. Há segmento, status e detalhe por contato processado. **Parar** impede os próximos envios; a operação em andamento pode terminar. O navegador fecha ao final.

O primeiro envio em tela deve funcionar antes de continuar no modo misto. Erros de limite HTTP 429 e resultados incertos sempre interrompem o lote. A configuração permite continuar após recusas de validação conhecidas nos envios pela API. Não há repetição automática: um timeout pode acontecer depois da aceitação.

`aceito` confirma a resposta do formulário/API; confira também a classificação de spam e as automações no HubSpot. Os e-mails de exemplo não recebem confirmações. Para localizar e limpar os contatos, use o prefixo TESTE e o identificador LOTE do CSV.

## Código e reconstrução

`app.py`: interface Tkinter. `engine.py`: configuração, sincronização, geração e envio. `test_app.py`: testes locais sem contatos em produção. `requirements.txt`: dependências. Os arquivos ficam em `tools/hubspot-lotes/`, separados do site e excluídos do pacote de deploy Cloudflare.

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe test_app.py
.venv/Scripts/python.exe -m PyInstaller --onefile --windowed --collect-all playwright --name HubSpotLotes app.py
```

A leitura de configuração pública do HubSpot não exige token e não utiliza APIs privadas da conta. Ela pode mudar no futuro. O transporte HTTPS usa a validação de certificados do Windows; não desativa TLS.

## Validação

17 testes cobrem os três modos, prévias sem envio, distribuição/identificadores, persistência, atualização das opções, campos removidos/obrigatórios, bloqueios, interrupção e continuação em erros de validação. Testes com navegador real usam servidor local e respostas interceptadas, sem enviar contatos ao HubSpot. A sincronização e a descoberta de IDs foram verificadas na página e no formulário públicos. O executável é validado separadamente com a aba Config e o driver Edge.



## Build e releases automáticos

O GitHub Actions testa e compila o app a cada alteração na branch main. Tags hubspot-lotes-vX.Y.Z, correspondentes a VERSION no engine.py, publicam o executável, ZIP e SHA-256 automaticamente. Consulte CI/CD no README da raiz. A versão 1.1.1 inaugura a distribuição pelo pipeline.

