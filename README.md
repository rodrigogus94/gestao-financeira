# Gestão Financeira — Guia passo a passo

Este documento descreve como montar o projeto do zero, em ordem. Use-o como roteiro de estudo: siga os passos na sequência para entender a estrutura e os comandos em cada ambiente (PowerShell no Windows e Bash em Linux/macOS ou Git Bash).

---

## Visão geral da estrutura

Antes de executar os comandos, convém saber como o projeto fica organizado:

```
backend/app/
├── __init__.py
├── main.py
├── core/
│   └── __init__.py
├── models/
│   ├── __init__.py
│   └── domain/
├── services/
│   ├── __init__.py
│   ├── ia/providers/
│   └── ocr/
├── api/
│   ├── __init__.py
│   └── routes/
└── scripts/

frontend/
├── streamlit_app.py
├── api_client.py
└── components/

tests/
docs/

.env.example  Makefile  setup.sh  docker-compose.yml
```

- **backend/app** — aplicação principal (core, modelos, serviços, API).
- **frontend** — interface (Streamlit) e cliente da API.
- **tests** — testes automatizados.
- **docs** — documentação adicional.
- **Raiz** — configuração (ambiente, Makefile, setup, Docker).

---

## Passo 1 — Criar a pasta do projeto

Abra o terminal na pasta onde você quer o projeto (por exemplo, `Projetos`) e crie a pasta do repositório:

**PowerShell:**

```powershell
New-Item -ItemType Directory -Force -Path "gestao-financeira"
```

- **New-Item** — cmdlet que cria um novo item (arquivo, pasta, etc.).
- **-ItemType Directory** — indica que o item a criar é uma pasta (diretório).
- **-Force** — cria a pasta mesmo que algum nível do caminho não exista; se a pasta já existir, o comando não gera erro.
- **-Path "gestao-financeira"** — caminho da pasta a criar (relativo ao diretório atual).

**Bash:**

```bash
mkdir -p gestao-financeira
```

- **mkdir** — comando para criar diretórios.
- **-p** — cria todas as pastas necessárias no caminho (parents); se a pasta já existir, não gera erro.

Entre na pasta:

```powershell
cd gestao-financeira
```

- **cd** — muda o diretório atual para o indicado (funciona no PowerShell e no Bash).

---

## Passo 2 — Criar a estrutura de pastas do backend

Execute **um** dos blocos abaixo, conforme seu terminal.

### No PowerShell (Windows)

```powershell
New-Item -ItemType Directory -Force -Path "backend/app/core", "backend/app/models/domain", "backend/app/services/ia/providers", "backend/app/services/ocr", "backend/app/api/routes"
```

- **New-Item** — cria novos itens no sistema de arquivos.
- **-ItemType Directory** — define que cada item criado é uma pasta.
- **-Force** — cria todas as pastas intermediárias necessárias (ex.: `backend`, `backend/app`, `backend/app/services/ia`) e não gera erro se alguma pasta já existir.
- **-Path "..., ..., ..."** — lista de caminhos separados por vírgula; cada um é criado como pasta. No PowerShell não se usa `{ }` para expandir vários caminhos, por isso os caminhos são listados um a um.

### No Bash (Git Bash, WSL, Linux ou macOS)

```bash
mkdir -p backend/app/{core,models/domain,services/{ia/providers,ocr},api/routes}
```

- **mkdir** — comando para criar diretórios.
- **-p** — cria os “parents” (pastas intermediárias) quando necessário e não gera erro se a pasta já existir.
- **`{core,models/domain,...}`** — expansão de chaves: o Bash substitui por vários argumentos (ex.: `core`, `models/domain`, etc.), e o `mkdir` recebe vários caminhos em um único comando.

**Esclarecimento:** No PowerShell, as chaves `{ }` são usadas para blocos de script, não para expandir listas. Por isso, no PowerShell os caminhos devem ser escritos explicitamente no `-Path`, separados por vírgula.

