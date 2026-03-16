# Gestão Financeira — Guia passo a passo

Este documento descreve como montar o projeto do zero, em ordem. Use-o como roteiro de estudo: siga os passos na sequência para entender a estrutura e os comandos em cada ambiente (PowerShell no Windows e Bash em Linux/macOS ou Git Bash).

---

## Visão geral da estrutura

Antes de executar os comandos, convém saber como o projeto fica organizado:

```
backend/
├── main.py                       # Script simples de entrada (exemplo/CLI)
├── app/
│   ├── core/
│   │   └── config.py             # Configuração (Settings) carregada do .env
│   ├── models/
│   │   └── domain/
│   │       └── despesa.py        # Modelos Pydantic de despesa (enums, Create, InDB, Update)
│   ├── services/
│   │   ├── supabase_service.py   # SupabaseService: CRUD despesas, resumo mensal, por categoria, evolução
│   │   └── ia/
│   │       ├── config.py         # ProviderConfig, PROVIDER_CONFIGS, PROMPT, get_config, get_prompt
│   │       ├── base.py           # ExtracaoDespesa e interface abstrata IAProvider (helpers de parsing)
│   │       ├── clients.py        # ClienteFactory: criar_cliente (OpenAI/Gemini/Ollama/Claude), chamar_ollama
│   │       ├── provider.py       # IAProvider concreto (um por tipo: openai, gemini, ollama, claude)
│   │       ├── factory.py        # IAProviderFactory: get_provider (singleton), listar_provedores_disponiveis/recarregar
│   │       └── manager.py        # IAManager/EstrategiaSelecao (principal, fallback, paralelo, votacao, rapido, preciso)
│   ├── api/
│   │   ├── main.py               # Ponto de entrada FastAPI: cria app, CORS, inclui rotas
│   │   ├── deps.py               # Dependências: HTTPBearer, singletons (Supabase, IA), get_current_user
│   │   └── routes/
│   │       ├── despesas.py       # Rotas CRUD de despesas (/despesas)
│   │       ├── ia.py             # Rotas de IA (/ia): extração, perguntas, comparação, recarregar provedores
│   │       └── relatorios.py     # Rotas de relatórios (/relatorios): mensal, categoria, evolução, insights
│   └── __init__.py (opcional)
└── scripts/
    └── setup-supabase.sql        # Script SQL para criar tabelas/políticas no Supabase

tests/
├── conftest.py                   # Env de teste (SUPABASE_*), fixtures (extracao_exemplo, texto_despesa)
├── test_ia_config.py             # Testes de get_config, get_prompt, categorias e prompts
├── test_ia_base.py               # Testes do modelo ExtracaoDespesa
├── test_ia_factory.py            # Testes da IAProviderFactory
├── test_ia_manager.py            # Testes do IAManager e estratégias
└── test_supabase_service.py      # Testes do SupabaseService (CRUD e agregações)

arquitetura/
├── Arquitetura Geral do Sistema.png
├── Estrutura de Dados.png
├── Fluxo de Dados no Sistema.png
└── Fluxo de Processamento Multi-IA.png

.env.example  README.md  Makefile  setup.sh  docker-compose.yml  backend/pyproject.toml
```

