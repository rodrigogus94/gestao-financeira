"""
Configuração compartilhada para todos os testes do projeto (pytest).

Este arquivo é carregado automaticamente pelo pytest antes dos módulos de teste.
Ele faz três coisas principais:

1. Define variáveis de ambiente mínimas (SUPABASE_*) antes de qualquer import
   do pacote app, para que app.core.config.Settings() consiga instanciar sem
   exigir um arquivo .env. Caso contrário, ao importar app.services.ia.config
   (ou qualquer módulo que use settings), o Pydantic levantaria ValidationError
   por campos obrigatórios faltando.

2. Importa pytest e os mocks necessários, e o modelo ExtracaoDespesa usado
   em várias fixtures.

3. Declara fixtures reutilizáveis: extracao_exemplo (uma ExtracaoDespesa
   pronta para testes) e texto_despesa (uma string de exemplo de despesa em
   linguagem natural). Qualquer teste ou outro conftest pode usar essas
   fixtures declarando o nome no parâmetro da função de teste.
"""

import os

# -----------------------------------------------------------------------------
# Variáveis de ambiente para testes (antes de importar app)
# -----------------------------------------------------------------------------
# Definir env antes de qualquer import de app evita ValidationError ao carregar
# Settings() em app.core.config. Os valores são placeholders apenas para
# os testes passarem; testes que dependem de Supabase real devem usar
# variáveis de ambiente reais ou mocks.
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ia.base import ExtracaoDespesa


# -----------------------------------------------------------------------------
# Fixtures compartilhadas
# -----------------------------------------------------------------------------


@pytest.fixture
def extracao_exemplo() -> ExtracaoDespesa:
    """
    Retorna uma ExtracaoDespesa de exemplo para usar em testes.

    Contém valor 50.0, categoria transporte, data fixa, descrição "Uber para o trabalho",
    fonte textual_natural, status pendente, provedor OpenAI e confiança 0.95.
    Útil para testar serialização, comparações ou como valor esperado em mocks.
    """
    return ExtracaoDespesa(
        valor=50.0,
        categoria="transporte",
        data=date(2026, 3, 10),
        descricao="Uber para o trabalho",
        fonte="textual_natural",
        status="pendente",
        provedor="OpenAI",
        confianca=0.95,
    )


@pytest.fixture
def texto_despesa() -> str:
    """
    Retorna um texto de despesa em linguagem natural para testes.

    Exemplo: "Gastei 50 reais em Uber ontem para ir ao trabalho".
    Usado em testes de extração de despesa, prompts e fallbacks.
    """
    return "Gastei 50 reais em Uber ontem para ir ao trabalho"
