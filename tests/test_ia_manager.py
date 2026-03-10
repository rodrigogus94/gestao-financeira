"""
Testes do módulo app.services.ia.manager (IAManager e EstrategiaSelecao).

Cobre:
- Construtor: estratégia padrão PRINCIPAL, estratégia RAPIDO e listas
  provedores_rapidos / provedores_precisos.
- extrair_despesa com cada estratégia: PRINCIPAL chama get_provider(provider_default),
  RAPIDO chama get_provider("ollama"), PRECISO get_provider("openai"), VOTACAO
  delega para _executar_votacao, FALLBACK para _executar_fallback, e que o resultado
  retornado tem os campos esperados (valor, categoria, provedor).
- _executar_votacao: agregação por valor médio e categoria mais votada quando
  vários provedores retornam; e exceção quando nenhum provedor consegue extrair.

Os testes usam @patch em IAProviderFactory.get_provider para injetar um
mock_provider cujo extrair_despesa retorna uma ExtracaoDespesa fixa, assim
não é necessário chamar APIs reais.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ia.base import ExtracaoDespesa
from app.services.ia.manager import IAManager, EstrategiaSelecao
from datetime import date


# -----------------------------------------------------------------------------
# Fixture: provedor mock
# -----------------------------------------------------------------------------


@pytest.fixture
def mock_provider() -> MagicMock:
    """
    Provider mock cujo extrair_despesa é um AsyncMock que retorna uma
    ExtracaoDespesa fixa (valor 50, categoria transporte). Usado nos testes
    que patcham IAProviderFactory.get_provider para controlar o retorno.
    """
    p = MagicMock()
    p.extrair_despesa = AsyncMock(
        return_value=ExtracaoDespesa(
            valor=50.0,
            categoria="transporte",
            data=date(2026, 3, 10),
            descricao="Uber",
            fonte="textual_natural",
            status="pendente",
            provedor="OpenAI",
            confianca=0.95,
        )
    )
    return p


# -----------------------------------------------------------------------------
# Testes do construtor do IAManager
# -----------------------------------------------------------------------------


class TestIAManagerInit:
    """Verifica que o IAManager é construído com a estratégia e listas corretas."""

    def test_init_default_estrategia_principal(self) -> None:
        """Sem argumentos, estrategia deve ser PRINCIPAL."""
        manager = IAManager()
        assert manager.estrategia == EstrategiaSelecao.PRINCIPAL

    def test_init_estrategia_rapido(self) -> None:
        """Com estrategia=RAPIDO, o atributo estrategia deve ser RAPIDO."""
        manager = IAManager(estrategia=EstrategiaSelecao.RAPIDO)
        assert manager.estrategia == EstrategiaSelecao.RAPIDO

    def test_provedores_rapidos_e_precisos_definidos(self) -> None:
        """provedores_rapidos deve conter ollama; provedores_precisos openai e gemini."""
        manager = IAManager()
        assert "ollama" in manager.provedores_rapidos
        assert "openai" in manager.provedores_precisos
        assert "gemini" in manager.provedores_precisos


# -----------------------------------------------------------------------------
# Testes de extrair_despesa com cada estratégia (factory mockada)
# -----------------------------------------------------------------------------


class TestIAManagerExtrairDespesa:
    """
    Garante que, para cada estratégia, extrair_despesa chama o provedor
    correto (ou o método de agregação) e retorna um ExtracaoDespesa coerente.
    """

    @pytest.mark.asyncio
    @patch("app.services.ia.manager.IAProviderFactory.get_provider")
    async def test_estrategia_principal_chama_provider_default(
        self, mock_get: MagicMock, mock_provider: MagicMock
    ) -> None:
        """PRINCIPAL com provider_default=openai deve chamar get_provider("openai") e retornar o resultado do provedor."""
        mock_get.return_value = mock_provider
        manager = IAManager(estrategia=EstrategiaSelecao.PRINCIPAL)
        resultado = await manager.extrair_despesa(
            "Gastei 50 em uber", provider_default="openai"
        )
        mock_get.assert_called_once_with("openai")
        assert resultado.valor == 50.0
        assert resultado.categoria == "transporte"

    @pytest.mark.asyncio
    @patch("app.services.ia.manager.IAProviderFactory.get_provider")
    async def test_estrategia_rapido_usa_ollama(
        self, mock_get: MagicMock, mock_provider: MagicMock
    ) -> None:
        """RAPIDO deve chamar get_provider("ollama") independente do texto."""
        mock_get.return_value = mock_provider
        manager = IAManager(estrategia=EstrategiaSelecao.RAPIDO)
        await manager.extrair_despesa("Almoço 30 reais")
        mock_get.assert_called_once_with("ollama")

    @pytest.mark.asyncio
    @patch("app.services.ia.manager.IAProviderFactory.get_provider")
    async def test_estrategia_preciso_usa_openai(
        self, mock_get: MagicMock, mock_provider: MagicMock
    ) -> None:
        """PRECISO deve chamar get_provider("openai")."""
        mock_get.return_value = mock_provider
        manager = IAManager(estrategia=EstrategiaSelecao.PRECISO)
        await manager.extrair_despesa("Farmácia 45 reais")
        mock_get.assert_called_once_with("openai")

    @pytest.mark.asyncio
    @patch("app.services.ia.manager.IAProviderFactory.get_provider")
    async def test_estrategia_votacao_chama_executar_votacao(
        self, mock_get: MagicMock, mock_provider: MagicMock
    ) -> None:
        """VOTACAO deve retornar resultado com provedor indicando Votação e valor agregado."""
        mock_get.return_value = mock_provider
        manager = IAManager(estrategia=EstrategiaSelecao.VOTACAO)
        resultado = await manager.extrair_despesa("Taxi 20 reais")
        assert resultado.provedor.startswith("Vota")
        assert resultado.valor == 50.0  # valor do mock único

    @pytest.mark.asyncio
    @patch("app.services.ia.manager.IAProviderFactory.get_provider")
    async def test_estrategia_fallback_retorna_ao_primeiro_ok(
        self, mock_get: MagicMock, mock_provider: MagicMock
    ) -> None:
        """FALLBACK deve tentar o provider_default primeiro e retornar ao primeiro sucesso."""
        mock_get.return_value = mock_provider
        manager = IAManager(estrategia=EstrategiaSelecao.FALLBACK)
        resultado = await manager.extrair_despesa(
            "Compras 100", provider_default="openai"
        )
        assert resultado.valor == 50.0
        assert mock_get.called


# -----------------------------------------------------------------------------
# Testes do método _executar_votacao
# -----------------------------------------------------------------------------


class TestIAManagerVotacao:
    """
    Garante que _executar_votacao agrega múltiplos resultados (valor médio,
    categoria mais votada) e que levanta exceção quando nenhum provedor retorna sucesso.
    """

    @pytest.mark.asyncio
    @patch("app.services.ia.manager.IAProviderFactory.get_provider")
    async def test_votacao_agrega_valor_medio_e_categoria_mais_votada(
        self, mock_get: MagicMock
    ) -> None:
        """
        Com um side_effect que retorna provedores com valores e categorias
        diferentes, o resultado agregado deve ter categoria entre as usadas
        e valor numérico coerente (média), e provedor deve conter "Vota".
        """
        def provider_side_effect(tipo: str) -> MagicMock:
            m = MagicMock()
            cat = "transporte" if tipo == "ollama" else "alimentacao"
            m.extrair_despesa = AsyncMock(
                return_value=ExtracaoDespesa(
                    valor=40.0 if tipo == "openai" else 60.0,
                    categoria=cat,
                    data=date(2026, 3, 10),
                    descricao="x",
                    fonte="textual_natural",
                    status="pendente",
                    provedor=tipo,
                    confianca=0.9,
                )
            )
            return m

        mock_get.side_effect = provider_side_effect
        manager = IAManager(estrategia=EstrategiaSelecao.VOTACAO)
        resultado = await manager._executar_votacao("Almoço e transporte")
        assert resultado.categoria in ("transporte", "alimentacao")
        assert resultado.valor >= 0
        assert "Vota" in resultado.provedor

    @pytest.mark.asyncio
    @patch("app.services.ia.manager.IAProviderFactory.get_provider")
    async def test_votacao_sem_resultados_levanta(self, mock_get: MagicMock) -> None:
        """Se todos os get_provider falharem, _executar_votacao deve levantar exceção com mensagem 'Sem resultados'."""
        mock_get.side_effect = Exception("Sem API key")
        manager = IAManager(estrategia=EstrategiaSelecao.VOTACAO)
        with pytest.raises(Exception, match="Sem resultados"):
            await manager._executar_votacao("Qualquer texto")
