# nmGET

**Number Map Get** — captura e organização de números de telefone do **Google Maps** para montar listas de contatos.

![License](https://img.shields.io/badge/licen%C3%A7a-GPL--3.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab.svg)
![Flask](https://img.shields.io/badge/Flask-3.x-000000.svg)
![SQLite](https://img.shields.io/badge/banco-SQLite-003b57.svg)

---

## 📸 Screenshots

Capturas de tela do projeto (uma abaixo da outra).

<!-- Para trocar as fotos, basta substituir os endereços em src abaixo. -->

<img alt="Dashboard - nmGET" src="https://github.com/user-attachments/assets/2a7d7a89-de65-49ae-923c-bd59447785b4">
<img alt="Geração de script - nmGET" src="https://github.com/user-attachments/assets/36b3d14d-f06c-40b5-9610-8e3e4f5ec403">
<img alt="Listas de contatos - nmGET" src="https://github.com/user-attachments/assets/b577c98b-fb89-42d7-bb97-7eecad0b9218">
<img alt="Configurações - nmGET" src="https://github.com/user-attachments/assets/a5078d3e-19ac-4307-b078-46b31d7c1c3b">

---

## 📖 Apresentação

**nmGET** significa **Number Map Get**: a aplicação foi pensada, originalmente, para **extrair dados
do Google Maps** — como números de telefone de estabelecimentos exibidos na página. Ainda hoje a
principal forma de uso é abrir o Google Maps, colar o script gerado no console do navegador e capturar
os números visíveis na região exibida.

O nmGET gera um **script JavaScript** que coleta números de telefone de uma página web e os envia a um
servidor, onde ficam organizados por **etiquetas (tags)**. **Futuras atualizações pretendem generalizar**
a ferramenta para outras páginas de raspagem de números, além do Google Maps.

Com os números capturados você pode:

- acompanhar o volume de capturas em um **dashboard** com gráficos;
- gerenciar uma **fila de captura** por etiqueta;
- gerar **listas de contatos clicáveis** no formato `wa.me` (WhatsApp), com visual claro ou escuro;
- **exportar e importar** o banco de dados.

### Por que foi desenvolvido?

Este projeto foi desenvolvido com **fins de estudo** de desenvolvimento web: Flask, SQLite,
JavaScript vanilla, integração entre cliente e servidor (via API JSON), gráficos com Chart.js e
navegação por htmx. Ele é **totalmente funcional e utilizável**, mas foi criado em um contexto
educacional.

### ⚠️ Aviso de responsabilidade

> Este software é fornecido **apenas para fins de estudo e aprendizagem**. O autor
> **não se responsabiliza** por qualquer uso indevido, ilegal ou contrário aos termos de
> serviço de terceiros. Utilize-o somente em páginas que você controla ou para as quais
> possui autorização.

---

## ✨ Funcionalidades

- **Geração de script de captura** — escolha a etiqueta e o tempo de execução (10s até 1h) e copie um script JS pronto.
- **Captura via Google Maps** — o script é colado no console do navegador na página do Google Maps e coleta os números visíveis no mapa. Futuras atualizações vão generalizar para outras páginas.
- **Etiquetas (tags)** — crie, selecione e exclua etiquetas para organizar os contatos.
- **Dashboard** — total de números, capturados hoje, última captura e gráficos (status, por etiqueta, por dia).
- **Fila de captura** — números aguardando, com ações de enviar (movem para a base de contatos) e excluir.
- **Gerador de listas** — gera arquivo HTML com links `wa.me` clicáveis, marca como enviados e mostra quem já foi acessado.
- **Exportar/Importar** — baixe ou restaure o banco de dados inteiro.
- **Extras técnicos** — CORS liberado, compressão gzip, SQLite em modo WAL, cache de consultas, tema escuro e efeito Matrix.

## 🛠️ Tecnologias

| Camada      | Tecnologia                                      |
|-------------|-------------------------------------------------|
| Backend     | Python 3.10+ com Flask 3.x                      |
| Banco       | SQLite (modo WAL, índices otimizados)           |
| Frontend    | HTML, CSS e JavaScript vanilla                  |
| Auxiliares  | htmx (navegação), Chart.js (gráficos)           |

---

## 🚀 Instalação

### Pré-requisitos

- **Python 3.10 ou superior** — verifique com `python3 --version`.
- **git** — para clonar o repositório (opcional se você baixar o zip).
- Nenhum banco de dados externo é necessário: o SQLite é criado automaticamente na primeira execução.

### Passo a passo

**1. Clone o repositório**

```bash
git clone git@github.com:DaFi-1/nmget.git
cd nmget
```

> Se preferir, use HTTPS: `git clone https://github.com/DaFi-1/nmget.git`

**2. Crie um ambiente virtual**

```bash
python3 -m venv venv
```

**3. Ative o ambiente virtual**

Linux/macOS:

```bash
source venv/bin/activate
```

Windows (PowerShell):

```powershell
venv\Scripts\Activate.ps1
```

**4. Instale as dependências**

```bash
pip install -r requirements.txt
```

**5. Inicie o servidor**

```bash
python main.py
```

Você verá no terminal a URL do servidor de desenvolvimento.

**6. Acesse a aplicação**

Abra no navegador: <http://127.0.0.1:5000>

O banco de dados (`instance/nmget.db`) é criado automaticamente no primeiro acesso.

### Rodando em produção (opcional)

Para um servidor de produção com Gunicorn:

```bash
pip install gunicorn
gunicorn -w 2 -b 127.0.0.1:5000 main:app
```

---

## 📖 Como usar

A aplicação possui 4 páginas acessíveis pela barra lateral (com o efeito Matrix ao fundo).

### 1. Dashboard (início)

Mostra o panorama geral das capturas:

- **Cards no topo** — total de números capturados, capturados hoje e data/hora da última captura.
- **Gráfico "Overall status"** — proporção entre números pendentes (`ON`) e enviados (`OFF`).
- **Gráfico "Status by tag"** — barras empilhadas com pendentes/enviados por etiqueta.
- **Gráfico "Numbers by tag"** — volume total de cada etiqueta.
- **Gráfico "Captures per day"** — linha com o número de capturas por dia.

Os dados são atualizados automaticamente a cada poucos segundos.

### 2. Nmget — captura de números (função principal)

Esta é a tela central do projeto. O fluxo é:

**a) Escolha ou crie a etiqueta**

Na seção **Add tag**, digite o nome e clique em **Add**. A nova etiqueta passa a constar na lista.

**b) Configure a captura**

Na seção **Configuration**:

- **Tag** — selecione a etiqueta que receberá os números.
- **Duration** — por quanto tempo o script deve capturar (10s, 20s, 60s, 5m, 10m, 30m ou 1h).

Clique em **Activate script**. O campo **Generated script** será preenchido com um bloco de
código JavaScript pronto.

**c) Copie o script**