---

## Passo 3 — Criar as pastas de scripts, testes, frontend e documentação

Crie as pastas `backend/scripts`, `tests`, `frontend/components` e `docs`.

### No PowerShell

```powershell
New-Item -ItemType Directory -Force -Path "backend/scripts", "tests", "frontend/components", "docs"
```

- **New-Item -ItemType Directory** — cria pastas.
- **-Force** — cria pastas intermediárias (ex.: `backend` para `backend/scripts`, `frontend` para `frontend/components`) e não falha se a pasta já existir.
- **-Path "..., ..., ..."** — vários caminhos em um único comando, separados por vírgula.

### No Bash

```bash
mkdir -p backend/scripts tests
mkdir -p frontend/components
mkdir -p docs
```

- **mkdir -p** — cria as pastas e, se precisar, as pastas pai (`-p`).
- Vários caminhos no mesmo comando são separados por **espaço** (ex.: `backend/scripts` e `tests` no primeiro comando).

---

## Passo 4 — Criar toda a estrutura de pastas de uma vez (opcional)

Se preferir um único comando para todas as pastas (backend + scripts, tests, frontend, docs):

### No PowerShell

```powershell
New-Item -ItemType Directory -Force -Path "backend/app/core", "backend/app/models/domain", "backend/app/services/ia/providers", "backend/app/services/ocr", "backend/app/api/routes", "backend/scripts", "tests", "frontend/components", "docs"
```

### No Bash

Use os comandos dos passos 2 e 3 em sequência, ou combine conforme a sintaxe do passo 2.

---

## Passo 5 — Criar os arquivos iniciais do projeto

Crie os arquivos vazios que marcam módulos e pontos de entrada. No Bash isso costuma ser feito com `touch`; no PowerShell use `New-Item -ItemType File -Force`.

### No PowerShell

```powershell
New-Item -ItemType File -Force -Path "backend/app/__init__.py", "backend/app/main.py", "backend/app/core/__init__.py", "backend/app/models/__init__.py", "backend/app/services/__init__.py", "backend/app/api/__init__.py", "frontend/streamlit_app.py", "frontend/api_client.py", ".env.example", "Makefile", "setup.sh", "docker-compose.yml"
```

- **New-Item** — cria novos itens (aqui, arquivos).
- **-ItemType File** — indica que cada item é um arquivo.
- **-Force** — cria pastas intermediárias se faltarem e, **em arquivos**, sobrescreve o arquivo se ele já existir (o conteúdo é substituído por vazio). Use com cuidado em arquivos que já têm conteúdo.
- **-Path "..., ..., ..."** — lista de caminhos de arquivos a criar, separados por vírgula.

Para apenas atualizar a data de modificação de um arquivo (por exemplo `README.md`) sem alterar o conteúdo:

```powershell
(Get-Item "README.md").LastWriteTime = Get-Date
```

- **Get-Item "README.md"** — obtém o objeto que representa o arquivo.
- **.LastWriteTime = Get-Date** — define a data de modificação do arquivo para a data e hora atuais (equivalente ao `touch` no Bash quando o arquivo já existe).

### No Bash

```bash
touch backend/app/__init__.py backend/app/main.py
touch backend/app/core/__init__.py backend/app/models/__init__.py backend/app/services/__init__.py backend/app/api/__init__.py
touch frontend/streamlit_app.py frontend/api_client.py
touch .env.example README.md Makefile setup.sh docker-compose.yml
```

- **touch** — comando que “toca” o arquivo: se não existir, cria vazio; se existir, apenas atualiza a data de modificação **sem apagar o conteúdo**. Vários arquivos podem ser passados no mesmo comando, separados por espaço.

---

## Resumo dos comandos no PowerShell

Para referência rápida, estes dois comandos recriam toda a estrutura de pastas e arquivos iniciais no PowerShell, na raiz do projeto. O significado de **New-Item**, **-ItemType Directory** / **-ItemType File**, **-Force** e **-Path** está explicado nos passos acima.

