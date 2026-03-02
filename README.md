# Gestão Financeira

## Estrutura do projeto

### Criando a estrutura de pastas do backend

A aplicação backend usa a seguinte estrutura de diretórios:

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

#### Por que o comando original não funcionou (Bash vs PowerShell)

Se você tentou usar este comando (sintaxe **Bash/Linux**):

```bash
mkdir -p backend/app/{core,models/domain,services/{ia/providers,ocr},api/routes}
```

ele **não funciona no PowerShell** do Windows por dois motivos:

1. **Expansão de chaves `{ }`** — No Bash, `{a,b,c}` é expandido em várias strings (`a`, `b`, `c`). No PowerShell, as chaves têm outro significado (blocos de script) e não fazem essa expansão, gerando erros como *"Argumento ausente na lista de parâmetros"*.

2. **Flag `-p`** — No Bash, `mkdir -p` cria pastas intermediárias e não dá erro se já existirem. No PowerShell, o `mkdir` (alias de `New-Item`) não usa `-p`; o equivalente é usar `-Force` para não falhar se a pasta já existir.

#### Comando correto no PowerShell (Windows)

Use este comando no terminal PowerShell, na raiz do projeto:

```powershell
New-Item -ItemType Directory -Force -Path "backend/app/core", "backend/app/models/domain", "backend/app/services/ia/providers", "backend/app/services/ocr", "backend/app/api/routes"
```

- `New-Item -ItemType Directory` — cria diretórios.
- `-Force` — cria pastas intermediárias e não falha se alguma já existir.
- `-Path "caminho1", "caminho2", ...` — lista de caminhos a criar.

#### Se você estiver no Bash (Git Bash, WSL ou Linux/macOS)

Pode usar o comando original:

```bash
mkdir -p backend/app/{core,models/domain,services/{ia/providers,ocr},api/routes}
```

### Criando scripts, tests, frontend e docs

Para criar as pastas `backend/scripts`, `tests`, `frontend/components` e `docs`:

**PowerShell (Windows):**

```powershell
New-Item -ItemType Directory -Force -Path "backend/scripts", "tests", "frontend/components", "docs"
```

**Bash (Git Bash, WSL ou Linux/macOS):**

```bash
mkdir -p backend/scripts tests
mkdir -p frontend/components
mkdir -p docs
```

No Bash, cada `mkdir -p` pode receber vários caminhos separados por espaço; no PowerShell use uma única chamada com os caminhos separados por vírgula no `-Path`.

### Resumo: todos os comandos no PowerShell

Para criar toda a estrutura de pastas de uma vez no PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path "backend/app/core", "backend/app/models/domain", "backend/app/services/ia/providers", "backend/app/services/ocr", "backend/app/api/routes", "backend/scripts", "tests", "frontend/components", "docs"
```

### Criando os arquivos iniciais

Para criar os arquivos vazios do projeto (equivalente ao `touch` no Bash):

**PowerShell (Windows):**

```powershell
New-Item -ItemType File -Force -Path "backend/app/__init__.py", "backend/app/main.py", "backend/app/core/__init__.py", "backend/app/models/__init__.py", "backend/app/services/__init__.py", "backend/app/api/__init__.py", "frontend/streamlit_app.py", "frontend/api_client.py", ".env.example", "Makefile", "setup.sh", "docker-compose.yml"
```

Para apenas atualizar a data de modificação de um arquivo existente (ex.: `README.md`) sem apagar o conteúdo:

```powershell
(Get-Item "README.md").LastWriteTime = Get-Date
```

**Bash (Git Bash, WSL ou Linux/macOS):**

```bash
touch backend/app/__init__.py backend/app/main.py
touch backend/app/core/__init__.py backend/app/models/__init__.py backend/app/services/__init__.py backend/app/api/__init__.py
touch frontend/streamlit_app.py frontend/api_client.py
touch .env.example README.md Makefile setup.sh docker-compose.yml
```

No PowerShell não existe `touch`: use `New-Item -ItemType File -Force` para criar (ou esvaziar) arquivos. Cuidado: `-Force` em arquivo existente sobrescreve o conteúdo; para só atualizar a data use `(Get-Item "arquivo").LastWriteTime = Get-Date`.

---

## Como executar

_(Adicione aqui as instruções de instalação e execução do projeto.)_