Clique em **Copy**. O script vai para a área de transferência.

**d) Execute no Google Maps**

Abra a página do **Google Maps** (https://maps.google.com) com os estabelecimentos que deseja
capturar e cole o script no **Console do navegador** (F12 → Console) e pressione Enter.
Alternativamente, injete o código na própria página.

> O script lê os números que estão **visíveis na tela** (na região do mapa exibida). Role o mapa para
> carregar mais resultados e refaça a varredura dentro do tempo escolhido.
>
> Esta é a única página de raspagem implementada até o momento. **Futuras atualizações vão
> generalizar o nmGET para outras páginas de captura de números.**

O script irá:

1. varrer a página por números de telefone (10 a 13 dígitos);
2. agrupar os números únicos e deduplicá-los;
3. enviá-los ao servidor na etiqueta escolhida (via `POST /phones`);
4. repetir a varredura a cada ~2s até o tempo escolhido expirar.

> O navegador precisa estar com o Google Maps **aberto** durante a captura.

**e) Acompanhe a fila**

A seção **Capture queue** lista, por etiqueta, quantos números aguardam. Ações disponíveis:

- **Send all** — move todos os números da fila para a base de contatos (status `ON`, pendentes).
- **Delete all** — remove os números da fila.
- Por etiqueta — botões de envio/exclusão individuais.

**f) Exclua etiquetas**

A seção **Current tag** mostra a etiqueta ativa; **Delete tag** remove a etiqueta atual
(a etiqueta padrão `EMPTY` não pode ser excluída).

### 3. Ngenerate — gerar listas de contatos

