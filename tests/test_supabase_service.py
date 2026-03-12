"""
Testes do SupabaseService (backend/app/services/supabase_service.py).

Cobre CRUD de despesas (salvar, listar, atualizar, deletar) e relatórios
(get_resumo_mensal, get_despesas_por_categoria, get_evolucao_mensal).
O cliente Supabase é mockado para não depender de banco real; cada teste
configura o retorno esperado do mock (response.data).
"""

import pytest
from datetime import date, datetime
from unittest.mock import MagicMock, patch, AsyncMock

from app.models.domain.despesa import (
    CategoriaDespesa,
    DespesaCreate,
    DespesaInDB,
    FonteDespesa,
)
from app.services.supabase_service import SupabaseService


# -----------------------------------------------------------------------------
# Fixtures: dados de exemplo e mock do cliente Supabase
# -----------------------------------------------------------------------------


@pytest.fixture
def usuario_id() -> str:
    """ID de usuário fictício para filtrar despesas."""
    return "user-uuid-123"


@pytest.fixture
def despesa_create(usuario_id: str) -> DespesaCreate:
    """DespesaCreate de exemplo para salvar no banco."""
    return DespesaCreate(
        usuario_id=usuario_id,
        valor=100.50,
        categoria=CategoriaDespesa.ALIMENTACAO,
        data=date(2026, 3, 15),
        descricao="Supermercado",
        fonte=FonteDespesa.MANUAL,
    )


@pytest.fixture
def despesa_in_db(usuario_id: str) -> dict:
    """Dict no formato retornado pelo Supabase (response.data[0]) para uma despesa."""
    return {
        "id": 1,
        "usuario_id": usuario_id,
        "valor": 100.50,
        "categoria": "alimentacao",
        "data": "2026-03-15",
        "descricao": "Supermercado",
        "fonte": "manual",
        "status": "pendente",
        "metadata": None,
        "created_at": "2026-03-15T10:00:00",
        "updated_at": "2026-03-15T10:00:00",
    }


def _make_table_mock(execute_return: object):
    """Monta um mock encadeado para client.table('despesas').insert/select/update/delete."""
    table = MagicMock()
    # insert(data).execute() -> execute_return
    insert_chain = MagicMock()
    insert_chain.execute = AsyncMock(return_value=execute_return)
    table.insert.return_value = insert_chain
    # select().eq().order().limit() e .gte/.lte/.eq encadeados
    query_chain = MagicMock()
    query_chain.eq.return_value = query_chain
    query_chain.order.return_value = query_chain
    query_chain.limit.return_value = query_chain
    query_chain.gte.return_value = query_chain
    query_chain.lte.return_value = query_chain
    query_chain.execute = AsyncMock(return_value=execute_return)
    table.select.return_value = query_chain
    # update(dados).eq().eq().execute()
    update_chain = MagicMock()
    update_chain.eq.return_value = update_chain
    update_chain.execute.return_value = execute_return
    table.update.return_value = update_chain
    # delete().eq().eq().execute()
    delete_chain = MagicMock()
    delete_chain.eq.return_value = delete_chain
    delete_chain.execute.return_value = execute_return
    table.delete.return_value = delete_chain
    return table


@pytest.fixture
def mock_supabase_client(despesa_in_db: dict):
    """Cliente Supabase mockado: table('despesas') retorna chain com execute() retornando .data."""
    client = MagicMock()
    response_insert = MagicMock()
    response_insert.data = [despesa_in_db]
    client.table.return_value = _make_table_mock(response_insert)
    return client


# -----------------------------------------------------------------------------
# Testes: inicialização e salvar_despesa
# -----------------------------------------------------------------------------


class TestSupabaseServiceInit:
    """Verifica que o serviço inicializa com create_client(URL, KEY)."""

    @patch("app.services.supabase_service.create_client")
    def test_init_cria_cliente_com_url_e_key(
        self, mock_create: MagicMock, mock_supabase_client: MagicMock
    ) -> None:
        mock_create.return_value = mock_supabase_client
        service = SupabaseService()
        mock_create.assert_called_once()
        args = mock_create.call_args[0]
        assert len(args) >= 2
        assert "supabase" in args[0].lower() or "test" in args[0].lower()
        assert service.client is mock_supabase_client


