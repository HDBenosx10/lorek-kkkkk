# HubSpot Lotes — Windows

Aplicação simples para gerar contatos sintéticos segmentados no formulário da beta de Leonardo Lagoa.

## Baixar para usar

[Baixar HubSpotLotes.exe para Windows x64](https://github.com/HDBenosx10/lorek-kkkkk/releases/download/hubspot-lotes-v1.0.0/HubSpotLotes.exe)

[Release com pacote e instruções](https://github.com/HDBenosx10/lorek-kkkkk/releases/tag/hubspot-lotes-v1.0.0)

O executável já inclui o interpretador Python e as bibliotecas. Não exige Python instalado, conta no GitHub, login no HubSpot ou token de API. Requer Windows de 64 bits, Edge ou Chrome e internet. Foi validado no Windows 11. A prévia também precisa de internet para abrir a página pública.

Esta versão aponta para o formulário de Leonardo Lagoa; ela não configura formulários de outras contas. Usar **Enviar lote** envia contatos de teste para esse CRM. Para demonstrar ao cliente sem criar contatos, use **Prévia sem enviar**.

O executável não tem assinatura digital; o Windows pode apresentar aviso de editor desconhecido. Os hashes SHA-256 dos arquivos estão nos anexos da release.

## Executar

Abra `HubSpotLotes.exe`. Não precisa instalar Python. Requer conexão com a internet e Microsoft Edge ou Google Chrome instalado.

1. Marque Recrutador, Gestor(a) de Marketing, Colega de área e/ou Curioso.
2. Informe a quantidade total, entre 1 e 5.000. A distribuição é equilibrada; a diferença entre segmentos é de no máximo um contato.
3. Use **Prévia sem enviar** para ver o primeiro preenchimento e gerar um CSV sem criar contatos.
4. Use **Enviar lote** para criar os contatos de teste no HubSpot. O primeiro contato é preenchido e enviado em uma janela real do navegador. Os restantes são enviados pela Forms API, um por segundo, sem janelas adicionais.
5. Acompanhe os contadores. **Parar** interrompe os próximos envios; a requisição em andamento pode terminar.

O navegador fecha ao fim do lote. Enquanto ele está aberto, deixe a janela concluir o envio; fechá-la pode interromper a demonstração.

## Dados e relatórios

Cada contato possui nome com prefixo `TESTE`, sobrenome com sufixo `LOTE-<identificador>` e e-mail único `teste.<lote>.<sequência>@example.com`. São endereços de exemplo; não recebem mensagens. A aplicação não gera endereços de pessoas reais.

O CSV fica em `Documentos/HubSpotLotes/lote-<identificador>.csv`, com segmento, status e detalhe por contato processado. Contatos não tentados depois de uma interrupção não aparecem como enviados. O botão **Abrir relatório CSV** abre o arquivo no aplicativo padrão do Windows.

Para filtrar no HubSpot, use a propriedade **Você é…** / `origem_formulario_1`. Para localizar ou remover estes contatos depois, filtre nome começando com `TESTE` e sobrenome contendo o identificador `LOTE-...` do relatório. Os identificadores das opções foram conferidos no formulário original.

`aceito` significa que o formulário/API confirmou a recepção. Confira também no CRM se o contato foi classificado como spam e se as automações desejadas dispararam. Não há confirmação de entrega de e-mails.

## Falhas

Se o primeiro envio for recusado, o lote para antes de enviar o restante. Se a API retornar erro, limite de requisições ou falha de conexão, o lote também para. Não há reenvio automático: um timeout pode acontecer depois de o HubSpot já ter aceitado o contato.

Se o HubSpot bloquear o domínio `example.com`, revise as restrições do formulário ou use a prévia. A aplicação não ignora consentimento, CAPTCHA ou regras de validação. Uma alteração nesses campos no HubSpot exige atualizar a aplicação.

## Implementação

Python + Tkinter para a interface; Playwright com Edge/Chrome para o primeiro contato; biblioteca padrão do Python para as requisições restantes. Sem token ou senha. O destino está fixado no formulário autorizado, portal 51906766 / formulário c2ff372a-85ba-40e0-8f90-18badde87196.

Código em `app.py`; dependências em `requirements.txt`. Para reconstruir no Windows:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe -m PyInstaller --onefile --windowed --collect-all playwright --name HubSpotLotes app.py
```

## Validação desta entrega

Testes de geração/distribuição, identificadores, e-mails únicos, quantidades inválidas, falhas HTTP e limites. Teste com navegador real contra um servidor local: primeiro envio visível + restantes pela API, prévia sem requisições e interrupção na primeira falha. Nenhum lote foi enviado ao HubSpot de produção durante o desenvolvimento.

O executável também passou no teste de inicialização da interface Tkinter e acionamento do Edge empacotado com Playwright, sem requisições externas. Os seis testes podem ser executados com `python test_app.py` após instalar as dependências.
