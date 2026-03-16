"""
Testes de integração das rotas de relatórios (`/api/relatorios`).

Sobrescreve `get_current_user`, `get_supabase_service` e `get_ia_provider_manager`
para não depender de Supabase nem de providers de IA reais.
"""

import pytest
from datetime import date
from httpx import AsyncClient

from app.api.main import app
from app.api.deps import get_current_user, get_supabase_service, get_ia_provider_manager
from app.services.supabase_service import SupabaseService
from app.services.ia.manager import IAProviderManager


class FakeSupabaseRelatorios(SupabaseService):
    """Fake de SupabaseService focado nos métodos de relatório."""

    def __init__(self) -> None:  # type: ignore[override]
        pass

    async def get_resumo_mensal(  # type: ignore[override]
        self, usuario_id: str, ano: int, mes: int
    ) -> dict:
        return {
            "total": 100.0,
            "categorias": {"alimentacao": 60.0, "transporte": 40.0},
            "quantidade": 2,
            "media_por_dia": 3.33,
            "maior_despesa": 60.0,
            "periodo": {
                "inicio": f"{ano:04d}-{mes:02d}-01",
                "fim": f"{ano:04d}-{(mes % 12) + 1:02d}-01",
            },
        }

    async def get_despesas_por_categoria(  # type: ignore[override]
        self, usuario_id: str, data_inicio: date, data_fim: date
    ) -> dict:
        return {"alimentacao": 80.0, "transporte": 20.0}

    async def get_evolucao_mensal(  # type: ignore[override]
        self, usuario_id: str, ano: int, mes: int
    ) -> list[dict]:
        return [{"mes": i, "total": float(i * 10)} for i in range(1, 13)]


class FakeIAManager(IAProviderManager):
    """Fake de IAProviderManager que devolve um texto fixo de insights."""

    def __init__(self) -> None:  # type: ignore[override]
        pass

    async def gerar_insights(self, resumo_mensal: dict, provedor: str | None = None) -> str:  # type: ignore[override]
        return "Insights de teste gerados com sucesso."


fake_supabase = FakeSupabaseRelatorios()
fake_ia_manager = FakeIAManager()


async def override_get_current_user() -> str:
    return "usuario-teste"


def override_get_supabase_service() -> SupabaseService:
    return fake_supabase


def override_get_ia_provider_manager() -> IAProviderManager:
    return fake_ia_manager


app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[get_supabase_service] = override_get_supabase_service
app.dependency_overrides[get_ia_provider_manager] = override_get_ia_provider_manager


@pytest.mark.asyncio
async def test_relatorio_mensal() -> None:
    """Verifica que /api/relatorios/mensal retorna o resumo fake."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get(
            "/api/relatorios/mensal?ano=2026&mes=3",
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp.status_code == 200
        dados = resp.json()
        assert dados["total"] == 100.0
        assert dados["quantidade"] == 2


@pytest.mark.asyncio
async def test_gastos_por_categoria() -> None:
    """Verifica que /api/relatorios/categoria retorna o dict de categorias fake."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get(
            "/api/relatorios/categoria?data_inicio=2026-03-01&data_fim=2026-03-31",
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp.status_code == 200
        dados = resp.json()
        assert dados["alimentacao"] == 80.0
        assert dados["transporte"] == 20.0


@pytest.mark.asyncio
async def test_evolucao_mensal() -> None:
    """Verifica que /api/relatorios/evolucao/{ano} retorna 12 itens."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get(
            "/api/relatorios/evolucao/2026",
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp.status_code == 200
        dados = resp.json()
        assert len(dados) == 12
        assert dados[0]["mes"] == 1


@pytest.mark.asyncio
async def test_gerar_insights() -> None:
    """Verifica que /api/relatorios/insights retorna o texto de insights fake."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.post(
            "/api/relatorios/insights?ano=2026&mes=3",
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp.status_code == 200
        dados = resp.json()
        assert "insights" in dados
        assert dados["insights"].startswith("Insights de teste")