class TestSalvarDespesa:
    """Testes de salvar_despesa: insert e conversão para DespesaInDB."""

    @pytest.mark.asyncio
    @patch("app.services.supabase_service.create_client")
    async def test_salvar_despesa_retorna_despesa_in_db(
        self,
        mock_create: MagicMock,
        mock_supabase_client: MagicMock,
        despesa_create: DespesaCreate,
        despesa_in_db: dict,
    ) -> None:
        mock_create.return_value = mock_supabase_client
        service = SupabaseService()
        result = await service.salvar_despesa(despesa_create)
        assert isinstance(result, DespesaInDB)
        assert result.id == despesa_in_db["id"]
        assert result.valor == despesa_in_db["valor"]
        assert result.categoria.value == despesa_in_db["categoria"]
        assert result.usuario_id == despesa_create.usuario_id

    @pytest.mark.asyncio
    @patch("app.services.supabase_service.create_client")
    async def test_salvar_despesa_sem_dados_retornados_levanta(
        self, mock_create: MagicMock, despesa_create: DespesaCreate
    ) -> None:
        response_empty = MagicMock()
        response_empty.data = []
        client = MagicMock()
        client.table.return_value = _make_table_mock(response_empty)
        mock_create.return_value = client
        service = SupabaseService()
        with pytest.raises(Exception, match="sem dados retornados"):
            await service.salvar_despesa(despesa_create)


# -----------------------------------------------------------------------------
# Testes: listar_despesas
# -----------------------------------------------------------------------------


class TestListarDespesas:
    """Testes de listar_despesas: filtros e conversão para list[DespesaInDB]."""

    @pytest.mark.asyncio
    @patch("app.services.supabase_service.create_client")
    async def test_listar_despesas_retorna_lista_de_despesa_in_db(
        self,
        mock_create: MagicMock,
        mock_supabase_client: MagicMock,
        usuario_id: str,
        despesa_in_db: dict,
    ) -> None:
        mock_create.return_value = mock_supabase_client
        service = SupabaseService()
        lista = await service.listar_despesas(usuario_id)
        assert len(lista) == 1
        assert lista[0].id == despesa_in_db["id"]
        assert lista[0].valor == despesa_in_db["valor"]

    @pytest.mark.asyncio
    @patch("app.services.supabase_service.create_client")
    async def test_listar_despesas_com_filtros_aplica_query(
        self,
        mock_create: MagicMock,
        mock_supabase_client: MagicMock,
        usuario_id: str,
    ) -> None:
        response = MagicMock()
        response.data = []
        mock_supabase_client.table.return_value = _make_table_mock(response)
        mock_create.return_value = mock_supabase_client
        service = SupabaseService()
        data_inicio = date(2026, 3, 1)
        data_fim = date(2026, 3, 31)
        await service.listar_despesas(
            usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            categoria=CategoriaDespesa.TRANSPORTE,
            limit=50,
        )
        table = mock_supabase_client.table.return_value
        table.select.return_value.gte.assert_called_once_with(
            "data", data_inicio.isoformat()
        )
        table.select.return_value.lte.assert_called_once_with(
            "data", data_fim.isoformat()
        )
        table.select.return_value.eq.assert_any_call("usuario_id", usuario_id)
        table.select.return_value.eq.assert_any_call(
            "categoria", CategoriaDespesa.TRANSPORTE.value
        )

    @pytest.mark.asyncio
    @patch("app.services.supabase_service.create_client")
    async def test_listar_despesas_em_erro_retorna_lista_vazia(
        self, mock_create: MagicMock, usuario_id: str
    ) -> None:
        client = MagicMock()
        query = MagicMock()
        query.eq.return_value = query
        query.order.return_value = query
        query.limit.return_value = query
        query.execute = AsyncMock(side_effect=Exception("Erro de rede"))
        client.table.return_value.select.return_value = query
        mock_create.return_value = client
        service = SupabaseService()
        lista = await service.listar_despesas(usuario_id)
        assert lista == []


# -----------------------------------------------------------------------------
# Testes: atualizar_despesa e deletar_despesa
# -----------------------------------------------------------------------------


class TestAtualizarDespesa:
    """Testes de atualizar_despesa: update e retorno DespesaInDB ou None."""

    @pytest.mark.asyncio
    @patch("app.services.supabase_service.create_client")
    async def test_atualizar_despesa_com_dados_retorna_despesa_in_db(
        self,
        mock_create: MagicMock,
        despesa_in_db: dict,
        usuario_id: str,
    ) -> None:
        despesa_in_db["valor"] = 150.0
        response = MagicMock()
        response.data = [despesa_in_db]
        client = MagicMock()
        client.table.return_value = _make_table_mock(response)
        mock_create.return_value = client
        service = SupabaseService()
        result = await service.atualizar_despesa(
            1, usuario_id, {"valor": 150.0, "descricao": "Atualizado"}
        )
        assert result is not None
        assert result.valor == 150.0

    @pytest.mark.asyncio
    @patch("app.services.supabase_service.create_client")
    async def test_atualizar_despesa_sem_registro_retorna_none(
        self, mock_create: MagicMock, usuario_id: str
    ) -> None:
        response = MagicMock()
        response.data = []
        client = MagicMock()
        client.table.return_value = _make_table_mock(response)
        mock_create.return_value = client
        service = SupabaseService()
        result = await service.atualizar_despesa(
            999, usuario_id, {"descricao": "Não existe"}
        )
        assert result is None


