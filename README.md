# monitor-DOE-RN
# 📰 Monitor DOE/RN — Diário Oficial do Estado do Rio Grande do Norte

Este projeto é um script de automação desenvolvido em **Python** para monitorar publicações do **Diário Oficial do Estado do Rio Grande do Norte — DOE/RN**.

A ferramenta verifica edições novas do Diário Oficial, baixa os arquivos em PDF, extrai o texto e procura termos definidos pelo usuário. Quando encontra uma nova publicação ou algum termo monitorado, envia um alerta pelo **Telegram** e, no Windows, também pode emitir um aviso sonoro.

O objetivo é ajudar servidores, professores, candidatos de concursos, advogados, estudantes e demais interessados a acompanhar publicações oficiais sem precisar consultar manualmente o Diário Oficial todos os dias.

---

## 🙏 Inspiração

Este projeto foi inspirado no repositório [juntaEstado](https://github.com/guteco/juntaEstado), desenvolvido por **Augusto Severo (Guteco)**, que criou uma ferramenta em Python para monitorar vagas de agendamento na Junta Médica do Rio Grande do Norte.

A ideia deste monitor do DOE/RN surgiu a partir da mesma necessidade prática: automatizar consultas repetitivas a serviços públicos e enviar alertas úteis ao usuário. Embora o objetivo e a lógica de funcionamento sejam diferentes, o projeto `juntaEstado` serviu como referência inicial de organização, simplicidade e uso de notificações via Telegram.

---

## ✨ Funcionalidades

* 🔎 Verifica publicações recentes do DOE/RN.
* 📅 Monitora apenas o dia atual e os últimos dias configurados.
* 📄 Localiza edições normais e extraordinárias em PDF.
* ⬇️ Baixa os PDFs encontrados.
* 🧠 Extrai o texto dos arquivos PDF.
* 📝 Procura termos cadastrados no arquivo `termos.txt`.
* 📢 Envia alertas pelo Telegram.
* 🔔 Emite alerta sonoro no Windows quando encontra termo monitorado.
* 🗂️ Mantém histórico local para evitar alertas repetidos.
* 📌 Mostra a data de publicação de cada PDF analisado.
* ✅ Informa quais termos foram encontrados em cada publicação.
* 💓 Pode enviar mensagem periódica de “estou ativo” para confirmar que o robô continua rodando.
* 🧾 Gera logs para facilitar conferência e solução de problemas.

---

## 📁 Estrutura do projeto

```text
monitor_doe_rn/
├── monitor_doe_rn.py          # Script principal
├── testar_telegram.py         # Teste simples de envio pelo Telegram
├── requirements.txt           # Dependências do projeto
├── .env.example               # Modelo de configuração
├── termos.txt                 # Lista de termos monitorados
├── instalar_dependencias.bat  # Instala as dependências no Windows
├── executar_monitor.bat       # Executa o monitor continuamente
├── testar_uma_vez.bat         # Faz apenas uma verificação
├── README.md                  # Instruções do projeto
├── LICENSE                    # Licença do projeto
└── .gitignore                 # Arquivos ignorados pelo Git
```

Durante o uso, o próprio sistema poderá criar também:

```text
estado.json     # Histórico local de PDFs já processados
downloads/      # Pasta onde os PDFs podem ser salvos
logs/           # Pasta onde os logs são armazenados
.env            # Arquivo local com token e chat_id do Telegram
```

> **Atenção:** o arquivo `.env` não deve ser publicado no GitHub.

---

## 🧰 Pré-requisitos

Antes de começar, você precisa ter:

* Python 3.10 ou superior instalado;
* conexão com a internet;
* uma conta no Telegram;
* um bot criado no Telegram pelo `@BotFather`.

Durante a instalação do Python no Windows, marque a opção:

```text
Add Python to PATH
```

Isso permite executar o comando `python` diretamente pelo Prompt de Comando, PowerShell, Git Bash ou terminal do VS Code.

---

## 🚀 Instalação

### Opção A — Download ZIP

1. Clique no botão verde **Code** no GitHub.
2. Escolha **Download ZIP**.
3. Extraia a pasta no seu computador.
4. Abra a pasta do projeto.

### Opção B — Git

Clone o repositório:

```bash
git clone https://github.com/SEU_USUARIO/monitor-DOE-RN.git
```

Entre na pasta:

```bash
cd monitor-DOE-RN
```

---

## 📦 Instalar dependências

### No Windows, modo fácil

Dê dois cliques no arquivo:

```text
instalar_dependencias.bat
```

Esse arquivo instalará automaticamente as dependências necessárias.

### Pelo terminal

Também é possível instalar manualmente:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

---

## 🤖 Configurar o Telegram

O monitor usa o Telegram para enviar alertas no celular.

### 1. Criar um bot

1. Abra o Telegram.
2. Procure por:

```text
@BotFather
```

3. Envie o comando:

```text
/newbot
```

4. Escolha um nome para o bot.
5. Escolha um nome de usuário para o bot, terminando com `bot`.

Exemplo:

```text
monitor_doe_rn_bot
```

6. O BotFather enviará um token parecido com:

```text
123456789:ABCDEF_seu_token_aqui
```

Guarde esse token.

---

### 2. Descobrir seu Chat ID

1. Abra uma conversa com o bot criado.
2. Envie qualquer mensagem para ele, por exemplo:

```text
teste
```

3. No navegador, acesse o endereço abaixo, trocando `SEU_TOKEN_AQUI` pelo token do seu bot:

```text
https://api.telegram.org/botSEU_TOKEN_AQUI/getUpdates
```

4. Procure no resultado algo parecido com:

```json
"chat":{"id":123456789}
```

Esse número é o seu `TELEGRAM_CHAT_ID`.

---

## ⚙️ Configuração do projeto

Na pasta do projeto existe um arquivo chamado:

```text
.env.example
```

Faça uma cópia dele e renomeie a cópia para:

```text
.env
```

Depois abra o arquivo `.env` e preencha:

```env
TELEGRAM_BOT_TOKEN=COLE_SEU_TOKEN_AQUI
TELEGRAM_CHAT_ID=COLE_SEU_CHAT_ID_AQUI
```

Exemplo:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCDEF_seu_token_aqui
TELEGRAM_CHAT_ID=987654321
```

Não use aspas.

---

## 🔐 Importante sobre segurança

Nunca publique no GitHub o arquivo:

```text
.env
```

Esse arquivo contém informações privadas, como o token do bot e o seu chat ID.

O projeto já possui um `.gitignore` para evitar que arquivos sensíveis sejam enviados ao GitHub, como:

```text
.env
estado.json
downloads/
logs/
```

Se você publicar acidentalmente o token do bot, gere um novo token no `@BotFather`.

---

## 📝 Configurar os termos monitorados

Abra o arquivo:

```text
termos.txt
```

Coloque um termo por linha.

Exemplo:

```text
SEEC
DIREC
nomeação
convocação
posse
```

Você também pode monitorar nomes completos, cargos, órgãos, matrículas, municípios ou expressões específicas.

Exemplo:

```text
MARIA DA SILVA
JOÃO PEREIRA
SECRETARIA DE ESTADO DA EDUCAÇÃO
CONCURSO PÚBLICO
DIÁRIO OFICIAL
```

Observações:

* o monitor ignora diferença entre maiúsculas e minúsculas;
* o monitor ignora acentos;
* linhas iniciadas com `#` são ignoradas;
* você pode alterar os termos quando quiser.

---

## 📅 Configurar período de busca

No arquivo `.env`, você pode definir quantos dias o monitor deve verificar.

Para verificar apenas o dia atual e os últimos 2 dias, deixe assim:

```env
DIAS_RETROATIVOS=2
DIAS_FUTUROS=0
```

Exemplo: se hoje for 10/07/2026, o monitor verificará:

```text
08/07/2026
09/07/2026
10/07/2026
```

Também é possível configurar a verificação de dias futuros, pois algumas edições do Diário Oficial podem ser disponibilizadas com data posterior à data de fechamento, como ocorre quando a edição de hoje é fechada à noite e publicada apenas no dia seguinte.

---

## ⏱️ Configurar intervalo entre buscas

No arquivo `.env`, ajuste:

```env
INTERVALO_MINUTOS=15
INTERVALO_VARIACAO_SEGUNDOS=60
```

Nesse exemplo, o monitor fará uma nova verificação aproximadamente a cada 15 minutos, com uma pequena variação aleatória.

Evite intervalos muito curtos para não sobrecarregar o site consultado.

---

## 📢 Tipos de aviso

No arquivo `.env`, você pode configurar os alertas:

```env
AVISAR_NOVA_EDICAO=true
AVISAR_SEM_TERMOS=false
ENVIAR_HEARTBEAT=true
HEARTBEAT_HORAS=6
```

### Explicação

```env
AVISAR_NOVA_EDICAO=true
```

Envia alerta quando uma nova edição for encontrada e analisada.

```env
AVISAR_SEM_TERMOS=false
```

Se estiver `false`, o monitor não envia aviso detalhado quando nenhum termo for encontrado.

```env
ENVIAR_HEARTBEAT=true
```

Envia mensagem periódica dizendo que o monitor continua ativo.

```env
HEARTBEAT_HORAS=6
```

Define de quantas em quantas horas o robô enviará a mensagem de atividade.

---

## 🧪 Testar o Telegram

Depois de configurar o `.env`, teste o envio de mensagem:

```bash
python testar_telegram.py
```

Ou:

```bash
python monitor_doe_rn.py --test-telegram
```

Se tudo estiver correto, você receberá uma mensagem no Telegram.

---

## 🔍 Fazer uma verificação única

Antes de deixar o monitor rodando continuamente, faça um teste único:

```bash
python monitor_doe_rn.py --once
```

No Windows, você também pode dar dois cliques em:

```text
testar_uma_vez.bat
```

Esse comando verifica as publicações recentes, analisa os PDFs encontrados e encerra o programa.

---

## ▶️ Rodar continuamente

Para deixar o monitor ativo, execute:

```bash
python monitor_doe_rn.py
```

No Windows, você também pode dar dois cliques em:

```text
executar_monitor.bat
```

Mantenha a janela aberta enquanto quiser que o monitor continue funcionando.

---

## 🖥️ Como usar no PyCharm

1. Abra o PyCharm.
2. Clique em **Open**.
3. Selecione a pasta do projeto.
4. Aguarde o PyCharm carregar os arquivos.
5. Abra o terminal interno do PyCharm.
6. Instale as dependências:

```bash
python -m pip install -r requirements.txt
```

7. Configure o arquivo `.env`.
8. Execute:

```bash
python monitor_doe_rn.py --once
```

Depois, para rodar continuamente:

```bash
python monitor_doe_rn.py
```

---

## 🗂️ Histórico de publicações

O monitor cria automaticamente o arquivo:

```text
estado.json
```

Esse arquivo guarda os PDFs já processados, evitando alertas repetidos.

Se você quiser forçar o reprocessamento de arquivos já analisados, altere no `.env`:

```env
REPROCESSAR_JA_LIDOS=true
```

Use isso apenas para testes.

Depois, volte para:

```env
REPROCESSAR_JA_LIDOS=false
```

Outra opção é apagar o arquivo `estado.json`, mas isso fará o monitor analisar novamente publicações que já tinham sido processadas.

---

## 📄 Exemplo de alerta enviado

Quando encontrar termos em uma publicação, o alerta será parecido com:

```text
🚨 Termos encontrados no DOE/RN

📄 Publicação: 12026-07-10.pdf
📅 Data de publicação: 10/07/2026

✅ Termos encontrados:
- SEEC
- nomeação
- Professor
- convocação

🔗 Link do PDF:
https://...
```

Quando apenas uma nova edição for encontrada, mas sem termos monitorados, o aviso poderá ser mais simples, dependendo da configuração escolhida.

---

## 🛠️ Principais arquivos

### `monitor_doe_rn.py`

Script principal do projeto. Ele faz a busca, baixa os PDFs, extrai texto, procura termos e envia alertas.

### `testar_telegram.py`

Script auxiliar para testar se o token e o chat ID estão funcionando.

### `termos.txt`

Arquivo onde o usuário informa os termos que deseja monitorar.

### `.env.example`

Modelo de configuração. Deve ser copiado e renomeado para `.env`.

### `.env`

Arquivo local de configuração. Não deve ser publicado.

### `estado.json`

Arquivo de histórico criado automaticamente. Não deve ser publicado.

---

## ❓ Problemas comuns

### O comando `python` não funciona

O Python pode não estar no PATH. Reinstale o Python e marque:

```text
Add Python to PATH
```

Ou tente:

```bash
py monitor_doe_rn.py
```

---

### Não recebo mensagem no Telegram

Verifique:

1. se o token está correto;
2. se o chat ID está correto;
3. se você enviou uma mensagem para o bot antes de usar o `getUpdates`;
4. se o arquivo `.env` está na mesma pasta do script;
5. se não há espaços extras no token ou no chat ID.

---

### O monitor não encontra termos

Verifique:

1. se o termo está no arquivo `termos.txt`;
2. se há uma publicação recente contendo o termo;
3. se o PDF foi lido corretamente;
4. se o arquivo já tinha sido processado antes.

Para testar novamente, use temporariamente:

```env
REPROCESSAR_JA_LIDOS=true
```

---

### O monitor avisa repetidamente sobre o mesmo PDF

Confira se o arquivo `estado.json` está sendo criado corretamente e se o programa tem permissão para salvar arquivos na pasta.

---

## ⚠️ Nota importante

Este projeto foi desenvolvido para fins educacionais e de utilidade pública, automatizando a consulta a publicações oficiais disponibilizadas publicamente.

Use com responsabilidade:

* não utilize intervalos de busca excessivamente curtos;
* não sobrecarregue o site consultado;
* não publique dados pessoais extraídos das publicações;
* não publique PDFs baixados automaticamente;
* respeite a LGPD e demais normas aplicáveis;
* mantenha tokens e credenciais em segurança.

O uso da ferramenta é de responsabilidade do usuário.

---

## 🤝 Contribuições

Sugestões, melhorias e correções são bem-vindas.

Você pode contribuir:

* abrindo uma issue;
* enviando um pull request;
* sugerindo novos recursos;
* melhorando a documentação;
* testando em diferentes ambientes.

Ideias futuras:

* interface gráfica simples;
* envio por e-mail;
* suporte a múltiplos chats do Telegram;
* painel web local;
* filtro por órgão;
* resumo automático das publicações encontradas.

---

## 📜 Licença

Este projeto está licenciado sob a licença MIT.

Você pode usar, modificar e compartilhar, desde que mantenha os créditos, respeite os termos da licença e não utilize para fins ilegais. 

---

## 👨‍💻 Créditos

Desenvolvido por **Thiago Barbosa**, com apoio da Inteligência Artificial pertencente a OpenAI, para auxiliar no acompanhamento de publicações do Diário Oficial do Estado do Rio Grande do Norte.

Se este projeto ajudou você, deixe uma estrela ⭐ no repositório.

