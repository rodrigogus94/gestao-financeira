"""
Rotas da API relacionadas a IA (Inteligência Artificial).

Expõe endpoints para: listar provedores de IA, extrair despesa a partir de texto
natural, fazer perguntas com contexto financeiro, comparar extrações entre
provedores e recarregar a configuração dos provedores. Usa as dependências
get_current_user, get_ia_provider_manager e get_supabase_service para
autenticação e acesso aos serviços.
"""

from datetime import datetime
import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_current_user, get_ia_provider_manager, get_supabase_service
from app.models.domain.despesa import DespesaCreate, FonteDespesa
from app.services.ia.factory import IAProviderFactory
from app.services.ia.manager import EstrategiaSelecao, IAProviderManager
from app.services.supabase_service import SupabaseService

# ---------------------------------------------------------------------------
# Configuração do router e logging
# ---------------------------------------------------------------------------
# prefix="/ia" agrupa todos os endpoints sob /ia (ex.: /ia/provedores, /ia/extrair-despesa).
# tags=["IA"] agrupa a documentação no Swagger/OpenAPI.
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ia", tags=["IA"])

# ---------------------------------------------------------------------------
# Modelos de Request/Response (schemas Pydantic)
# ---------------------------------------------------------------------------
# Usados para validar o corpo das requisições e padronizar o formato das
# respostas da API (incluindo documentação automática no Swagger).


class TextoRequest(BaseModel):
    """
    Corpo da requisição para extração de despesa a partir de texto.

    - texto: frase em linguagem natural descrevendo a despesa (ex.: "50 reais no almoço").
    - provedor: qual provedor de IA usar (openai, gemini, ollama); None = padrão.
    - estrategia: PRINCIPAL, RAPIDO, PRECISO, FALLBACK, PARALELO, VOTACAO; None = padrão.
    - Salvar: se True, persiste a despesa no Supabase após extrair.
    """

    texto: str
    provedor: str | None = None
    estrategia: EstrategiaSelecao | None = None
    Salvar: bool = True


class TextoResponse(BaseModel):
    """
    Resposta do endpoint de extração de despesa.

    - sucesso: indica se a extração (e opcionalmente o salvamento) deu certo.
    - extraido: dict com os campos da despesa extraída (valor, categoria, data, etc.).
    - estrategia: estratégia efetivamente usada (valor do enum).
    - provedor_usado: provedor que realizou a extração.
    - despesa_id: ID no banco se foi salvo; None se Salvar era False.
    - mensagem: texto descritivo do resultado.
    """

    sucesso: bool
    extraido: dict[str, Any]
    estrategia: str
    provedor_usado: str | None = None
    despesa_id: int | None = None
    mensagem: str


class PerguntaRequest(BaseModel):
    """
    Corpo da requisição para pergunta ao modelo de IA.

    - pergunta: texto da pergunta do usuário (ex.: "Quanto gastei com transporte?").
    - contexto: texto opcional com dados financeiros; se omitido, a API busca as últimas despesas.
    - provedor: provedor de IA a usar; None = padrão (DEFAULT_IA_PROVIDER).
    """

    pergunta: str
    contexto: str | None = None
    provedor: str | None = None


class PerguntaResponse(BaseModel):
    """Resposta do endpoint de pergunta: texto original, resposta da IA e timestamp."""

    texto_original: str
    resposta: dict[str, Any]
    timestamp: str


class ComparacaoResponse(BaseModel):
    """
    Resposta do endpoint de comparação entre provedores.

    - texto_original: texto da despesa enviado.
    - resultados: dict cuja chave é o nome do provedor e o valor é o resultado da extração
      (ou dict com chave "Erro" em caso de falha).
    - timestamp: data/hora da comparação em ISO.
    """

    texto_original: str
    resultados: dict[str, Any]
    timestamp: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/provedores")
async def listar_provedores():
    """
    Lista todos os provedores de IA configurados e suas estratégias.

    Para cada provedor (openai, gemini, ollama, etc.) tenta obter a instância
    e retorna nome, tipo e status (disponivel/indisponivel). Inclui também
    a lista de estratégias de extração (PRINCIPAL, RAPIDO, PRECISO, etc.) e
    os valores default/fallback para uso no frontend ou em chamadas à API.
    """
    try:
        provedores = IAProviderFactory.listar_provedores_disponiveis()
        return {
            "provedores": provedores,
            "estrategias": [estrategia.value for estrategia in EstrategiaSelecao],
            "default": EstrategiaSelecao.PRINCIPAL.value,
            "fallback": "ollama",
        }
    except Exception as e:
        logger.error("Erro ao listar provedores de IA: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao listar provedores de IA: {e}",
        ) from e