class TestDeletarDespesa:
    """Testes de deletar_despesa: delete e retorno bool."""

    @pytest.mark.asyncio
    @patch("app.services.supabase_service.create_client")
    async def test_deletar_despesa_com_registro_retorna_true(
        self,
        mock_create: MagicMock,
        despesa_in_db: dict,
        usuario_id: str,
    ) -> None:
        response = MagicMock()
        response.data = [despesa_in_db]
        client = MagicMock()
        client.table.return_value = _make_table_mock(response)
        mock_create.return_value = client
        service = SupabaseService()
        result = await service.deletar_despesa(1, usuario_id)
        assert result is True

    @pytest.mark.asyncio
    @patch("app.services.supabase_service.create_client")
    async def test_deletar_despesa_sem_registro_retorna_false(
        self, mock_create: MagicMock, usuario_id: str
    ) -> None:
        response = MagicMock()
        response.data = []
        client = MagicMock()
        client.table.return_value = _make_table_mock(response)
        mock_create.return_value = client
        service = SupabaseService()
        result = await service.deletar_despesa(999, usuario_id)
        assert result is False


# -----------------------------------------------------------------------------
# Testes: get_resumo_mensal, get_despesas_por_categoria, get_evolucao_mensal
# -----------------------------------------------------------------------------


class TestResumoMensal:
    """Testes de get_resumo_mensal: estrutura do dict e cálculo com/sem despesas."""

    @pytest.mark.asyncio
    @patch("app.services.supabase_service.create_client")
    async def test_get_resumo_mensal_sem_despesas_retorna_zeros(
        self, mock_create: MagicMock, usuario_id: str
    ) -> None:
        response = MagicMock()
        response.data = []
        client = MagicMock()
        client.table.return_value = _make_table_mock(response)
        mock_create.return_value = client
        service = SupabaseService()
        resumo = await service.get_resumo_mensal(usuario_id, 2026, 3)
        assert resumo["total"] == 0
        assert resumo["categorias"] == {}
        assert resumo["quantidade"] == 0
        assert resumo["media_por_dia"] == 0
        assert resumo["maior_despesa"] == 0
        assert "periodo" in resumo
        assert resumo["periodo"]["inicio"] == "2026-03-01"
        assert resumo["periodo"]["fim"] == "2026-04-01"

    @pytest.mark.asyncio
    @patch("app.services.supabase_service.create_client")
    async def test_get_resumo_mensal_com_despesas_calcula_total_e_categorias(
        self,
        mock_create: MagicMock,
        despesa_in_db: dict,
        usuario_id: str,
    ) -> None:
        despesa2 = {**despesa_in_db, "id": 2, "valor": 50.0, "categoria": "transporte"}
        response = MagicMock()
        response.data = [despesa_in_db, despesa2]
        client = MagicMock()
        client.table.return_value = _make_table_mock(response)
        mock_create.return_value = client
        service = SupabaseService()
        resumo = await service.get_resumo_mensal(usuario_id, 2026, 3)
        assert resumo["total"] == 150.50
        assert resumo["quantidade"] == 2
        assert "alimentacao" in resumo["categorias"]
        assert "transporte" in resumo["categorias"]
        assert resumo["maior_despesa"] == 100.50
        assert resumo["media_por_dia"] > 0


class TestDespesasPorCategoria:
    """Testes de get_despesas_por_categoria: agregação por categoria."""

    @pytest.mark.asyncio
    @patch("app.services.supabase_service.create_client")
    async def test_get_despesas_por_categoria_soma_por_categoria(
        self,
        mock_create: MagicMock,
        despesa_in_db: dict,
        usuario_id: str,
    ) -> None:
        despesa2 = {**despesa_in_db, "id": 2, "valor": 80.0, "categoria": "alimentacao"}
        response = MagicMock()
        response.data = [despesa_in_db, despesa2]
        client = MagicMock()
        client.table.return_value = _make_table_mock(response)
        mock_create.return_value = client
        service = SupabaseService()
        resultado = await service.get_despesas_por_categoria(
            usuario_id, date(2026, 3, 1), date(2026, 3, 31)
        )
        assert resultado["alimentacao"] == 180.50


class TestEvolucaoMensal:
    """Testes de get_evolucao_mensal: 12 meses com mes e total."""

    @pytest.mark.asyncio
    @patch("app.services.supabase_service.create_client")
    async def test_get_evolucao_mensal_retorna_12_itens(
        self, mock_create: MagicMock, usuario_id: str
    ) -> None:
        response = MagicMock()
        response.data = []
        client = MagicMock()
        client.table.return_value = _make_table_mock(response)
        mock_create.return_value = client
        service = SupabaseService()
        resultado = await service.get_evolucao_mensal(usuario_id, 2026, 3)
        assert len(resultado) == 12
        for i, item in enumerate(resultado):
            assert item["mes"] == i + 1
            assert "total" in item
