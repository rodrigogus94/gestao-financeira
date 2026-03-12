"""
Serviço de acesso ao banco de dados Supabase.

Este módulo centraliza a comunicação com o Supabase: criação do cliente (URL + chave)
e operações CRUD e de agregação sobre as tabelas do projeto, em especial `despesas`.
As rotas da API devem usar este serviço em vez de chamar o Supabase diretamente.

Dependências: supabase (create_client, Client), app.core.config.settings,
app.models.domain.despesa (DespesaCreate, DespesaInDB, CategoriaDespesa, StatusDespesa).
"""

import logging
from datetime import date, datetime
from typing import Any

from supabase import Client, create_client

from app.core.config import settings
from app.models.domain.despesa import (
    CategoriaDespesa,
    DespesaCreate,
    DespesaInDB,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Classe principal do serviço
# -----------------------------------------------------------------------------


class SupabaseService:
    """
    Serviço para interagir com o Supabase (banco de dados e API).

    Encapsula o cliente Supabase (criado com SUPABASE_URL e SUPABASE_KEY) e expõe
    métodos para despesas (salvar, listar, atualizar, deletar) e para relatórios
    (resumo mensal, despesas por categoria, evolução mensal). Todas as operações
    são filtradas por usuario_id quando aplicável, alinhado às políticas RLS.
    """

    def __init__(self) -> None:
        """
        Inicializa o serviço criando o cliente Supabase com as credenciais do settings.

        Usa SUPABASE_URL e SUPABASE_KEY (anon key). Para operações que precisam
        bypassar RLS (ex.: jobs em background), pode-se usar SUPABASE_SERVICE_KEY
        em outro ponto ou em uma variante do serviço.
        """
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY,
        )
        logger.info("SupabaseService inicializado")
        logger.info("Conectado ao Supabase")

    # -------------------------------------------------------------------------
    # Despesas — CRUD
    # -------------------------------------------------------------------------

    async def salvar_despesa(self, despesa: DespesaCreate) -> DespesaInDB:
        """
        Insere uma nova despesa na tabela `despesas` do Supabase.

        Converte o modelo DespesaCreate em dict com model_dump(), adiciona
        created_at (timestamp atual em ISO) e envia um INSERT. O Supabase retorna
        o registro inserido (com id gerado); esse registro é convertido em
        DespesaInDB e retornado. Em caso de falha (ex.: constraint violation ou
        erro de rede), a exceção é logada e re-levantada.
        """
        try:
            data = despesa.model_dump()
            data["created_at"] = datetime.now().isoformat()

            response = await self.client.table("despesas").insert(data).execute()

            if not response.data:
                raise Exception("Erro ao salvar despesa: sem dados retornados")

            logger.info(f"Despesa salva com sucesso: {response.data[0]['id']}")
            return DespesaInDB(**response.data[0])

        except Exception as e:
            logger.error(f"Erro ao salvar despesa: {e}")
            raise

    async def listar_despesas(
        self,
        usuario_id: str,
        data_inicio: date | None = None,
        data_fim: date | None = None,
        categoria: CategoriaDespesa | None = None,
        limit: int = 100,
    ) -> list[DespesaInDB]:
        """
        Lista despesas do usuário com filtros opcionais, ordenadas por data (mais recente primeiro).

        Monta uma query na tabela `despesas`: select *, filtro por usuario_id,
        ordenação por data descendente e limit. Se data_inicio e/ou data_fim forem
        informados, aplica gte/lte na coluna data. Se categoria for informada, filtra
        por categoria. O resultado é convertido em lista de DespesaInDB. Em erro,
        loga e retorna lista vazia.
        """
        try:
            query = (
                self.client.table("despesas")
                .select("*")
                .eq("usuario_id", usuario_id)
                .order("data", desc=True)
                .limit(limit)
            )

            if data_inicio:
                query = query.gte("data", data_inicio.isoformat())
            if data_fim:
                query = query.lte("data", data_fim.isoformat())
            if categoria:
                query = query.eq("categoria", categoria.value)

            response = await query.execute()

            return [DespesaInDB(**item) for item in response.data]

        except Exception as e:
            logger.error(f"Erro ao listar despesas: {e}")
            return []

    async def atualizar_despesa(
        self,
        despesa_id: int,
        usuario_id: str,
        dados: dict[str, Any],
    ) -> DespesaInDB | None:
        """
        Atualiza parcialmente uma despesa existente, desde que pertença ao usuario_id.

        Adiciona updated_at aos dados, executa UPDATE na tabela `despesas` com
        filtro id = despesa_id e usuario_id = usuario_id. Retorna o registro
        atualizado como DespesaInDB se a resposta trouxer dados; caso contrário
        retorna None (ex.: id inexistente ou usuário não dono do registro).
        """
        dados["updated_at"] = datetime.now().isoformat()

        response = (
            self.client.table("despesas")
            .update(dados)
            .eq("id", despesa_id)
            .eq("usuario_id", usuario_id)
            .execute()
        )

        if response.data:
            return DespesaInDB(**response.data[0])
        return None

    async def deletar_despesa(self, despesa_id: int, usuario_id: str) -> bool:
        """
        Remove uma despesa da tabela, desde que pertença ao usuario_id.

        Executa DELETE com filtro id e usuario_id. Retorna True se pelo menos
        um registro foi removido (len(response.data) > 0), False caso contrário.
        """
        response = (
            self.client.table("despesas")
            .delete()
            .eq("id", despesa_id)
            .eq("usuario_id", usuario_id)
            .execute()
        )

        return len(response.data) > 0

    # -------------------------------------------------------------------------
    # Relatórios e agregações
    # -------------------------------------------------------------------------

    async def get_resumo_mensal(
        self, usuario_id: str, ano: int, mes: int
    ) -> dict[str, Any]:
        """
        Gera o resumo de despesas do usuário para um mês: total, por categoria,
        quantidade, média/dia, maior despesa.

        Calcula o intervalo do mês (primeiro dia ao último). Se mes == 12, o fim
        do período é o primeiro dia do ano seguinte (exclusive na lógica de dias).
        Busca as despesas do período com listar_despesas, soma o total, agrupa por
        categoria, calcula a média por dia (total / dias_no_mes) e a maior despesa.
        Retorna um dict com total, categorias (categoria -> total), quantidade,
        media_por_dia, maior_despesa e periodo (inicio/fim em ISO). Se não houver
        despesas, retorna estrutura com zeros. Em erro, loga e retorna dict vazio.
        """
        try:
            data_inicio = date(ano, mes, 1)
            if mes == 12:
                data_fim = date(ano + 1, 1, 1)
            else:
                data_fim = date(ano, mes + 1, 1)

            despesas = await self.listar_despesas(
                usuario_id, data_inicio, data_fim
            )

            if not despesas:
                return {
                    "total": 0,
                    "categorias": {},
                    "quantidade": 0,
                    "media_por_dia": 0,
                    "maior_despesa": 0,
                    "periodo": {
                        "inicio": data_inicio.isoformat(),
                        "fim": data_fim.isoformat(),
                    },
                }

            total = sum(despesa.valor for despesa in despesas)

            por_categoria: dict[str, float] = {}
            for despesa in despesas:
                cat = despesa.categoria.value
                por_categoria[cat] = por_categoria.get(cat, 0) + despesa.valor

            dias_no_mes = (data_fim - data_inicio).days
            maior = max((despesa.valor for despesa in despesas), default=0)

            return {
                "total": round(total, 2),
                "categorias": {
                    cat: round(val, 2) for cat, val in por_categoria.items()
                },
                "quantidade": len(despesas),
                "media_por_dia": round(total / dias_no_mes, 2)
                if dias_no_mes > 0
                else 0,
                "maior_despesa": round(maior, 2),
                "periodo": {
                    "inicio": data_inicio.isoformat(),
                    "fim": data_fim.isoformat(),
                },
            }
        except Exception as e:
            logger.error(f"Erro ao gerar resumo mensal: {e}")
            return {}

    async def get_despesas_por_categoria(
        self,
        usuario_id: str,
        data_inicio: date,
        data_fim: date,
    ) -> dict[str, float]:
        """
        Agrupa as despesas do usuário no período por categoria e retorna o total por categoria.

        Usa listar_despesas para o intervalo e usuario_id, percorre os resultados
        somando o valor por categoria (usando o value do enum). Retorna um dict
        categoria -> total arredondado em 2 casas decimais.
        """
        despesas = await self.listar_despesas(
            usuario_id, data_inicio, data_fim
        )

        resultado: dict[str, float] = {}
        for despesa in despesas:
            cat = despesa.categoria.value
            resultado[cat] = resultado.get(cat, 0) + despesa.valor

        return {cat: round(val, 2) for cat, val in resultado.items()}

    async def get_evolucao_mensal(
        self, usuario_id: str, ano: int, mes: int
    ) -> list[dict[str, Any]]:
        """
        Retorna a evolução dos totais mensais de despesas do usuário ao longo dos 12 meses do ano.

        Itera de janeiro (1) a dezembro (12), chama get_resumo_mensal para cada
        mês e monta uma lista de dicts com "mes" e "total". O parâmetro `mes` da
        função não é usado (a evolução cobre o ano inteiro); pode ser mantido
        para compatibilidade com assinatura futura (ex.: até o mês atual).
        """
        resultado: list[dict[str, Any]] = []

        for m in range(1, 13):
            resumo = await self.get_resumo_mensal(usuario_id, ano, m)
            resultado.append({
                "mes": m,
                "total": resumo.get("total", 0),
            })

        return resultado