@router.post("/extrair-despesa", response_model=TextoResponse)
async def extrair_despesa(
    request: TextoRequest,
    usuario_id: str = Depends(get_current_user),
    ia_manager: IAProviderManager = Depends(get_ia_provider_manager),
    supabase: SupabaseService = Depends(get_supabase_service),
):
    """
    Extrai uma despesa a partir de texto em linguagem natural.

    O texto é enviado ao provedor de IA (ou à estratégia escolhida) para extrair
    valor, categoria, data e descrição. Se Salvar for True, a despesa é persistida
    no Supabase com fonte TEXTUAL_NATURAL e metadata (provedor, confiança, texto original).

    Exemplos de texto: "Gastei 50 reais com almoço hoje", "Uber 25 reais ontem",
    "Comprei 100 reais de alimentos na mercearia", "Paguei 150 reais de aluguel do mês".
    """
    try:
        logger.info(
            "Extraindo despesa para usuário %s, provedor=%s, estratégia=%s",
            usuario_id,
            request.provedor,
            request.estrategia,
        )

        # Aplica a estratégia solicitada no body (ex.: PARALELO, VOTACAO)
        if request.estrategia:
            ia_manager.estrategia = request.estrategia

        # Delega ao IAManager: escolhe o provedor conforme a estratégia e extrai
        extraido = await ia_manager.extrair_despesa(
            request.texto, provider_default=request.provedor
        )
        resultado_dict = extraido.model_dump()

        # Opcionalmente persiste no banco para o usuário autenticado
        despesa_id = None
        if request.Salvar:
            despesa = DespesaCreate(
                valor=extraido.valor,
                categoria=extraido.categoria,
                data=extraido.data,
                descricao=extraido.descricao or request.texto[:200],
                usuario_id=usuario_id,
                fonte=FonteDespesa.TEXTUAL_NATURAL,
                metadata={
                    "provedor": request.provedor,
                    "confianca": extraido.confianca,
                    "texto_original": request.texto,
                },
            )
            salva = await supabase.salvar_despesa(despesa)
            despesa_id = salva.id
            logger.info("Despesa salva com sucesso: %s", despesa_id)

        estrategia_efetiva = (
            request.estrategia.value if request.estrategia else ia_manager.estrategia.value
        )
        return TextoResponse(
            sucesso=True,
            extraido=resultado_dict,
            estrategia=estrategia_efetiva,
            provedor_usado=request.provedor,
            despesa_id=despesa_id,
            mensagem=(
                "Despesa extraída e salva com sucesso"
                if request.Salvar
                else "Despesa extraída com sucesso (não salva)"
            ),
        )

    except Exception as e:
        logger.error("Erro ao extrair despesa: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao extrair despesa: {e}",
        ) from e

@router.post("/perguntar")
async def perguntar(
    request: PerguntaRequest,
    usuario_id: str = Depends(get_current_user),
    ia_manager: IAProviderManager = Depends(get_ia_provider_manager),
    supabase: SupabaseService = Depends(get_supabase_service),
):
    """
    Envia uma pergunta ao modelo de IA com contexto financeiro opcional.

    Se contexto não for enviado no body, a API busca as últimas 50 despesas do
    usuário e monta um texto com descrição, valor e data de cada uma. Em seguida
    chama o provedor de IA (request.provedor ou padrão) para responder à pergunta
    com base nesse contexto (ex.: "Quanto gastei com transporte este mês?").
    """
    try:
        contexto = request.contexto
        if not contexto:
            despesas = await supabase.listar_despesas(usuario_id=usuario_id, limit=50)
            contexto = f"Últimas 50 despesas: {len(despesas)} registros"
            for despesa in despesas:
                contexto += (
                    f"\n- {despesa.descricao} - {despesa.valor:.2f} - "
                    f"{despesa.data.strftime('%d/%m/%Y')}"
                )

        # IAManager não expõe perguntar; usa o provedor diretamente
        provider = IAProviderFactory.get_provider(request.provedor)
        resposta = await provider.perguntar(contexto=contexto, pergunta=request.pergunta)

        return {
            "pergunta": request.pergunta,
            "resposta": resposta,
            "provedor": request.provedor or "auto",
        }

    except Exception as e:
        logger.error("Erro ao perguntar: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Erro ao perguntar: {e}",
        ) from e


@router.post("/comparar", response_model=ComparacaoResponse)
async def comparar_provedores(
    texto: str = Body(..., embed=True),
    usuario_id: str = Depends(get_current_user),
):
    """
    Compara a extração da mesma despesa em todos os provedores de IA configurados.

    Envia o mesmo texto para cada provedor (openai, gemini, ollama, etc.), extrai
    a despesa em cada um e devolve um dict com o resultado por provedor. Útil
    para diagnosticar diferenças de interpretação ou resolver ambiguidades.

    Exemplos de texto: "Gastei 50 reais com almoço hoje", "Uber 25 reais ontem",
    "Comprei 100 reais de alimentos na mercearia", "Paguei 150 reais de aluguel do mês".
    """
    resultados: dict[str, Any] = {}
    provedores = IAProviderFactory.listar_provedores_disponiveis()

    for item in provedores:
        nome = item.get("tipo") or item.get("nome", "unknown")
        try:
            provider = IAProviderFactory.get_provider(nome)
            resultado = await provider.extrair_despesa(texto)
            resultados[nome] = resultado.model_dump()
        except Exception as e:
            resultados[nome] = {"Erro": str(e)}

    return ComparacaoResponse(
        texto_original=texto,
        resultados=resultados,
        timestamp=datetime.now().isoformat(),
    )

@router.post("/recarregar")
async def recarregar():
    """
    Recarrega a configuração dos provedores de IA (limpa o cache de instâncias).

    Limpa o cache interno da IAProviderFactory para que a próxima chamada a
    get_provider recrie os clientes. Útil após alterar variáveis de ambiente
    (ex.: API keys) sem reiniciar o servidor. Retorna a lista de tipos que
    estavam em cache.
    """
    tipos_limpos = IAProviderFactory.recarregar_provedores()
    return {
        "mensagem": "Provedores recarregados com sucesso",
        "provedores": tipos_limpos,
    }