**Pastas (New-Item -ItemType Directory -Force -Path ...):**

```powershell
New-Item -ItemType Directory -Force -Path "backend/app/core", "backend/app/models/domain", "backend/app/services/ia/providers", "backend/app/services/ocr", "backend/app/api/routes", "backend/scripts", "tests", "frontend/components", "docs"
```

**Arquivos (New-Item -ItemType File -Force -Path ...):**

```powershell
New-Item -ItemType File -Force -Path "backend/app/__init__.py", "backend/app/main.py", "backend/app/core/__init__.py", "backend/app/models/__init__.py", "backend/app/services/__init__.py", "backend/app/api/__init__.py", "frontend/streamlit_app.py", "frontend/api_client.py", ".env.example", "Makefile", "setup.sh", "docker-compose.yml"
```

---





## Fase 1 — Configuração do backend com UV

O [UV](https://docs.astral.sh/uv/) é um gerenciador de pacotes e ambientes Python. Os comandos abaixo são iguais no PowerShell e no Bash; apenas a forma de definir o arquivo `.python-version` pode variar.

### Passo 1.1 — Inicializar o projeto backend com UV

1) Entre na pasta do backend:

`cd backend` (o comando **cd** muda o diretório atual para `backend`).

2) Inicialize o projeto UV (quando `backend/pyproject.toml` ainda não existir):

`uv init --app --name gestao-financeira-backend`

- **uv init** — cria um novo projeto Python (arquivo `pyproject.toml` e estrutura básica).
- **--app** — define o projeto como aplicação (em vez de biblioteca), adequado para um backend.
- **--name gestao-financeira-backend** — nome do projeto usado no `pyproject.toml`.

### Passo 1.2 — Configurar o `pyproject.toml` completo

O arquivo `backend/pyproject.toml` centraliza:

- **Metadados do projeto** (`[project]`): nome, versão, descrição, autores e `requires-python`.
- **Build system** (`[build-system]`): como o projeto é empacotado (aqui com `hatchling`).
- **Ferramentas de qualidade** (seções `tool.*`): lint/format, tipos e testes.

Nesta base do projeto, as configurações principais ficam assim:

- **Ruff** (`[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.format]`)
  - **line-length = 100** — largura de linha usada para lint/format.
  - **target-version = "py313"** — guia as regras e formatação para Python 3.13.
  - **select** — conjunto de regras (erros comuns, imports, boas práticas e upgrades de sintaxe).
  - **isort** — organiza imports considerando `app` como “first party”.
- **Black** (`[tool.black]`)
  - **line-length = 100** e **target-version = ["py313"]** — formatação consistente para Python 3.13.
- **Mypy** (`[tool.mypy]`)
  - **python_version = "3.13"** — checagem de tipos compatível com Python 3.13.
  - **packages = ["app"]** — analisa tipagem do pacote `app` (código em `backend/app`).
  - **strict = true** — um conjunto de verificações mais completas para estudo e evolução do código.
- **Pytest** (`[tool.pytest.ini_options]`)
  - **testpaths = ["../tests"]** — como os testes ficam em `tests/` na raiz do repositório (fora de `backend/`), o caminho relativo parte de `backend/`.
  - **pythonpath = ["."]** — facilita imports do pacote `app` durante os testes.
  - **asyncio_mode = "auto"** — integra testes assíncronos com `pytest-asyncio`.

Com essas configurações, você consegue rodar as ferramentas via UV, por exemplo:

- **Lint**: `uv run ruff check .`
- **Format**: `uv run ruff format .`
- **Black**: `uv run black .`
- **Tipos**: `uv run mypy`
- **Testes**: `uv run pytest`

### Passo 1.3 — Sincronizar dependências (`uv sync`)

Depois de editar dependências (ou ao baixar o projeto em uma nova máquina), use `uv sync` para alinhar o ambiente virtual com o que está descrito no projeto.

