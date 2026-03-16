"""
Gerenciador de provedores de IA com estratégias de seleção e agregação.

O IAManager permite escolher como usar os provedores: usar apenas o principal
(PRINCIPAL), o mais rápido (RAPIDO = Ollama), o mais preciso (PRECISO = OpenAI),
tentar em sequência até um funcionar (FALLBACK), rodar todos em paralelo e
ficar com o resultado de maior confiança (PARALELO), ou rodar todos e agregar
por votação (valor médio, categoria mais votada) (VOTACAO). O método principal
é extrair_despesa(texto, provider_default), que delega para o provedor ou para
_executar_paralelo, _executar_fallback ou _executar_votacao conforme a estratégia.
"""

import asyncio
import logging
from collections import Counter
from enum import Enum

from app.core.config import settings

from .base import ExtracaoDespesa
from .factory import IAProviderFactory

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Estratégias de seleção do provedor
# -----------------------------------------------------------------------------


class EstrategiaSelecao(str, Enum):
    """
    Modos de uso dos provedores de IA na extração de despesa.

    - PRINCIPAL: usa o provider_default (ou o padrão de settings).
    - RAPIDO: força uso do Ollama (geralmente local, mais rápido).
    - PRECISO: força uso do OpenAI (modelos em nuvem, em geral mais precisos).
    - FALLBACK: tenta provider_default, depois FALLBACK_IA_PROVIDER, depois openai,
      gemini, ollama em ordem até um suceder.
    - PARALELO: dispara extração em todos os provedores em paralelo e retorna o
      resultado com maior confiança.
    - VOTACAO: dispara em todos, calcula valor médio e categoria mais votada e
      retorna um único ExtracaoDespesa agregado.
    """

    PRINCIPAL = "principal"
    FALLBACK = "fallback"
    PARALELO = "paralelo"
    VOTACAO = "votacao"
    RAPIDO = "rapido"
    PRECISO = "preciso"


# -----------------------------------------------------------------------------
# Gerenciador
# -----------------------------------------------------------------------------


