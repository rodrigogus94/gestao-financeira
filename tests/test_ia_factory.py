"""
Testes do módulo app.services.ia.factory (IAProviderFactory).

Cobre:
- get_provider(tipo): criação da instância com o tipo correto, singleton
  (mesma instância na segunda chamada), e fallback para DEFAULT_IA_PROVIDER
  quando o tipo não está em PROVIDER_CONFIGS.
- listar_provedores_disponiveis(): retorno de uma lista com um item por
  provedor configurado, cada um com nome, tipo e status (disponivel/indisponivel).

Os testes usam mocks de IAProvider e de settings para não depender de
API keys ou rede. teardown_method limpa o cache _instance entre testes
para evitar vazamento de estado.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.services.ia.config import PROVIDER_CONFIGS
from app.services.ia.factory import IAProviderFactory
from app.services.ia.provider import IAProvider


# -----------------------------------------------------------------------------
# Testes da IAProviderFactory
# -----------------------------------------------------------------------------


class TestIAProviderFactory:
    """
    Garante que a factory cria e reutiliza provedores corretamente e que
    lista todos os provedores com status.
    """

    def teardown_method(self) -> None:
        """
        Limpa o cache de instâncias após cada teste para que um teste
        não reuse um provedor criado em outro (evita vazamento de estado).
        """
        IAProviderFactory._instance.clear()

    @patch("app.services.ia.factory.IAProvider")
    def test_get_provider_usa_tipo_e_cria_instancia(
        self, mock_ia_provider: MagicMock
    ) -> None:
        """get_provider("ollama") deve chamar IAProvider("ollama") e retornar a instância."""
        mock_ia_provider.return_value = MagicMock()
        p = IAProviderFactory.get_provider("ollama")
        mock_ia_provider.assert_called_once_with("ollama")
        assert p is mock_ia_provider.return_value

    @patch("app.services.ia.factory.IAProvider")
    def test_get_provider_retorna_mesma_instancia_segunda_chamada(
        self, mock_ia_provider: MagicMock
    ) -> None:
        """Duas chamadas get_provider("openai") devem retornar a mesma instância (singleton)."""
        mock_ia_provider.return_value = MagicMock()
        p1 = IAProviderFactory.get_provider("openai")
        p2 = IAProviderFactory.get_provider("openai")
        assert p1 is p2
        mock_ia_provider.assert_called_once_with("openai")

    @patch("app.services.ia.factory.settings")
    @patch("app.services.ia.factory.IAProvider")
    def test_get_provider_tipo_invalido_usa_default(
        self, mock_ia_provider: MagicMock, mock_settings: MagicMock
    ) -> None:
        """Tipo inexistente deve ser substituído por DEFAULT_IA_PROVIDER (ollama no mock)."""
        mock_settings.DEFAULT_IA_PROVIDER = "ollama"
        mock_ia_provider.return_value = MagicMock()
        p = IAProviderFactory.get_provider("provider_fake")
        mock_ia_provider.assert_called_with("ollama")

    def test_listar_provedores_disponiveis_retorna_lista(self) -> None:
        """
        listar_provedores_disponiveis deve retornar uma lista com um item por
        provedor em PROVIDER_CONFIGS. Cada item tem nome, tipo e status.
        Com o mock fazendo IAProvider levantar exceção, todos ficam indisponivel.
        """
        with patch("app.services.ia.factory.IAProvider") as mock_provider:
            mock_provider.side_effect = Exception("Sem API key")
            lista = IAProviderFactory.listar_provedores_disponiveis()
        assert isinstance(lista, list)
        assert len(lista) == len(PROVIDER_CONFIGS)
        for item in lista:
            assert "nome" in item
            assert "tipo" in item
            assert "status" in item
