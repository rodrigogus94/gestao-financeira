"""
Testes de integração das rotas de despesas (`/api/despesas`).

Usam httpx.AsyncClient com a app FastAPI em memória e sobrescrevem as
dependências `get_current_user` e `get_supabase_service` para não chamar
Supabase real nem exigir autenticação de verdade.
"""

import pytest
from httpx import AsyncClient

from app.api.main import app
from app.api.deps import get_current_user, get_supabase_service
from app.models.domain.despesa import (
    CategoriaDespesa,
    DespesaCreate,
    DespesaInDB,
    DespesaUpdate,
)
from app.services.supabase_service import SupabaseService


class FakeSupabaseService(SupabaseService):
    """Implementação fake mínima para testar as rotas sem acessar o banco."""

    def __init__(self) -> None:  # type: ignore[override]
        # Não chama o __init__ real que cria cliente Supabase
        self._despesas: dict[int, DespesaInDB] = {}
        self._next_id = 1

    async def salvar_despesa(self, despesa: DespesaCreate) -> DespesaInDB:  # type: ignore[override]
        nova = DespesaInDB(
            id=self._next_id,
            usuario_id=despesa.usuario_id,
            valor=despesa.valor,
            categoria=despesa.categoria,
            data=despesa.data,
            descricao=despesa.descricao,
            fonte=despesa.fonte,
            status=despesa.status,
            metadata=despesa.metadata,
            created_at=None,
            updated_at=None,
        )
        self._despesas[self._next_id] = nova
        self._next_id += 1
        return nova

    async def listar_despesas(  # type: ignore[override]
        self,
        usuario_id: str,
        data_inicio=None,
        data_fim=None,
        categoria: CategoriaDespesa | None = None,
        limit: int = 100,
    ) -> list[DespesaInDB]:
        despesas = [d for d in self._despesas.values() if d.usuario_id == usuario_id]
        if categoria is not None:
            despesas = [d for d in despesas if d.categoria == categoria]
        return despesas[:limit]

    async def buscar_despesa(  # type: ignore[override]
        self, despesa_id: int, usuario_id: str
    ) -> DespesaInDB | None:
        d = self._despesas.get(despesa_id)
        if d and d.usuario_id == usuario_id:
            return d
        return None

    async def atualizar_despesa(  # type: ignore[override]
        self, despesa_id: int, usuario_id: str, dados: dict
    ) -> DespesaInDB | None:
        d = await self.buscar_despesa(despesa_id, usuario_id)
        if not d:
            return None
        for k, v in dados.items():
            setattr(d, k, v)
        self._despesas[despesa_id] = d
        return d

    async def deletar_despesa(  # type: ignore[override]
        self, despesa_id: int, usuario_id: str
    ) -> bool:
        d = await self.buscar_despesa(despesa_id, usuario_id)
        if not d:
            return False
        del self._despesas[despesa_id]
        return True


fake_service = FakeSupabaseService()


async def override_get_current_user() -> str:
    return "usuario-teste"


def override_get_supabase_service() -> SupabaseService:
    return fake_service


app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[get_supabase_service] = override_get_supabase_service


@pytest.mark.asyncio
async def test_criar_e_listar_despesas() -> None:
    """Cria uma despesa via POST /api/despesas/ e verifica se aparece no GET /api/despesas/."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "usuario_id": "ignorado-pelo-backend",
            "valor": 50.0,
            "categoria": "alimentacao",
            "data": "2026-03-10",
            "descricao": "Almoço",
            "fonte": "manual",
        }
        resp = await client.post(
            "/api/despesas/",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp.status_code == 200
        criada = resp.json()
        assert criada["valor"] == 50.0
        assert criada["categoria"] == "alimentacao"

        resp_lista = await client.get(
            "/api/despesas/",
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp_lista.status_code == 200
        lista = resp_lista.json()
        assert len(lista) >= 1
        assert any(d["descricao"] == "Almoço" for d in lista)


@pytest.mark.asyncio
async def test_buscar_atualizar_e_deletar_despesa() -> None:
    """Fluxo completo: cria, busca, atualiza e deleta uma despesa."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # cria
        payload = {
            "usuario_id": "ignorado",
            "valor": 30.0,
            "categoria": "transporte",
            "data": "2026-03-11",
            "descricao": "Uber",
            "fonte": "manual",
        }
        resp = await client.post(
            "/api/despesas/",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        )
        criada = resp.json()
        despesa_id = criada["id"]

        # busca
        resp_busca = await client.get(
            f"/api/despesas/{despesa_id}",
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp_busca.status_code == 200
        assert resp_busca.json()["descricao"] == "Uber"

        # atualiza
        resp_update = await client.put(
            f"/api/despesas/{despesa_id}",
            json={"descricao": "Uber trabalho"},
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp_update.status_code == 200
        assert resp_update.json()["descricao"] == "Uber trabalho"

        # deleta
        resp_delete = await client.delete(
            f"/api/despesas/{despesa_id}",
            headers={"Authorization": "Bearer test-token"},
        )
        assert resp_delete.status_code == 200
        assert resp_delete.json()["message"] == "Despesa deletada com sucesso"

