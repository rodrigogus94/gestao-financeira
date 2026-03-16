"""
Rotas da API para relatórios e insights financeiros.

Reúne endpoints sob o prefixo `/relatorios` para:
- Gerar resumo mensal de despesas (total, por categoria, quantidade, etc.).
- Obter gastos agregados por categoria em um intervalo de datas.
- Consultar a evolução mensal de gastos ao longo de um ano.
- (Opcional) Gerar insights com IA a partir de um resumo mensal.

Todas as consultas são sempre filtradas pelo `usuario_id` obtido via
`get_current_user`, garantindo que cada usuário veja apenas seus próprios dados.
"""

from datetime import date
import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user, get_ia_provider_manager, get_supabase_service
from app.services.ia.manager import IAProviderManager
from app.services.supabase_service import SupabaseService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/relatorios", tags=["relatorios"])


@router.get("/mensal")
async def relatorio_mensal(
    ano: int = Query(..., description="Ano do relatório", ge=2020, le=2030),
    mes: int = Query(..., description="Mês do relatório", ge=1, le=12),
    usuario_id: str = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
):
    """
    Gera um relatório mensal de despesas do usuário autenticado.

    Usa `SupabaseService.get_resumo_mensal(usuario_id, ano, mes)` para calcular:
    - total do mês
    - total por categoria
    - quantidade de despesas
    - média de gastos por dia
    - maior despesa
    - período (início/fim em ISO)
    """
    try:
        return await supabase.get_resumo_mensal(usuario_id, ano, mes)
    except Exception as e:
        logger.error("Erro ao gerar relatório mensal: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/categoria")
async def gastos_por_categoria(
    data_inicio: date = Query(
        ...,
        description="Data inicial do relatório",
        ge=date(2020, 1, 1),
    ),
    data_fim: date = Query(
        ...,
        description="Data final do relatório",
        ge=date(2020, 1, 1),
    ),
    usuario_id: str = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
):
    """
    Gera um relatório de gastos agregados por categoria em um intervalo de datas.

    Usa `SupabaseService.get_despesas_por_categoria(usuario_id, data_inicio, data_fim)`
    para somar o valor de todas as despesas do usuário em cada categoria no período.
    """
    try:
        return await supabase.get_despesas_por_categoria(
            usuario_id, data_inicio, data_fim
        )
    except Exception as e:
        logger.error("Erro ao gerar relatório de gastos por categoria: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/evolucao/{ano}")
async def evolucao_mensal(
    ano: int = Query(..., description="Ano do relatório", ge=2020, le=2030),
    usuario_id: str = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
):
    """
    Gera um relatório de evolução mensal de despesas ao longo de um ano.

    Retorna uma lista de 12 itens (um por mês), cada um com:
    - `mes`: número do mês (1–12)
    - `total`: soma das despesas do usuário naquele mês.
    """
    try:
        # O método get_evolucao_mensal percorre os 12 meses internamente.
        return await supabase.get_evolucao_mensal(usuario_id, ano, mes=1)
    except Exception as e:
        logger.error("Erro ao gerar relatório de evolução mensal: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/insights")
async def gerar_insights(
    ano: int = Query(..., description="Ano do relatório", ge=2020, le=2030),
    mes: int = Query(..., description="Mês do relatório", ge=1, le=12),
    usuario_id: str = Depends(get_current_user),
    supabase: SupabaseService = Depends(get_supabase_service),
    ia_manager: IAProviderManager = Depends(get_ia_provider_manager),
):
    """
    Gera insights de despesas com base no resumo mensal e em um provedor de IA.

    Fluxo esperado:
    - Chama `get_resumo_mensal(usuario_id, ano, mes)` para obter o resumo numérico.
    - Se não houver despesas (`quantidade == 0`), retorna mensagem amigável.
    - Usa o `IAProviderManager` (estratégia/IA configurada) para gerar um texto
      com insights sobre o período (padrão: provedor \"openai\").
    - Retorna os insights junto com o período e o resumo usado como contexto.
    """
    try:
        resumo = await supabase.get_resumo_mensal(usuario_id, ano, mes)

        if not resumo or resumo.get("quantidade", 0) == 0:
            return {"message": "Nenhuma despesa encontrada para o mês selecionado"}

        # A implementação de gerar_insights deve existir em IAProviderManager;
        # aqui assumimos que ela recebe o resumo e um provedor opcional.
        insights = await ia_manager.gerar_insights(
            resumo,
            provedor="openai",
        )
        return {
            "insights": insights,
            "periodo": f"{mes}/{ano}",
            "resumo": resumo,
        }

    except Exception as e:
        logger.error("Erro ao gerar insights: %s", e)
        raise HTTPException(status_code=500, detail=str(e)) from e
