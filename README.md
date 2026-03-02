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

## Próximos passos — Como executar

_(Adicione aqui as instruções de instalação de dependências e execução do projeto, por exemplo: ambiente virtual, `pip install`, `streamlit run`, etc.)_