```bash
uv sync
```

- **uv sync** — atualiza o ambiente do projeto para ficar consistente com o lockfile (e com o `pyproject.toml`).
- **Sincronização exata (padrão)** — mantém o ambiente com apenas as dependências do projeto, ajudando a reproduzir o mesmo conjunto de pacotes.
- **Criação de ambiente** — quando `backend/.venv` ainda não existir, ele é criado automaticamente.
- **Atualização do lock** — antes de sincronizar, o UV pode atualizar o lockfile; para manter o lockfile fixo durante a sincronização, use:
  - **`uv sync --locked`** — verifica que o lockfile está atualizado e sincroniza sem alterá-lo.
  - **`uv sync --frozen`** — usa o lockfile como fonte de verdade e sincroniza sem atualizá-lo.
- **Grupos de dependências** — para sincronizar apenas as dependências de runtime (sem o grupo `dev`), use **`uv sync --no-dev`**.
- **Manter pacotes extras** — quando você quer manter pacotes adicionais instalados no ambiente, use **`uv sync --inexact`**.

### Passo 1.4 — Definir a versão do Python

O arquivo `.python-version` indica qual Python o UV usa. **PowerShell:** `Set-Content -Path ".python-version" -Value "3.13"`. **Bash:** `echo "3.13" > .python-version` (redireciona a saída para o arquivo).

### Passo 1.5 — Adicionar dependências principais

```bash
uv add fastapi "uvicorn[standard]" pydantic pydantic-settings python-dotenv supabase supabase-pydantic langchain langchain-openai langchain-community langchain-google-genai openai google-generativeai aiohttp pytesseract pillow pandas plotly pdf2image python-multipart
```

