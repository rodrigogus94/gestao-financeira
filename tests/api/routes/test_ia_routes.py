"""
Testes de integração das rotas de IA (`/api/ia`).

Sobrescreve dependências para usar fakes/mocks:
- get_current_user
- get_supabase_service
- get_ia_provider_manager
e também IAProviderFactory.get_provider/listar_provedores_disponiveis em pontos
específicos para evitar chamadas reais a provedores de IA.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient

from app.api.main import app
from app.api.deps import get_current_user, get_supabase_service, get_ia_provider_manager
from app.services.supabase_service import SupabaseService
from app.services.ia.manager import IAProviderManager
from app.services.ia.base import ExtracaoDespesa


class FakeSupabaseIA(SupabaseService):
    """Fake de SupabaseService focado em listar/salvar despesas para IA."""

    def __init__(self) -> None:  # type: ignore[override]
        self._despesas = []

    async def listar_despesas(  # type: ignore[override]
        self, usuario_id: str, limit: int = 50, **kwargs
    ):
        return self._despesas[:limit]

    async def salvar_despesa(self, despesa):  # type: ignore[override]
        # devolve um objeto com id para o teste de extrair_despesa
        class Obj:
            def __init__(self, id_: int) -> None:
                self.id = id_

        self._despesas.append(despesa)
        return Obj(len(self._despesas))


class FakeIAManagerRoutes(IAProviderManager):
    """Fake de IAProviderManager para extrair_despesa e gerar_insights."""

    def __init__(self) -> None:  # type: ignore[override]
        pass

    async def extrair_despesa(self, texto: str, provider_default: str | None = None):  # type: ignore[override]
        return ExtracaoDespesa(
            valor=50.0,
            categoria="alimentacao",
            data=datetime(2026, 3, 10).date(),
            descricao="Almoço teste",
            fonte="textual_natural",
            status="pendente",
            provedor=provider_default or "openai",
            confianca=0.9,
        )

    async def gerar_insights(self, resumo_mensal: dict, provedor: str | None = None) -> str:  # type: ignore[override]
        return "Insights de teste a partir do resumo."


fake_supabase = FakeSupabaseIA()
fake_manager = FakeIAManagerRoutes()


async def override_get_current_user() -> str:
    return "usuario-teste"


def override_get_supabase_service() -> SupabaseService:
    return fake_supabase


def override_get_ia_provider_manager() -> IAProviderManager:
    return fake_manager


app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[get_supabase_service] = override_get_supabase_service
app.dependency_overrides[get_ia_provider_manager] = override_get_ia_provider_manager


@pytest.mark.asyncio
async def test_listar_provedores() -> None:
    """Verifica que /api/ia/provedores retorna lista de provedores e estratégias."""
    with patch(
        "app.services.ia.factory.IAProviderFactory.listar_provedores_disponiveis",
        return_value=[{"nome": "OpenAI", "tipo": "openai", "status": "disponivel"}],
    ):
        async with AsyncClient(app=app, base_url="http://test") as client:
            resp = await client.get("/api/ia/provedores")
            assert resp.status_code == 200
            dados = resp.json()
            assert "provedores" in dados
            assert len(dados["provedores"]) == 1
            assert "estrategias" in dados


@pytest.mark.asyncio
async def test_extrair_despesa_sem_salvar() -> None:
    """Verifica que /api/ia/extrair-despesa retorna TextoResponse e não salva quando Salvar=False."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "texto": "Gastei 50 reais em almoço",
            "provedor": "openai",
            "estrategia": "principal",
            "Salvar": False,
        }
        resp = await client.post(
            "/api/ia/extrair-despesa",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp.status_code == 200
        dados = resp.json()
        assert dados["sucesso"] is True
        assert dados["extraido"]["valor"] == 50.0
        assert dados["estrategia"] == "principal"
        assert dados["despesa_id"] is None


@pytest.mark.asyncio
async def test_perguntar_usa_contexto_de_despesas_quando_nao_informado() -> None:
    """Verifica que /api/ia/perguntar monta contexto a partir de despesas quando contexto=None."""
    # prepara um provider fake para IAProviderFactory.get_provider
    provider = MagicMock()
    provider.perguntar = AsyncMock(return_value={"resposta": "ok"})

    with patch(
        "app.services.ia.factory.IAProviderFactory.get_provider",
        return_value=provider,
    ):
        async with AsyncClient(app=app, base_url="http://test") as client:
            payload = {
                "pergunta": "Quanto gastei?",
                "contexto": None,
                "provedor": "openai",
            }
            resp = await client.post(
                "/api/ia/perguntar",
                json=payload,
                headers={"Authorization": "Bearer test-token"},
            )
            assert resp.status_code == 200
            dados = resp.json()
            assert dados["pergunta"] == "Quanto gastei?"
            assert dados["resposta"] == {"resposta": "ok"}


@pytest.mark.asyncio
async def test_comparar_provedores() -> None:
    """Verifica que /api/ia/comparar retorna resultados para provedores listados."""
    async def _fake_extrair(texto: str) -> ExtracaoDespesa:
        return ExtracaoDespesa(
            valor=10.0,
            categoria="outros",
            data=datetime(2026, 3, 10).date(),
            descricao="x",
            fonte="textual_natural",
            status="pendente",
            provedor="fake",
            confianca=0.8,
        )

    def provider_side_effect(tipo: str):
        p = MagicMock()
        p.extrair_despesa = AsyncMock(side_effect=_fake_extrair)
        return p

    with patch(
        "app.services.ia.factory.IAProviderFactory.listar_provedores_disponiveis",
        return_value=[{"nome": "OpenAI", "tipo": "openai", "status": "disponivel"}],
    ), patch(
        "app.services.ia.factory.IAProviderFactory.get_provider",
        side_effect=provider_side_effect,
    ):
        async with AsyncClient(app=app, base_url="http://test") as client:
            resp = await client.post(
                "/api/ia/comparar",
                json={"texto": "Almoço 10"},
                headers={"Authorization": "Bearer test-token"},
            )
            assert resp.status_code == 200
            dados = resp.json()
            assert dados["texto_original"] == "Almoço 10"
            assert "openai" in dados["resultados"]