class IAManager:
    """
    Orquestra a extração de despesa conforme a estratégia configurada.

    No __init__ recebe a EstrategiaSelecao e guarda listas de provedores
    considerados "rápidos" (ollama) e "precisos" (openai, gemini). O método
    extrair_despesa(texto, provider_default) implementa o despacho para
    o provedor único (PRINCIPAL, RAPIDO, PRECISO) ou para os métodos
    _executar_paralelo, _executar_fallback ou _executar_votacao.
    """

    def __init__(
        self, estrategia: EstrategiaSelecao = EstrategiaSelecao.PRINCIPAL
    ) -> None:
        """
        Inicializa o gerenciador com a estratégia de seleção e listas de provedores.

        Args:
            estrategia: Como escolher ou agregar provedores (principal, rapido,
                preciso, fallback, paralelo, votacao).
        """
        self.estrategia = estrategia
        # Provedores considerados rápidos (ex.: Ollama local) e precisos (ex.: OpenAI, Gemini).
        self.provedores_rapidos = ["ollama"]
        self.provedores_precisos = ["openai", "gemini", "claude"]

    async def extrair_despesa(
        self, texto: str, provider_default: str | None = None
    ) -> ExtracaoDespesa:
        """
        Extrai uma despesa do texto usando a estratégia configurada.

        PRINCIPAL/else: get_provider(provider_default) e extrair_despesa(texto).
        RAPIDO: get_provider("ollama") e extrair_despesa(texto).
        PRECISO: get_provider("openai") e extrair_despesa(texto).
        VOTACAO: _executar_votacao(texto).
        PARALELO: _executar_paralelo(texto).
        FALLBACK: _executar_fallback(texto, provider_default).

        Args:
            texto: Texto natural descrevendo a despesa.
            provider_default: Provedor preferido (usado em PRINCIPAL e na ordem de
                tentativa do FALLBACK).

        Returns:
            ExtracaoDespesa resultante.
        """
        if self.estrategia == EstrategiaSelecao.PRINCIPAL:
            provider = IAProviderFactory.get_provider(provider_default)
            return await provider.extrair_despesa(texto)

        if self.estrategia == EstrategiaSelecao.RAPIDO:
            provider = IAProviderFactory.get_provider("ollama")
            return await provider.extrair_despesa(texto)

        if self.estrategia == EstrategiaSelecao.PRECISO:
            provider = IAProviderFactory.get_provider("openai")
            return await provider.extrair_despesa(texto)

        if self.estrategia == EstrategiaSelecao.VOTACAO:
            return await self._executar_votacao(texto)

        if self.estrategia == EstrategiaSelecao.PARALELO:
            return await self._executar_paralelo(texto)

        if self.estrategia == EstrategiaSelecao.FALLBACK:
            return await self._executar_fallback(texto, provider_default)

        # Qualquer valor inesperado de estratégia cai no comportamento padrão (PRINCIPAL).
        provider = IAProviderFactory.get_provider(provider_default)
        return await provider.extrair_despesa(texto)

    async def gerar_insights(
        self,
        resumo_mensal: dict,
        provedor: str | None = None,
    ) -> str:
        """
        Gera um texto de insights a partir de um resumo mensal de despesas.

        Usa o método `gerar_relatorio(dados)` do IAProvider, que por sua vez
        utiliza o prompt "gerar_relatorio" definido em `config.py`. O dicionário
        `resumo_mensal` deve ser o retorno de `SupabaseService.get_resumo_mensal`,
        contendo chaves como total, categorias, quantidade, media_por_dia e periodo.

        Args:
            resumo_mensal: Dict com o resumo numérico das despesas no período.
            provedor: Tipo de provedor de IA a usar ("openai", "gemini", "ollama", etc.).
                Se None, usa o DEFAULT_IA_PROVIDER das configurações.

        Returns:
            Texto com insights e sugestões sobre os gastos do período.
        """
        provider = IAProviderFactory.get_provider(provedor)
        return await provider.gerar_relatorio(resumo_mensal)

    async def _executar_paralelo(self, texto: str) -> ExtracaoDespesa:
        """
        Dispara extrair_despesa em todos os provedores (openai, gemini, ollama) em paralelo.

        Usa asyncio.gather com return_exceptions=True. Descarta resultados que forem exceção.
        Se não houver nenhum sucesso, levanta exceção. Caso contrário, retorna o
        ExtracaoDespesa com maior confiança (max por confianca).
        """
        tarefas = []
        for tipo in ["openai", "gemini", "ollama", "claude"]:
            try:
                provider = IAProviderFactory.get_provider(tipo)
                tarefas.append(provider.extrair_despesa(texto))
            except Exception:
                continue
        if not tarefas:
            raise Exception("Nenhum provedor de IA disponível para execução paralela.")
        resultados = await asyncio.gather(*tarefas, return_exceptions=True)
        sucessos = [r for r in resultados if not isinstance(r, Exception)]
        if not sucessos:
            raise Exception("Nenhum provedor de IA conseguiu extrair a despesa.")
        return max(sucessos, key=lambda x: x.confianca)

    async def _executar_fallback(
        self, texto: str, provider_default: str | None = None
    ) -> ExtracaoDespesa:
        """
        Tenta extrair a despesa com vários provedores em ordem até um suceder.

        Ordem de tentativa: provider_default (se informado), FALLBACK_IA_PROVIDER
        (se existir em settings), depois "openai", "gemini", "ollama". Para cada
        tipo, get_provider(tipo) e extrair_despesa(texto); na primeira resposta
        sem exceção, retorna. Se todos falharem, levanta exceção.
        """
        tentativas: list[str] = []
        if provider_default:
            tentativas.append(provider_default)
        if hasattr(settings, "FALLBACK_IA_PROVIDER") and settings.FALLBACK_IA_PROVIDER:
            tentativas.append(settings.FALLBACK_IA_PROVIDER)
        tentativas.extend(["openai", "gemini", "ollama", "claude"])
        for tipo in tentativas:
            try:
                provider = IAProviderFactory.get_provider(tipo)
                return await provider.extrair_despesa(texto)
            except Exception as e:
                logger.warning(f"Fallback {tipo} falhou: {e}")
                continue
        raise Exception("Todos os fallbacks falharam.")

    async def _executar_votacao(self, texto: str) -> ExtracaoDespesa:
        """
        Extrai a despesa com todos os provedores e agrega por votação.

        Chama extrair_despesa(texto) para openai, gemini e ollama (ignorando
        falhas). Valor final: média dos valores retornados. Categoria final:
        a mais frequente (Counter.most_common(1)). Data e descrição vêm do
        primeiro resultado; provedor é "Votação (N provedores)" e confianca 0.95.
        """
        resultados: list[ExtracaoDespesa] = []
        for tipo in ["openai", "gemini", "ollama", "claude"]:
            try:
                provider = IAProviderFactory.get_provider(tipo)
                resultados.append(await provider.extrair_despesa(texto))
            except Exception:
                continue
        if not resultados:
            raise Exception("Sem resultados de votação.")
        valor_medio = sum(r.valor for r in resultados) / len(resultados)
        categorias = [r.categoria for r in resultados]
        categoria_vencedora = Counter(categorias).most_common(1)[0][0]
        return ExtracaoDespesa(
            valor=round(valor_medio, 2),
            categoria=categoria_vencedora,
            data=resultados[0].data,
            descricao=texto[:100],
            fonte="textual_natural",
            status="pendente",
            provedor=f"Votação ({len(resultados)} provedores)",
            confianca=0.95,
        )


# -----------------------------------------------------------------------------
# Compatibilidade
# -----------------------------------------------------------------------------
# Parte do código (rotas/deps) usa o nome IAProviderManager. Mantemos um alias
# para evitar que imports existentes quebrem.
IAProviderManager = IAManager