**uv add** adiciona pacotes e instala no ambiente. Principais: **fastapi** e **uvicorn[standard]** (API e servidor); **pydantic**, **pydantic-settings**, **python-dotenv** (config e env); **supabase** e **supabase-pydantic** (banco/auth); **langchain** e **openai**/**google-generativeai** (IA); **aiohttp** (HTTP assíncrono); **pytesseract**, **pillow**, **pdf2image** (OCR e imagens); **pandas**, **plotly** (dados e gráficos); **python-multipart** (upload na FastAPI).

### Passo 1.6 — Adicionar dependências de desenvolvimento

```bash
uv add --dev pytest pytest-asyncio black ruff mypy httpx
```

**uv add --dev** adiciona ao grupo de desenvolvimento. **pytest** e **pytest-asyncio** (testes); **black** e **ruff** (formatação e lint); **mypy** (tipos); **httpx** (cliente HTTP para testes).

Ambiente em `backend/.venv`. Ativar: PowerShell `\.venv\Scripts\Activate.ps1`, Bash `source .venv/bin/activate`. Ou usar `uv run python ...` / `uv run uvicorn ...` sem ativar.

### Passo 1.7 — Verificar o ambiente e dependências

Para listar as dependências instaladas e suas versões:

`uv tree`

---

## Fase 2 — Configuração do Supabase

Nesta fase você cria um projeto no Supabase e separa as credenciais que o backend e o frontend usam.

### Passo 2.1 — Acessar o Supabase e criar o projeto

1) Acesse o site do Supabase: `https://supabase.com`

2) Crie uma conta (plano gratuito) e faça login.

3) Crie um novo projeto:

- **Organization**: selecione ou crie uma organização.
- **Project name**: escolha um nome (ex.: `gestao-financeira`).
- **Database password**: defina uma senha forte para o banco (guarde em local seguro).
- **Region**: escolha a região mais próxima para melhorar latência.

### Passo 2.2 — Anotar as credenciais do projeto

No painel do Supabase, abra as configurações do projeto e localize as chaves de API:

- Caminho comum: **Project Settings → API**

Anote estas credenciais:

- **URL do projeto** (`SUPABASE_URL`): endereço base da sua instância (ex.: `https://xxxx.supabase.co`).
- **Anon key** (`SUPABASE_KEY` no `.env.example`): chave usada por aplicações cliente (ex.: frontend) com as permissões controladas por RLS (Row Level Security).
- **Service role key** (`SUPABASE_SERVICE_KEY` no `.env.example`): chave administrativa para uso em ambiente servidor (backend, jobs e scripts), com permissões amplas no projeto.

### Passo 2.3 — Guardar as credenciais no ambiente do projeto

1) Use o arquivo `.env.example` como modelo e crie um `.env` (ou defina variáveis no seu sistema/host).

2) Preencha as variáveis:

```env
SUPABASE_URL="..."
SUPABASE_KEY="..."
SUPABASE_SERVICE_KEY="..."
```

**Esclarecimento:** Uma prática comum é manter a `SUPABASE_SERVICE_KEY` apenas no ambiente do backend, enquanto a `SUPABASE_KEY` pode ser usada no frontend quando o projeto estiver configurado com RLS.

### Passo 2.3.1 — Criar o arquivo `.env` a partir do `.env.example`

O arquivo `.env.example` lista todas as variáveis esperadas pelo projeto. Você pode copiá-lo e preencher com seus valores.

**PowerShell (na raiz do projeto):**

```powershell
Copy-Item ".env.example" ".env"
```

- **Copy-Item** — copia um arquivo para outro caminho.

**Bash (na raiz do projeto):**

```bash
cp .env.example .env
```

- **cp** — copia um arquivo para outro caminho.

### Passo 2.3.2 — Entender cada variável do `.env.example`

A seguir, um guia curto do que cada variável representa (com foco em estudo e organização).

#### Supabase

- **SUPABASE_URL**: URL do projeto no Supabase (base URL da instância).
- **SUPABASE_KEY**: chave *anon* (uso comum em aplicações cliente, com permissões controladas por RLS).
- **SUPABASE_SERVICE_KEY**: chave *service role* (uso comum no backend, para operações administrativas e rotinas internas).

#### OpenAI

- **OPENAI_API_KEY**: credencial de acesso à API da OpenAI.
- **OPENAI_MODEL**: nome do modelo padrão para o provider OpenAI (ex.: `gpt-4`).

#### Google Gemini

- **GEMINI_API_KEY**: credencial de acesso à API do Google Gemini.
- **GEMINI_MODEL**: nome do modelo padrão para o provider Gemini (ex.: `gemini-pro`).

#### Ollama (local)

- **OLLAMA_BASE_URL**: URL do servidor do Ollama rodando localmente (por padrão, `http://localhost:11434`).
- **OLLAMA_MODEL**: nome do modelo local no Ollama (ex.: `llama3.2`). Escolha um modelo que exista na sua instalação.

#### Seleção de provider de IA

- **DEFAULT_IA_PROVIDER**: provider principal (ex.: `openai`, `gemini`, `ollama`).
- **FALLBACK_IA_PROVIDER**: provider de apoio quando o principal estiver indisponível (ex.: `ollama`).

#### Configurações da API

- **API_TITLE**: título da API exibido na documentação (OpenAPI/Swagger).
- **API_VERSION**: versão da API exibida na documentação.
- **DEBUG**: habilita modo de depuração (geralmente `true` ou `false`).

### Passo 2.3.3 — Separar variáveis do backend e do frontend

Para manter a organização:

- **Backend**: costuma usar `SUPABASE_SERVICE_KEY` e as chaves de providers de IA (`OPENAI_API_KEY`, `GEMINI_API_KEY`) para tarefas internas.
- **Frontend**: costuma usar `SUPABASE_URL` e `SUPABASE_KEY` quando o acesso estiver protegido por RLS e autenticação.

### Passo 2.4 — Criar as tabelas e políticas no Supabase (SQL)

Este repositório inclui um script SQL para preparar o banco no Supabase:

- `backend/scripts/setup-supabase.sql`

Para aplicar:

1) No painel do Supabase, abra **SQL Editor**.
2) Crie uma nova query.
3) Cole o conteúdo de `backend/scripts/setup-supabase.sql` e execute.

O script cria:

- **Tabelas**: `despesas`, `orcamentos_mensais`, `documentos`
- **Índices**: para consultas por usuário/data e por categoria
- **Triggers**: para manter `updated_at` atualizado automaticamente
- **RLS e políticas**: regras para que cada usuário acesse apenas os próprios dados usando `auth.uid()`

---

## Fase 3 — Implementação dos modelos (Pydantic)

Nesta fase o projeto define os modelos de dados com Pydantic (validação e serialização) e a configuração centralizada do backend.

### Passo 3.1 — Modelo de Despesa

O modelo de despesa fica em `backend/app/models/domain/despesa.py` e é usado na API e na persistência no Supabase.

**Enums (valores permitidos):**

- **CategoriaDespesa**: `alimentacao`, `transporte`, `saude`, `educacao`, `moradia`, `lazer`, `outros` — alinhado ao `CHECK` da tabela `despesas` no SQL.
- **StatusDespesa**: `pendente`, `confirmada`, `cancelada`.
- **FonteDespesa**: `manual`, `textual_natural`, `ocr`, `importacao` — indica como a despesa foi registrada.

**Modelos Pydantic:**

- **DespesaBase**: campos comuns — `valor` (obrigatório, maior que zero), `categoria`, `data`, `descricao` (opcional), `status` (padrão `pendente`). Inclui validador para garantir que o valor seja positivo.
- **DespesaCreate**: estende a base com `usuario_id` (obrigatório), `fonte` (padrão `manual`) e `metadata` (opcional). Usado ao receber dados para criar uma nova despesa.
- **DespesaInDB**: representa a despesa tal como está no banco — adiciona `id`, `usuario_id`, `fonte`, `metadata`, `created_at` e `updated_at`. Usa `from_attributes = True` para construção a partir de ORM/registros do Supabase.
- **DespesaUpdate**: todos os campos opcionais para atualização parcial (`valor`, `categoria`, `data`, `descricao`, `status`).

**Uso:** Os schemas servem para validar entrada da API, documentar o OpenAPI e mapear dados entre a aplicação e o banco.

### Passo 3.2 — Configuração do projeto

A configuração centralizada fica em `backend/app/core/config.py`, usando **pydantic-settings** para carregar variáveis do ambiente (e do arquivo `.env`).

**Classe `Settings`:**

- **Supabase**: `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY` (obrigatórios para o backend).
- **OpenAI**: `OPENAI_API_KEY` (opcional), `OPENAI_MODEL` (padrão `gpt-4`).
- **Google Gemini**: `GEMINI_API_KEY` (opcional), `GEMINI_MODEL` (padrão `gemini-pro`).
- **Ollama**: `OLLAMA_BASE_URL` (padrão `http://localhost:11434`), `OLLAMA_MODEL` (padrão definido no código).
- **Seleção de IA**: `DEFAULT_IA_PROVIDER`, `FALLBACK_IA_PROVIDER` (ex.: `openai` e `ollama`).
- **API**: `API_TITLE`, `API_VERSION`, `DEBUG`.

**Config da classe:**

- **env_file = ".env"** — carrega variáveis a partir do `.env` na raiz do projeto (ou do diretório de trabalho).
- **case_sensitive = True** — os nomes das variáveis de ambiente respeitam maiúsculas e minúsculas.

Uma instância global **`settings = Settings()`** é exportada para uso no resto da aplicação (ex.: em rotas e serviços). As variáveis obrigatórias (Supabase) precisam estar definidas no `.env` (ou no ambiente) para a aplicação subir sem erro.

---

## Próximos passos — Como executar

_(Adicione aqui as instruções de instalação de dependências e execução do projeto, por exemplo: `uv run uvicorn app.main:app`, `streamlit run`, etc.)_