- **backend/** — código da aplicação backend (núcleo, modelos, serviços, API e scripts).
- **tests/** — testes automatizados de IA e de acesso ao Supabase.
- **arquitetura/** — diagramas de arquitetura, fluxo de dados e estrutura de dados.
- **Raiz** — arquivos de configuração (ambiente, Makefile, setup, Docker, pyproject do backend).

### Fluxo geral do sistema (resumo textual)

1. **Entrada do usuário (frontend ou cliente HTTP)**  
   - O usuário registra despesas manualmente ou envia textos/consultas para IA.  
   - As requisições HTTP chegam à API FastAPI (`main.py`), que roteia para:
     - Rotas de **despesas** (`/despesas`) para CRUD direto.
     - Rotas de **IA** (`/ia`) para extrair despesas de texto ou fazer perguntas com contexto financeiro.
     - Rotas de **relatórios** (`/relatorios`) para resumos mensais, por categoria, evolução e insights.

2. **Camada de serviços e persistência**  
   - As rotas usam o `SupabaseService` para ler/escrever na tabela `despesas` (e relatórios derivados), sempre filtrando por `usuario_id` (RLS no Supabase).  
   - Resumos e agregações (mensal, por categoria, evolução) são montados nessa camada e devolvidos para a API.

3. **Camada de IA (multi-provedor)**  
   - Para extração de despesas e geração de insights, as rotas chamam o `IAProviderManager`, que usa:
     - `IAProviderFactory` para obter o provedor (`openai`, `gemini`, `ollama`, etc.).
     - `IAProvider` para executar prompts de extração, classificação, relatório e perguntas.  
   - Estratégias como principal, rápido, preciso, fallback, paralelo e votação são usadas para combinar ou escolher resultados entre provedores.

4. **Resposta ao cliente**  
   - A API retorna objetos estruturados (Pydantic) com:
     - Despesas individuais ou listas (`DespesaInDB`).
     - Resumos e relatórios numéricos (mensal, categoria, evolução).
     - Textos de insights e respostas da IA, sempre baseados nos dados do usuário autenticado.

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
New-Item -ItemType Directory -Force -Path "backend/app/core", "backend/app/models/domain", "backend/app/services/ia", "backend/app/api/routes"
```

- **New-Item** — cria novos itens no sistema de arquivos.
- **-ItemType Directory** — define que cada item criado é uma pasta.
- **-Force** — cria todas as pastas intermediárias necessárias (ex.: `backend`, `backend/app`, `backend/app/services/ia`) e não gera erro se alguma pasta já existir.
- **-Path "..., ..., ..."** — lista de caminhos separados por vírgula; cada um é criado como pasta. No PowerShell não se usa `{ }` para expandir vários caminhos, por isso os caminhos são listados um a um.

### No Bash (Git Bash, WSL, Linux ou macOS)

```bash
mkdir -p backend/app/{core,models/domain,services/ia,api/routes}
```

- **mkdir** — comando para criar diretórios.
- **-p** — cria os “parents” (pastas intermediárias) quando necessário e não gera erro se a pasta já existir.
- **`{core,models/domain,...}`** — expansão de chaves: o Bash substitui por vários argumentos (ex.: `core`, `models/domain`, etc.), e o `mkdir` recebe vários caminhos em um único comando.

**Esclarecimento:** No PowerShell, as chaves `{ }` são usadas para blocos de script, não para expandir listas. Por isso, no PowerShell os caminhos devem ser escritos explicitamente no `-Path`, separados por vírgula.

---

## Passo 3 — Criar as pastas de scripts, testes e arquitetura

Crie as pastas `backend/scripts`, `tests` e `arquitetura`.

### No PowerShell

```powershell
New-Item -ItemType Directory -Force -Path "backend/scripts", "tests", "arquitetura"
```

- **New-Item -ItemType Directory** — cria pastas.
- **-Force** — cria pastas intermediárias (ex.: `backend` para `backend/scripts`, `frontend` para `frontend/components`) e não falha se a pasta já existir.
- **-Path "..., ..., ..."** — vários caminhos em um único comando, separados por vírgula.

### No Bash

```bash
mkdir -p backend/scripts tests arquitetura
```

- **mkdir -p** — cria as pastas e, se precisar, as pastas pai (`-p`).
- Vários caminhos no mesmo comando são separados por **espaço** (ex.: `backend/scripts` e `tests` no primeiro comando).

---

## Passo 4 — Criar toda a estrutura de pastas de uma vez (opcional)

Se preferir um único comando para todas as pastas (backend + scripts, tests, arquitetura):

### No PowerShell

```powershell
New-Item -ItemType Directory -Force -Path "backend/app/core", "backend/app/models/domain", "backend/app/services/ia", "backend/app/api/routes", "backend/scripts", "tests", "arquitetura"
```

### No Bash

Use os comandos dos passos 2 e 3 em sequência, ou combine conforme a sintaxe do passo 2.

---

## Passo 5 — Criar os arquivos iniciais do projeto

Crie os arquivos vazios que marcam módulos e pontos de entrada. No Bash isso costuma ser feito com `touch`; no PowerShell use `New-Item -ItemType File -Force`.

### No PowerShell

```powershell
New-Item -ItemType File -Force -Path "backend/app/__init__.py", "backend/app/core/__init__.py", "backend/app/models/__init__.py", "backend/app/services/__init__.py", "backend/app/api/__init__.py", "backend/app/api/main.py", ".env.example", "Makefile", "setup.sh", "docker-compose.yml"
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
touch backend/app/__init__.py
touch backend/app/core/__init__.py backend/app/models/__init__.py backend/app/services/__init__.py backend/app/api/__init__.py backend/app/api/main.py
touch .env.example README.md Makefile setup.sh docker-compose.yml
```

- **touch** — comando que “toca” o arquivo: se não existir, cria vazio; se existir, apenas atualiza a data de modificação **sem apagar o conteúdo**. Vários arquivos podem ser passados no mesmo comando, separados por espaço.

---

## Resumo dos comandos no PowerShell

Para referência rápida, estes dois comandos recriam toda a estrutura de pastas e arquivos iniciais no PowerShell, na raiz do projeto. O significado de **New-Item**, **-ItemType Directory** / **-ItemType File**, **-Force** e **-Path** está explicado nos passos acima.

**Pastas (New-Item -ItemType Directory -Force -Path ...):**

```powershell
New-Item -ItemType Directory -Force -Path "backend/app/core", "backend/app/models/domain", "backend/app/services/ia", "backend/app/api/routes", "backend/scripts", "tests", "arquitetura"
```

**Arquivos (New-Item -ItemType File -Force -Path ...):**

```powershell
New-Item -ItemType File -Force -Path "backend/app/__init__.py", "backend/app/core/__init__.py", "backend/app/models/__init__.py", "backend/app/services/__init__.py", "backend/app/api/__init__.py", "backend/app/api/main.py", ".env.example", "Makefile", "setup.sh", "docker-compose.yml"
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

## Fase 4 — Camada de serviços de IA

A camada de IA fica em `backend/app/services/ia/` e é composta por seis módulos que trabalham juntos: **config**, **base**, **clients**, **provider**, **factory** e **manager**.

### Passo 4.1 — config.py

Centraliza a configuração dos provedores e os prompts:

- **ProviderConfig**: modelo Pydantic com nome, tipo, api_key_attr, model_attr, base_url_attr, suporta_json, precisa_limpeza, prompt_prefix, prompt_suffix, etc.
- **PROVIDER_CONFIGS**: dicionário com as configs de `openai`, `gemini` e `ollama`.
- **CATEGORIA_VALIDAS**: categorias aceitas para despesas (alimentacao, transporte, saude, educacao, moradia, lazer, outros).
- **PROMPT**: templates dos prompts (`extrair_despesa`, `classificar_categoria`, `gerar_relatorio`, `perguntar`) com placeholders `{texto}`, `{data_hoje}`, `{categorias}`, etc.
- **get_config(tipo)** e **get_prompt(nome, **kwargs)**: funções para obter a config de um provedor e o prompt já formatado.

### Passo 4.2 — base.py

Define o modelo de dados e a interface abstrata:

- **ExtracaoDespesa**: modelo Pydantic com valor, categoria, data, descricao, fonte, status, provedor, confianca (0–1), created_at e updated_at (com default em UTC).
- **IAProvider** (ABC): interface com nome, tipo, extrair_despesa, classificar_categoria, gerar_relatorio, perguntar e helpers _extrair_json, _extrair_valor, _extrair_data para parsing de respostas da IA.

### Passo 4.3 — clients.py

**ClienteFactory** cria o cliente correto por tipo:

- **criar_cliente(tipo)**: retorna AsyncOpenAI (openai), GenerativeModel (gemini) ou um dict com base_url e model (ollama).
- **chamar_ollama(prompt, config, temperatura)**: envia POST para `/api/generate` do Ollama via aiohttp e retorna o texto gerado.

### Passo 4.4 — provider.py

Uma única classe **IAProvider** (concreta) parametrizada pelo tipo (`openai`, `gemini`, `ollama`). No `__init__` carrega a config e o cliente; os métodos públicos montam o prompt com get_prompt(), aplicam prefix/suffix, chamam _chamar_api() e tratam a resposta. Inclui fallback: em falha na extração usa _extrair_simples() (heurística por palavras-chave) e _extrair_fallback() para devolver uma ExtracaoDespesa com confiança menor.

### Passo 4.5 — factory.py

**IAProviderFactory** mantém uma instância de IAProvider por tipo (singleton):

- **get_provider(tipo)**: retorna o provedor do tipo pedido (ou DEFAULT_IA_PROVIDER se tipo for inválido); em erro tenta o provedor padrão.
- **listar_provedores_disponiveis()**: retorna lista com nome, tipo e status (disponivel/indisponivel) para cada provedor configurado.

### Passo 4.6 — manager.py

**IAManager** aplica estratégias de uso dos provedores:

- **EstrategiaSelecao**: PRINCIPAL (usa provider_default), RAPIDO (ollama), PRECISO (openai), FALLBACK (tenta em ordem até um suceder), PARALELO (todos em paralelo, retorna o de maior confiança), VOTACAO (agrega valor médio e categoria mais votada).
- **extrair_despesa(texto, provider_default)**: delega para o provedor ou para _executar_paralelo, _executar_fallback ou _executar_votacao conforme a estratégia.

---

## Passo a passo — Adicionar um novo modelo de IA

Para integrar um novo provedor de IA (ex.: Claude, Groq, outro modelo), siga estes passos na ordem. O identificador do provedor (ex.: `"claude"`) será usado em todo o fluxo.

### 1. Variáveis de ambiente (Settings e .env)

**Arquivo:** `backend/app/core/config.py`

- Adicione os campos na classe **Settings** (nome da API key, modelo e, se existir, URL base), por exemplo:

```python
# --- Novo provedor (ex.: Claude) ---
CLAUDE_API_KEY: str | None = Field(
    default=None,
    env="CLAUDE_API_KEY",
    description="Chave da API Anthropic Claude.",
)
CLAUDE_MODEL: str = Field(
    default="claude-3-sonnet-20240229",
    env="CLAUDE_MODEL",
    description="Modelo Claude usado nas chamadas.",
)
```

- Atualize o **`.env.example`** (e o seu `.env`) com as novas variáveis, por exemplo: `CLAUDE_API_KEY`, `CLAUDE_MODEL`.

### 2. Configuração do provedor (config.py)

**Arquivo:** `backend/app/services/ia/config.py`

- Em **PROVIDER_CONFIGS**, adicione uma nova entrada com a chave igual ao identificador do provedor (ex.: `"claude"`):

```python
"claude": ProviderConfig(
    name="Anthropic Claude",
    tipo="claude",
    api_key_attr="CLAUDE_API_KEY",
    model_attr="CLAUDE_MODEL",
    suporta_json=True,       # ou False se a API não devolver JSON nativo
    precisa_limpeza=True,     # True se a resposta puder vir com ```json ... ```
    temperatura_attr=0.1,
    prompt_prefix="",        # ou o formato esperado pelo modelo (ex.: "\n\nHuman")
    prompt_suffix="",        # ex.: "\n\nAssistant"
),
```

- Ajuste **suporta_json** e **precisa_limpeza** conforme o comportamento da API (resposta pura JSON ou texto com JSON embutido). **prompt_prefix** e **prompt_suffix** são opcionais e dependem do formato de prompt do modelo.

### 3. Cliente do provedor (clients.py)

**Arquivo:** `backend/app/services/ia/clients.py`

- Se o provedor tiver **SDK oficial em Python**: importe o pacote e, em **ClienteFactory.criar_cliente(tipo)**, adicione um novo `elif tipo == "claude":` (ou o identificador escolhido) que instancia o cliente usando `settings.CLAUDE_API_KEY` (e modelo/URL se necessário). O método deve **retornar** esse cliente para o `provider.py` usar.

- Se o provedor for **apenas API HTTP** (como o Ollama): faça `criar_cliente` retornar um **dict** com `base_url`, `model` e o que for necessário e, em **provider.py**, implemente a chamada HTTP em **_chamar_api** (ou crie um método estático em `ClienteFactory`, como **chamar_ollama**, e chame esse método em `_chamar_api`).

### 4. Chamada à API no provider (provider.py)

**Arquivo:** `backend/app/services/ia/provider.py`

- No método **IAProvider._chamar_api(self, prompt, temperatura)** (bloco `try` com vários `if self.tipo == ...`), adicione um novo ramo:

```python
elif self.tipo == "claude":
    response = await self.cliente.messages.create(
        model=settings.CLAUDE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperatura,
        max_tokens=self.config.max_tokens_attr,
    )
    return response.choices[0].message.content  # ou o campo correto do SDK
```

- Adapte **model**, **messages**, **temperature** e o modo de obter o texto da resposta conforme a documentação do SDK/API do novo provedor. O retorno de **_chamar_api** deve ser sempre uma **string** (texto da resposta).

### 5. (Opcional) Manager — paralelo, fallback e votação

**Arquivo:** `backend/app/services/ia/manager.py`

- Se o novo provedor deve participar das estratégias **PARALELO**, **FALLBACK** ou **VOTACAO**, inclua o identificador nas listas fixas:
  - **_executar_paralelo**: no `for tipo in ["openai", "gemini", "ollama"]`, adicione o novo tipo (ex.: `"claude"`).
  - **_executar_fallback**: em `tentativas.extend([...])`, adicione o novo tipo.
  - **_executar_votacao**: no `for tipo in ["openai", "gemini", "ollama"]`, adicione o novo tipo.
- Se fizer sentido, inclua o tipo em **provedores_rapidos** ou **provedores_precisos** no `__init__` do IAManager (para documentação/organização; as estratégias RAPIDO e PRECISO continuam fixas em "ollama" e "openai" hoje).

### 6. Dependência Python (pyproject.toml)

- Se o provedor usar um **pacote Python** (ex.: `anthropic` para Claude), adicione-o às dependências do backend:

```powershell
cd backend
uv add anthropic
```

- Depois use esse pacote em **clients.py** (e, se necessário, em **provider.py**) conforme a documentação oficial.

### 7. Testar

- Defina no `.env` a API key e o modelo do novo provedor.
- Use **DEFAULT_IA_PROVIDER** ou **provider_default** com o novo identificador e chame um endpoint que use extração de despesa (ou rode um script que use `IAProviderFactory.get_provider("claude")` e `extrair_despesa(texto)`).
- Opcional: adicione testes em **tests/** para o novo tipo (ex.: em `test_ia_config.py` um `test_get_config_claude`; em `test_ia_factory.py` garantir que `get_provider("claude")` seja chamado corretamente com mocks).

**Resumo dos arquivos a alterar:**

| Arquivo | O que fazer |
|--------|--------------|
| `backend/app/core/config.py` | Novos campos em Settings (API key, model, base_url se houver). |
| `.env.example` / `.env` | Novas variáveis (ex.: CLAUDE_API_KEY, CLAUDE_MODEL). |
| `backend/app/services/ia/config.py` | Nova entrada em PROVIDER_CONFIGS. |
| `backend/app/services/ia/clients.py` | Novo ramo em criar_cliente(tipo); método HTTP auxiliar se for API REST. |
| `backend/app/services/ia/provider.py` | Novo ramo em _chamar_api() para chamar a API e retornar o texto. |
| `backend/app/services/ia/manager.py` | (Opcional) Incluir o tipo nas listas de PARALELO, FALLBACK e VOTACAO. |
| `backend/pyproject.toml` | (Se usar SDK) `uv add nome-do-pacote`. |

---

## Fase 5 — Serviço Supabase

Nesta fase o projeto expõe uma camada de serviço para acessar o banco de dados e as funcionalidades do Supabase (tabelas, RLS, Auth quando aplicável). O backend usa as credenciais configuradas na Fase 2 (`SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`) para conectar ao projeto.

### 5.1. Serviço de Banco de Dados

O **serviço de banco de dados** está implementado em **`backend/app/services/supabase_service.py`**. A classe **SupabaseService** centraliza o cliente Supabase (criado com `SUPABASE_URL` e `SUPABASE_KEY`) e as operações sobre a tabela `despesas` e relatórios derivados. As rotas da API devem usar esse serviço em vez de acessar o Supabase diretamente.

#### Implementação atual

- **Cliente:** no `__init__`, o cliente é criado com `create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)`. Para operações que precisem bypassar RLS, pode-se usar `SUPABASE_SERVICE_KEY` em outra variante do serviço.
- **Despesas — CRUD:**
  - **salvar_despesa(despesa: DespesaCreate)** → insere na tabela `despesas`, adiciona `created_at`, retorna o registro como `DespesaInDB`.
  - **listar_despesas(usuario_id, data_inicio?, data_fim?, categoria?, limit)** → lista despesas do usuário com filtros opcionais, ordenadas por data (mais recente primeiro), retorna `list[DespesaInDB]`.
  - **atualizar_despesa(despesa_id, usuario_id, dados)** → atualização parcial com `updated_at`; retorna `DespesaInDB` se houver registro, `None` caso contrário.
  - **deletar_despesa(despesa_id, usuario_id)** → remove o registro; retorna `True` se foi removido, `False` caso contrário.
- **Relatórios e agregações:**
  - **get_resumo_mensal(usuario_id, ano, mes)** → total, totais por categoria, quantidade, média por dia, maior despesa e período (início/fim em ISO).
  - **get_despesas_por_categoria(usuario_id, data_inicio, data_fim)** → dict categoria → total (soma das despesas no período).
  - **get_evolucao_mensal(usuario_id, ano, mes)** → lista de 12 itens (um por mês do ano) com `mes` e `total`.

Todos os métodos são assíncronos (`async`). Os modelos `DespesaCreate` e `DespesaInDB` (e enums como `CategoriaDespesa`) vêm de `backend/app/models/domain/despesa.py`.

#### Tabelas envolvidas (referência)

As tabelas criadas pelo `backend/scripts/setup-supabase.sql` são:

- **despesas**: `id`, `usuario_id`, `valor`, `categoria`, `data`, `descricao`, `fonte`, `status`, `metadata`, `created_at`, `updated_at`. Constraints: `categoria`, `fonte` e `status` com valores fixos (CHECK).
- **orcamentos_mensais**: `id`, `usuario_id`, `ano`, `mes`, `limites` (JSONB), `created_at`, `updated_at`. UNIQUE em `(usuario_id, ano, mes)`.
- **documentos**: `id`, `usuario_id`, `nome_arquivo`, `tipo_documento`, `conteudo_extraido` (JSONB), `status`, `created_at`.

RLS está ativo; as políticas permitem que cada usuário acesse apenas os próprios dados (`usuario_id = auth.uid()::text`). O serviço atual usa a chave anon; para operações privilegiadas (ex.: jobs), use `SUPABASE_SERVICE_KEY` na criação do cliente.

#### Integração com as rotas

Nas rotas FastAPI (`backend/app/api/routes/`), importe ou injete **SupabaseService**, instancie (ou use um dependency) e chame os métodos acima. Assim a lógica de banco fica no serviço e as rotas permanecem enxutas. Orçamentos e documentos podem ser adicionados ao mesmo serviço ou em módulos separados quando necessário.

---

## Dependências da API (deps.py)

O módulo **`backend/app/api/deps.py`** centraliza as dependências injetáveis usadas nas rotas FastAPI:

- **`security = HTTPBearer()`** — exige o header `Authorization: Bearer <token>` nas rotas protegidas.
- **Singletons** — `get_supabase_service()` e `get_ia_provider_manager()` devolvem a instância única de `SupabaseService` e `IAProviderManager`, evitando criar nova conexão a cada requisição.
- **`get_current_user(credentials)`** — dependência assíncrona que extrai o token do header, valida (em desenvolvimento aceita `test-token` e `dev-token` e retorna `"usuario-teste"`; em produção deve validar com Supabase Auth) e retorna o identificador do usuário. Em caso de token inválido, levanta `HTTP 401` com `WWW-Authenticate: Bearer`.

Uso nas rotas: declare `Depends(get_supabase_service)`, `Depends(get_ia_provider_manager)` ou `Depends(get_current_user)` nos parâmetros para injetar o serviço ou o ID do usuário atual.

---

## 6. API e rotas

### 6.1. Rotas de despesas

As rotas de despesas ficam em **`backend/app/api/routes/despesas.py`**, com prefixo **`/despesas`**. Todas as rotas que precisam de usuário autenticado exigem o header `Authorization: Bearer <token>` (via `get_current_user`). A URL base da API depende de como você executa o servidor (veja a secção “Como executar”).

| Método | Endpoint | Autenticação | Descrição |
|--------|----------|--------------|-----------|
| **POST** | `/despesas/` | Sim | Cria uma nova despesa para o usuário autenticado. Body: `DespesaCreate`. O `usuario_id` é sempre forçado para o usuário logado pelo backend, ignorando qualquer valor vindo no body. |
| **GET** | `/despesas/` | Sim | Lista despesas do usuário com filtros opcionais: `data_inicio`, `data_fim`, `categoria` e `limit` (padrão 100, máximo 500). Retorna uma lista de `DespesaInDB`. |
| **GET** | `/despesas/{despesa_id}` | Sim | Busca uma despesa específica pelo ID, garantindo que pertença ao usuário autenticado. Retorna 404 se não existir ou se não pertencer ao usuário. |
| **PUT** | `/despesas/{despesa_id}` | Sim | Atualiza parcialmente uma despesa existente. Body: `DespesaUpdate` (todos os campos opcionais). Apenas campos enviados são persistidos; retorna 404 se a despesa não existir ou não pertencer ao usuário. |
| **DELETE** | `/despesas/{despesa_id}` | Sim | Deleta uma despesa do usuário autenticado. Retorna 404 se não existir ou não pertencer ao usuário. |

Essas rotas usam o serviço `SupabaseService` para acessar a tabela `despesas`, aplicando sempre filtros por `usuario_id` para respeitar as políticas de RLS do Supabase.

### 6.2. Rotas de IA

As rotas de IA ficam em **`backend/app/api/routes/ia.py`**, com prefixo **`/ia`**. Todas as rotas que precisam de usuário autenticado exigem o header `Authorization: Bearer <token>` (via `get_current_user`). A URL base da API depende de como você executa o servidor (veja a secção “Como executar”).

| Método | Endpoint | Autenticação | Descrição |
|--------|----------|---------------|-----------|
| **GET** | `/ia/provedores` | Não | Lista provedores de IA configurados (nome, tipo, status disponivel/indisponivel) e as estratégias de extração (PRINCIPAL, RAPIDO, PRECISO, FALLBACK, PARALELO, VOTACAO). |
| **POST** | `/ia/extrair-despesa` | Sim | Extrai uma despesa a partir de texto em linguagem natural. Body: `texto`, `provedor` (opcional), `estrategia` (opcional), `Salvar` (bool). Opcionalmente persiste no Supabase com fonte TEXTUAL_NATURAL. |
| **POST** | `/ia/perguntar` | Sim | Envia uma pergunta ao modelo de IA. Body: `pergunta`, `contexto` (opcional; se omitido, usa as últimas 50 despesas do usuário), `provedor` (opcional). |
| **POST** | `/ia/comparar` | Sim | Compara a extração do mesmo texto em todos os provedores. Body: `{"texto": "..."}`. Retorna um resultado por provedor (ou objeto com "Erro" em falha). |
| **POST** | `/ia/recarregar` | Não | Limpa o cache de provedores da fábrica; na próxima chamada os clientes são recriados (útil após alterar variáveis de ambiente). |

**Exemplos de texto para extração:** `"Gastei 50 reais com almoço hoje"`, `"Uber 25 reais ontem"`, `"Comprei 100 reais de alimentos na mercearia"`, `"Paguei 150 reais de aluguel do mês"`.

**Schemas de request/response:** `TextoRequest` / `TextoResponse` (extração), `PerguntaRequest` (perguntar), `ComparacaoResponse` (comparar). A documentação interativa (Swagger) em `/docs` exibe esses modelos e permite testar os endpoints.

---

### 6.3. Rotas de relatórios

As rotas de relatórios ficam em **`backend/app/api/routes/relatorios.py`**, com prefixo **`/relatorios`**. Todas usam `get_current_user` para filtrar os dados pelo `usuario_id` e o `SupabaseService` para acessar o banco. Algumas também utilizam `IAProviderManager` para gerar insights com IA.

| Método | Endpoint | Autenticação | Descrição |
|--------|----------|--------------|-----------|
| **GET** | `/relatorios/mensal` | Sim | Gera um resumo mensal de despesas do usuário para o ano/mês informados. Usa `get_resumo_mensal(usuario_id, ano, mes)` para calcular total, totais por categoria, quantidade, média por dia, maior despesa e período. |
| **GET** | `/relatorios/categoria` | Sim | Gera um relatório de gastos por categoria em um intervalo de datas (`data_inicio`, `data_fim`). Usa `get_despesas_por_categoria(usuario_id, data_inicio, data_fim)` e retorna um dict `categoria -> total`. |
| **GET** | `/relatorios/evolucao/{ano}` | Sim | Retorna a evolução mensal dos gastos ao longo de um ano. Usa `get_evolucao_mensal(usuario_id, ano, mes=1)` para montar uma lista de 12 itens, cada um com `mes` e `total`. |
| **POST** | `/relatorios/insights` | Sim | Gera insights em linguagem natural sobre os gastos de um determinado mês (`ano`, `mes`). Calcula o resumo mensal e, se houver despesas, chama `IAManager.gerar_insights(resumo, provedor="openai")`, retornando texto com insights, o período e o resumo usado como contexto. |

Essas rotas complementam as de despesas e IA, oferecendo visão agregada (resumo, por categoria, evolução) e uma camada de interpretação automática com IA.

---

## Testes

Os testes ficam na pasta **`tests/`** na raiz do repositório. O `conftest.py` define variáveis de ambiente mínimas (SUPABASE_*) para o Settings carregar sem `.env` e oferece as fixtures `extracao_exemplo` e `texto_despesa`. Os módulos `test_ia_config.py`, `test_ia_base.py`, `test_ia_factory.py` e `test_ia_manager.py` cobrem config, modelo ExtracaoDespesa, factory e manager (com mocks nos provedores).

**Executar os testes** (a partir da pasta `backend`, para o `pythonpath` e `testpaths` do pyproject.toml):

```powershell
cd backend
uv run pytest ../tests -v
```

Ou com saída resumida:

```powershell
cd backend
uv run pytest ../tests -v --tb=short
```

---

## Como executar

**Backend (API FastAPI):**

Na pasta `backend`, com dependências já instaladas (`uv sync`):

```powershell
cd backend
uv run uvicorn app.api.main:app --reload
```

Ao iniciar, o Uvicorn mostra no terminal a URL onde a API está disponível (por exemplo, `http://localhost:8000`) e a rota da documentação interativa (Swagger), normalmente em `/docs`.

**Dependências:** na pasta `backend`, use `uv sync` para instalar/atualizar o ambiente conforme o `pyproject.toml`. Para incluir dependências de desenvolvimento (pytest, ruff, etc.): `uv sync` já as inclui pelo grupo `dev` definido no projeto.
