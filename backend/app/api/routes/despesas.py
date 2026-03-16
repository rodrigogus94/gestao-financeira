"""
Rotas da API para CRUD de despesas.

Expõe endpoints REST sob o prefixo `/despesas` para criar, listar, buscar,
atualizar e deletar despesas do usuário autenticado. Toda a persistência é
delegada ao `SupabaseService`, e o usuário atual é obtido via `get_current_user`,
garantindo que cada operação seja filtrada por `usuario_id`.
"""

from datetime import date
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user, get_supabase_service
from app.models.domain.despesa import (
    CategoriaDespesa,
    DespesaCreate,
    DespesaInDB,
    DespesaUpdate,
)
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/despesas", tags=["despesas"])


@router.post("/", response_model=DespesaInDB)
async def criar_despesa(
    despesa: DespesaCreate,
    usuario_id: str = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
) -> DespesaInDB:
    """
    Cria uma nova despesa para o usuário autenticado.

    - Usa o corpo `DespesaCreate` enviado pelo cliente.
    - Força o `usuario_id` da despesa para o usuário autenticado (não confia no body).
    - Persiste a despesa via `SupabaseService.salvar_despesa`.
    """
    try:
        despesa.usuario_id = usuario_id
        return await supabase.salvar_despesa(despesa)
    except Exception as e:
        logger.error("Erro ao criar despesa: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/", response_model=list[DespesaInDB])
async def listar_despesas(
    data_inicio: date | None = Query(
        None,
        description="Data inicial (inclusive) para filtro de despesas.",
    ),
    data_fim: date | None = Query(
        None,
        description="Data final (inclusive) para filtro de despesas.",
    ),
    categoria: CategoriaDespesa | None = Query(
        None,
        description="Categoria da despesa para filtro opcional.",
    ),
    limit: int = Query(
        100,
        le=500,
        description="Número máximo de registros a retornar (padrão 100, máximo 500).",
    ),
    usuario_id: str = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
) -> list[DespesaInDB]:
    """
    Lista despesas do usuário autenticado com filtros opcionais.

    Filtros disponíveis:
    - `data_inicio` / `data_fim`: intervalo de datas.
    - `categoria`: filtra por categoria específica.
    - `limit`: limite máximo de registros.
    """
    try:
        return await supabase.listar_despesas(
            usuario_id=usuario_id,
            data_inicio=data_inicio,
            data_fim=data_fim,
            categoria=categoria,
            limit=limit,
        )
    except Exception as e:
        logger.error("Erro ao listar despesas: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{despesa_id}", response_model=DespesaInDB)
async def buscar_despesa(
    despesa_id: int,
    usuario_id: str = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
) -> DespesaInDB:
    """
    Busca uma despesa específica pelo ID, pertencente ao usuário autenticado.

    Retorna 404 se a despesa não existir ou não pertencer ao usuário.
    """
    try:
        despesa = await supabase.buscar_despesa(despesa_id, usuario_id)
        if not despesa:
            raise HTTPException(status_code=404, detail="Despesa não encontrada")
        return despesa
    except HTTPException:
        # Repassa 404 sem reempacotar.
        raise
    except Exception as e:
        logger.error("Erro ao buscar despesa: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/{despesa_id}", response_model=DespesaInDB)
async def atualizar_despesa(
    despesa_id: int,
    dados: DespesaUpdate,
    usuario_id: str = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
) -> DespesaInDB:
    """
    Atualiza parcialmente uma despesa existente do usuário autenticado.

    - Recebe um `DespesaUpdate` (todos os campos opcionais).
    - Converte para dict apenas com campos enviados (`exclude_unset=True`).
    - Chama `SupabaseService.atualizar_despesa`, que aplica filtro por `usuario_id`.
    - Retorna 404 se a despesa não existir ou não pertencer ao usuário.
    """
    try:
        dados_dict = dados.model_dump(exclude_unset=True)
        atualizada = await supabase.atualizar_despesa(
            despesa_id=despesa_id,
            usuario_id=usuario_id,
            dados=dados_dict,
        )
        if not atualizada:
            raise HTTPException(status_code=404, detail="Despesa não encontrada")
        return atualizada
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro ao atualizar despesa: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/{despesa_id}")
async def deletar_despesa(
    despesa_id: int,
    usuario_id: str = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
) -> dict[str, str]:
    """
    Deleta uma despesa existente do usuário autenticado.

    Retorna 404 se a despesa não existir ou não pertencer ao usuário.
    """
    try:
        sucesso = await supabase.deletar_despesa(despesa_id, usuario_id)
        if not sucesso:
            raise HTTPException(status_code=404, detail="Despesa não encontrada")
        return {"message": "Despesa deletada com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Erro ao deletar despesa: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e

