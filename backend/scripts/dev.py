#! /usr/bin/env python3
"""
Script de desenvolvimento para o backend.

Objetivo:
- Subir a API FastAPI em modo desenvolvimento usando Uvicorn com *hot reload*.
  (o servidor reinicia automaticamente quando você altera arquivos Python)

Quando usar:
- Durante o desenvolvimento local, para acelerar o ciclo “alterar código → ver resultado”.

Como executar (na pasta `backend/`):
- `uv run python scripts/dev.py`

O que este script faz:
- Ajusta `sys.path` para facilitar imports (dependendo do diretório de execução).
- Executa o processo do Uvicorn apontando para `app.api.main:app`.
"""

import subprocess
import sys
import os

def main():
    """
    Roda o servidor de desenvolvimento com hot reload.

    Fluxo:
    - Mostra uma mensagem no console para deixar claro que o servidor está iniciando.
    - Garante que o Python consiga localizar módulos do projeto no runtime.
    - Executa o Uvicorn em um subprocesso, com:
      - `--reload`: reinicia o servidor ao detectar mudanças no código
      - `--host 0.0.0.0`: escuta em todas as interfaces (útil para Docker/VM/rede local)
      - `--port 8000`: porta padrão do backend neste projeto
    """
    print("Iniciando servidor de desenvolvimento com hot reload...")

    # ---------------------------------------------------------------------
    # Ajuste de PATH de imports (sys.path)
    # ---------------------------------------------------------------------
    # Em alguns cenários, dependendo de onde o comando foi executado,
    # o Python pode não encontrar o pacote `app` corretamente.
    #
    # Aqui inserimos o diretório do script no início do sys.path para
    # garantir que os imports do projeto sejam resolvidos.
    #
    # Observação:
    # - Se você sempre roda a partir de `backend/`, em geral isso não é necessário,
    #   mas não atrapalha e deixa o script mais robusto.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # ---------------------------------------------------------------------
    # Execução do servidor Uvicorn
    # ---------------------------------------------------------------------
    # `subprocess.run([...])` inicia um processo filho e espera ele terminar.
    # Como o Uvicorn fica rodando (loop do servidor), este script “fica preso”
    # até você interromper (CTRL+C).
    #
    # O alvo `app.api.main:app` significa:
    # - módulo Python: `app.api.main`
    # - objeto ASGI: `app` (instância FastAPI definida naquele módulo)
    subprocess.run([
        "uvicorn",
        "app.api.main:app",
        "--reload",
        "--host", "0.0.0.0",
        "--port", "8000",
    ])

if __name__ == "__main__":
    # Ponto de entrada quando o script é executado diretamente.
    main()