Transforma os números capturados em uma lista clicável de WhatsApp.

1. Selecione a **etiqueta** e a **quantidade** de números (máx. 5.000).
2. Clique em **Generate** — a lista é montada e exibida no **Preview**.
3. Escolha o tema (claro/escuro) e clique em **Download**.

O arquivo baixado é um HTML autossuficiente que:

- lista cada número como um link `wa.me` (abre conversa no WhatsApp);
- abre no padrão internacional (+55 Brasil);
- **marca como acessado** os links clicados (fica riscado, usando o armazenamento local) para você não clicar duas vezes.

> Ao baixar uma lista, os números correspondentes são marcados como **enviados** (`OFF`) no banco.

### 4. Config — exportar e importar dados

- **Export database** — baixa o arquivo `nmget.db` completo (com checkpoint do WAL para garantir consistência).
- **Import database** — envia um arquivo `.db` para substituir o atual. O banco é validado antes de
  aplicar e uma cópia de segurança (`nmget.db.bak`) é mantida.

---

## 🔌 API (referência)

| Método | Rota                  | Descrição                                              |
|--------|-----------------------|--------------------------------------------------------|
| GET    | `/`                   | Redireciona para `/dashboard`                          |
| GET    | `/dashboard`          | Página do dashboard                                    |
| GET    | `/dashboard/data`     | JSON com as estatísticas                               |
| GET    | `/nmget`              | Página de captura (também aceita `POST` p/ criar tag)  |
| GET    | `/tag/current`        | Etiqueta ativa                                          |
| DELETE | `/tag/current`        | Exclui a etiqueta ativa                                |
| GET    | `/tags`               | Lista as etiquetas                                     |
| POST   | `/tags`               | Cria uma etiqueta                                      |
| GET    | `/ngenerate`          | Página geradora de listas                              |
| GET    | `/ngenerate/tags`     | Contagens pendentes por etiqueta                       |
| POST   | `/ngenerate/generate` | Gera a lista de números                                |
| POST   | `/ngenerate/download` | Baixa a lista HTML e marca como enviados               |
| POST   | `/phones`             | Recebe números capturados (CORS liberado)              |
| GET    | `/queue`              | Fila de captura por etiqueta                           |
| POST   | `/queue/send`         | Envia a fila para a base de contatos                   |
| POST   | `/queue/clear`        | Limpa a fila                                           |
| GET    | `/config`             | Página de configuração                                 |
| GET    | `/config/export`      | Baixa o banco de dados                                 |
| POST   | `/config/import`      | Importa um banco de dados                              |

### Exemplo de envio de números (`/phones`)

```bash
curl -X POST http://127.0.0.1:5000/phones \
  -H "Content-Type: application/json" \
  -d '{"tag": "campaign", "phones": ["83999991111", "83988882222"]}'
```

---

## 📁 Estrutura do projeto

```
nmget/
├── app/
│   ├── __init__.py        # fábrica da aplicação + middleware gzip
│   ├── db.py              # camada de banco (SQLite) e modelos
│   └── views/             # blueprints: dashboard, nmget, ngenerate, phones, queue, config
├── static/
│   ├── css/style.css      # estilos da interface
│   ├── js/                # app.js e scripts por página
│   └── vendor/            # bibliotecas locais (htmx, chart.js)
├── templates/
│   ├── layouts/base.html  # layout base (barra lateral, matrix rain)
│   └── pages/             # dashboard, nmget, ngenerate, config
├── instance/              # banco de dados SQLite (criado em tempo de execução)
├── main.py                # ponto de entrada
├── requirements.txt       # dependências
└── LICENSE                # GNU GPL v3
```

---

## ⚖️ Licença

Este projeto é distribuído sob a **GNU General Public License v3.0**. Veja o arquivo
[LICENSE](LICENSE) para os detalhes completos.

Resumo: você pode usar, estudar, modificar e redistribuir, desde que mantenha a mesma
licença e informe as alterações. Não há garantias — o software é fornecido "como está".

---

## ⚠️ Aviso legal

**Este projeto foi desenvolvido para fins de estudo.** É um software funcional, porém o autor
**não se responsabiliza** por uso indevido, captura de dados sem autorização ou qualquer violação
de termos de serviço ou legislação. Use por sua conta e risco e apenas onde for permitido.
